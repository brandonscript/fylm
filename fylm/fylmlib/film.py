#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandoncript

# This program is bound to the Hippocratic License 2.1
# Full text is available here:
# https: // firstdonoharm.dev/version/2/1/license

# Further to adherence to the Hippocratic Licenese, this program is
# free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. Full text is avaialble here:
# http: // www.gnu.org/licenses

# Where a conflict or dispute would arise between these two licenses, HLv2.1
# shall take precedence.

"""Film descriptor object.

    Film: the main class exported by this module.
"""

import os
import re
import sys
import itertools
import asyncio
import concurrent.futures
from functools import partial
from copy import copy
from pathlib import Path
from typing import Union

from pymediainfo import MediaInfo
from lazy import lazy

import fylmlib.config as config
import fylmlib.patterns as patterns
from fylmlib.tools import *
from fylmlib.enums import *
from fylmlib import FilmPath
from fylmlib import Console
from fylmlib import Parser
from fylmlib import Duplicates
from fylmlib import Format
from fylmlib import TMDb
from fylmlib import Info

class Film(FilmPath):
    """A Film object contains basic details about the a film, references to the individual 
    File objects it contains (or just one, if it's a single file). Using regular expressions 
    and themoviedb.org API, it can intelligently identify key attributes of a film from 
    common file naming conventions.

    Attributes:

        src (FilmPath):                 Original (immutable) abs source path of the film's root, e.g.
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene or
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene.mkv

        dst (FilmPath):                 Desired abs path to this film's new root, e.g.
                                         - /volumes/movies/HD/Avatar (2009) or
                                         - /volumes/movies/HD/Avatar (2009) Bluray-1080p.mkv

        main_file (Film.File):          Returns the largest wanted file in a Film folder (or if there 
                                        is only a single file, that file). In most cases, this will be
                                        the primary video file
                                        Be careful when using this, as a folder could
                                        have multiple versions of the same film.

        title (str):                    Title of the film.

        title_the (str):                For titles that begin with 'The', move it to the
                                        end of the title, e.g. 'Chronicles of Narnia, The'.

        year (int):                     Primary release year, determined from FilmPath's filmrel.

        tmdb (TMDb.Result):             Selected TMDb.Result that was selected as a match.

        files ([Film.File]):            Mapped from FilmPath.files to Film.File. 
        
        new_name (Path):                New name of the film, including file extension if it's a file.
        new_name_lazy (Path):           Lazy (cached) copy of new_name
        
        wanted_files ([Film.File]):     A subset of files that have wanted file extensions.

        bad_files ([Film.File]):        A subset of files that are not wanted.

        should_ignore (bool):           Returns True if this film should be ignored, then updates
                                        ignore_reason with an explanation.

        ignore_reason (IgnoreReason):   If applicable, a reason describing why this film was ignored.

        should_hide (bool):             Return True if this Film should be hidden
                                        when printing to the console.
    """

    def __init__(self, path: Union[str, Path, 'FilmPath']):
        
        super().__init__(path)
        
        self._src = Path(self)
        self.tmdb: TMDb.Result = TMDb.Result()
        self._tmdb_matches: [TMDb.Result] = []

    def __repr__(self):
        return ' '.join([str(x) for x in [
            f"Film('{self}')",
            self.title,
            self.year,
            self.tmdb.id] if x])

    @property
    def bad_files(self) -> Iterable['Film.File']:
        return iter(filter(lambda f: not f.is_wanted, self.files))

    @property
    def dst(self) -> Path:
        # If 'rename_only' is enabled, we need to override the configured
        # destination dir with the source dir.
        if config.rename_only is True:
            return self.src.parent / self.new_name
        else:
            return config.destination_dir(self.main_file.resolution) / self.new_name
        
    @property
    def new_name(self) -> Path:
        name = Format.Name(self.main_file)
        self.new_name_lazy = name
        return name.dirname if config.use_folders else name.filename
    
    @lazy
    def new_name_lazy(self) -> Path:
        # Cached copy of new_name
        return self.new_name

    @lazy
    def duplicate_files(self) -> ['Film.File']:
        return duplicates.Find(self)

    @property
    def files(self) -> Iterable['Film.File']:
        files = [Film.File(f, film=self) for f in super().files]
        return iter(sorted(files, key=lambda f: f.size_lazy, reverse=True))

    @lazy
    def ignore_reason(self) -> IgnoreReason:
        
        i = IgnoreReason
        if re.search(patterns.UNPACK, str(self.filmrel)): return i.UNPACKING
        elif is_sys_file(self): return i.SYS
        elif re.search(patterns.SAMPLE, str(self.filmrel)): return i.SAMPLE
        elif Info.has_ignored_string(self.src): return i.IGNORED_STRING
        elif bool(re.search(patterns.TV_SHOW, str(self))): return i.TV_SHOW
        elif not self.exists(): return i.DOES_NOT_EXIST
        elif self.is_dir() and iterlen(self.video_files) == 0: return i.NO_VIDEO_FILES
        elif self.is_file() and not Info.has_valid_ext(self): return i.INVALID_EXT
        elif self.year is None: return i.UNKNOWN_YEAR
        elif not Info.is_acceptable_size(self.main_file): return i.TOO_SMALL
        else: return None
        
        # FIXME: Re-implement this in processor
        """if self.ignore_reason is i.TOO_SMALL:
            return f"{self.ignore_reason.display_name} - {formatter.pretty_size(self.size)}"
        return self.ignore_reason.display_name if self.ignore_reason else None"""

    @lazy
    def main_file(self) -> 'Film.File':
        if self.is_file():
            return Film.File(self, film=self)
        elif self.is_dir():
            return first(self.video_files, None)
        else:
            return None

    async def search_tmdb(self):
        """Performs a TMDb search on the existing film.

        Calls the tmdb.search() method, passing the current film
        as params. If a result is found, the current film's properties
        are updated with the values from TMDb.
        """

        # Only perform lookups if TMDb searching is enabled.
        if config.tmdb.enabled is False:
            return
    
        # Perform the search and save the first 10 sresults to the matches list.
        # If ID is not None, search by ID.
        self._tmdb_matches = await TMDb.Search(self.title, self.year, self.tmdb.id).do()
        best_match = first(iter(self._tmdb_matches or []), None)
        if best_match:
            # If we find a result, update title and year.
            self.tmdb = best_match
            self.title = best_match.new_title
            self.year = best_match.new_year
        else:
            # If not, we update the ignore_reason
            self.ignore_reason = IgnoreReason.NO_TMDB_RESULTS

    def search_tmdb_sync(self):
        """A synchronous wrapper for search_tmdb().
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.search_tmdb())

    @lazy
    def should_hide(self) -> bool:
        if (self.should_ignore is True and config.interactive is True
                # In interactive mode, these three exceptions should be ignored because the
                # user may want to manually match them anyway.
                and not self.ignore_reason is IgnoreReason.UNKNOWN_TITLE
                and not self.ignore_reason is IgnoreReason.UNKNOWN_YEAR
                and not self.ignore_reason is IgnoreReason.TOO_SMALL):
            return True
        elif (self.should_ignore is True 
              and config.interactive is False 
              and config.hide_ignored is True):
            return True
        else:
            return False

    @lazy
    def should_ignore(self) -> bool:
        return self.ignore_reason is not None

    @lazy
    def src(self) -> FilmPath:
        return self._src

    # title needs a getter and setter, because a TMDb search can update it
    @lazy
    def title(self) -> str:
        return Parser(self).title

    @property
    def title_the(self) -> str:
        return (f'{Format.strip_the(self.title)}, The'
                if re.search(patterns.THE_PREFIX_SUFFIX, self.title) else self.title)

    @property
    def video_files(self) -> Iterable['Film.File']:
        video_files = [Film.File(f, film=self) for f in super().video_files]
        return iter(sorted(video_files, key=lambda f: f.size_lazy, reverse=True))

    @property
    def wanted_files(self) -> Iterable['Film.File']:
        return iter(filter(lambda f: f.is_wanted, self.files))
    
    @lazy
    def year(self) -> int:
        return Parser(self).year

    class File(FilmPath):
        """A Film object contains specific details about a Film file, including detailed information 
        like file type, media info, and other details that may differentiate a file from others 
        along side it in the same folder. This is a critical separation of roles from Film, in that a 
        Film folder may contain multiple versions of the same film, each with unique properties.

        For example:
            /volumes/Movies/Avatar (2009) may contain both:
                - Avatar (2009) Bluray-2160p HDR.mp4
                - Avatar (2009) Bluray-1080p.mkv

        All File objects bound to the same Film object must share at least the same destination_root_dir
        path, title, year, and tmdb_id. 

        Invalid or unwanted files can still be mapped to a File object, but self.is_wanted will return False.

        Attributes:
        
            src (FilmPath):                 Original (immutable) abs source path of the file's root, e.g.
                                            - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene.mkv

            dst (FilmPath):                 Desired abs path to this file's new root, e.g.
                                            - /volumes/movies/HD/Avatar (2009) Bluray-1080p.mkv

            title (str):                    Ref to film.title.

            title_the (str):                Ref to film.title.the.

            year (str):                     Ref to film.year.
            
            tmdb (TMDb.Result):             Ref to film.tmdb.

            edition (str):                  Special edition.

            media (Media):                  Original release media (see enums.Media)
            
            mediainfo (libmediainfo):       mediainfo derived from libmediainfo

            resolution (Resolution):        Original pixel depth (see enums.Resolution)

            is_hdr (bool):                  Indicates whether this version is HDR.
            
            hdr (str):                      Returns 'HDR" if is_hdr is True.

            is_proper (bool):               Indicates whether this version is a proper release.

            film:                           Parent Film containing the file.

            new_name (Path):                New name of the file, including file extension.
            new_name_lazy (Path):           Lazy (cached) copy of new_name

            ignore_reason (IgnoreReason):   If applicable, a reason describing why this film was ignored.

            is_wanted (bool):               Returns True if the file is valid and wanted.

            is_subtitle (bool):             Returns True if the file is a subtitle.

            did_move (bool):                Returns true when the file has been successfully moved.
                                            Set manually from the return value (T/F) of Move.safe().
            
            is_duplicate (bool):            Returns True if this file is marked as a duplicate of another.

            duplicate_action (Should):      Returns None, or one of Should enum to describe what should happen when
                                            this file encounters a duplicate.

            upgrade_reason (UpgradeReason): Returns the reason this file should be upgraded, or an empty string.
        """
        
        def __init__(self, path: Union[str, Path, 'FilmPath'], film: 'Film'):

            super().__init__(path, origin=film.origin)

            self._src = Path(self)
            self.film: Film = film
            self.did_move: bool = False
            self.is_duplicate: bool = False
            self.duplicate_action: Should or None = None
            self.upgrade_reason: UpgradeReason = None
        
        def __repr__(self):
            return f"File('{self}')\n" + str(tuple([str(x) for x in [
                self.title,
                self.year,
                self.media.display_name,
                self.resolution.display_name,
                self.hdr,
                self.edition,
                'Proper ' if self.is_proper else None,
                self.tmdb.id] if x]))
            
        @lazy
        def src(self) -> FilmPath:
            return self._src
        
        @property
        def dst(self) -> Path:
            # If 'rename_only' is enabled, we need to override the configured
            # destination dir with the source dir.
            if config.rename_only is True:
                return self.src.parent / self.new_name
            elif config.use_folders:
                return (config.destination_dir(self.resolution) / 
                        self.film.new_name /
                        self.new_name)
            else:
                return (config.destination_dir(self.resolution) /
                        self.new_name)
            
        @lazy
        def title(self) -> str:
            return self.film.title

        @property
        def title_the(self) -> str:
            return self.film.title_the

        @lazy
        def year(self) -> int:
            return self.film.year
        
        @property
        def tmdb(self) -> TMDb.Result:
            return self.film.tmdb
        
        @lazy
        def edition(self) -> str:
            return Parser(self.filmrel).edition

        @lazy
        def media(self) -> Media:
            return Parser(self.filmrel).media
        
        @lazy
        def part(self) -> str:
            return Parser(self.name).part
        
        @lazy
        def hdr(self) -> bool:
            return 'HDR' if self.is_hdr else ''
        
        @lazy
        def is_hdr(self) -> bool:
            return Parser(self.filmrel).is_hdr
        
        @lazy
        def is_proper(self) -> bool:
            return Parser(self.filmrel).is_proper

        @lazy
        def mediainfo(self) -> Union['Track', None]:
            if not self.is_video_file or not self.exists():
                return None

            media_info = MediaInfo.parse(str(self), library_file=str(
                Path(__file__).resolve().parent / 'libmediainfo.0.dylib'))

            for track in media_info.tracks:
                if track.track_type == 'Video':
                    return track
                
        @lazy
        def resolution(self) -> Resolution:
            return Parser(self.filmrel, mediainfo=self.mediainfo).resolution
        
        @property
        def new_name(self) -> Path:
            name = Format.Name(self)
            self.new_name_lazy = name
            return f'{name.filename}{self.suffix}'

        @lazy
        def new_name_lazy(self) -> Path:
            # Cached copy of new_name
            return self.new_name
        
        @lazy
        def ignore_reason(self) -> IgnoreReason:
            i = IgnoreReason
            if is_sys_file(self): return i.SYS
            elif re.search(patterns.SAMPLE, str(self.filmrel)): return i.SAMPLE
            elif Info.has_ignored_string(self.src): return i.IGNORED_STRING
            elif not self.exists(): return i.DOES_NOT_EXIST
            elif not Info.has_valid_ext(self): return i.INVALID_EXT
            elif not Info.is_acceptable_size(self): return i.TOO_SMALL
            else: return None
            
        @lazy
        def is_wanted(self) -> bool:
            # If the file doesns't have an ignore reason, we
            # can assume it is wanted.
            return not self.ignore_reason

        @lazy
        def is_subtitle(self):
            return self.suffix.lower() in ['.srt', '.sub']
