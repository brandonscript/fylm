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

        src (Filmpath):                 Original (immutable) abs source path of the film's root, e.g.
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene or
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene.mkv

        dst (Filmpath):                 Desired abs path to this film's new root, e.g.
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
        
        new_name (Path):                New name of the film, including the file extension if applicable.

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
        # self._parser = Parser(self.main_file.filmrel if self.exists() else self)

    @property
    def bad_files(self) -> Iterable['Film.File']:
        return iter(filter(lambda f: not f.is_wanted_file, self.files))

    @property
    def dst(self) -> Path:
        # If 'rename_only' is enabled, we need to override the configured
        # destination dir with the source dir.
        if config.rename_only is True:
            return self.src.parent / self.new_name
        else:
            return config.destination_dir(self.main_file.resolution or None) / self.new_name
        
    @property
    def new_name(self) -> Path:
        name = Format.Name(self.main_file)
        self.new_name_lazy = name
        return name.parent if config.use_folders else name
    
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
        
        # TODO: Re-implement this in processor
        """if self.ignore_reason is i.TOO_SMALL:
            return f"{self.ignore_reason.str} - {formatter.pretty_size(self.size)}"
        return self.ignore_reason.str if self.ignore_reason else None"""

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
        return iter(filter(lambda f: f.is_wanted_file, self.files))
    
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

        Invalid or unwanted files can still be mapped to a File object, but self.is_wanted_file will return False.

        Attributes:
        
            title (str):                Title of the parent Film object.

            title_the (str):            Title, The of the parent Film object.

            year (str):                 Year of the parent Film object.

            edition (str):              Special edition.

            media (Media):              Original release media (see enums.Media)
            
            resolution (Resolution):    Original pixel depth (see enums.Resolution)

            is_hdr (bool):              Indicates whether this version is HDR.

            is_proper (bool):           Indicates whether this version is a proper release.

            film:                       Parent Film containing the file.

            original_path (str):        Original (immutable) abs source path of file, e.g.
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264/Avatar.2009.BluRay.1080p.x264.mkv

            original_rel_path (str):    Original (immutable) relative source path of file, e.g.
                                         - Avatar.2009.BluRay.1080p.x264/Avatar.2009.BluRay.1080p.x264.mkv

            original_filename (str):    Original (immutable) filename of file, e.g.
                                         - Avatar.2009.BluRay.1080p.x264-Scene.mkv

            current_path (str):         Current abs source path of file, e.g.
                                         - /volumes/movies/HD/Avatar (2009)/Avatar (2009) Bluray-1080p.mkv or
                                         - /volumes/downloads/Avatar.2009.BluRay.1080p.x264/Avatar.2009.BluRay.1080p.x264.mkv

            destination_path (str):     Desired abs path to this file should exist when moved
                                        renamed, e.g.
                                         - /volumes/movies/HD/Avatar (2009)/Avatar (2009) Bluray-1080p.mkv

            destination_root_dir (str): Desired root path based on the file's resolution, e.g.
                                         - /volumes/movies/HD 
                                         - /volumes/movies/SD

            destination_rel_path (str): Desired renamed path to file relative to destination_root_dir. This may be
                                        If config.use_folders is True, this will be in the form of {folder}/{file}. 
                                        If False, it will be just the new filename (and equal to new_filename).
                                         - Avatar (2009)/Avatar (2009) Bluray-1080p.mkv
                                         - Avatar (2009) Bluray-1080p.mkv

            new_filename (str):         New filename generated using the defined templating pattern
                                        in config.rename_pattern.file. Supports an overload to force a different
                                        file extension.

            new_dirname (str):          New dirname generated using the defined templating pattern
                                        in config.rename_pattern.folder.

            new_filename_stem (str):    Returns the new file name, excluding the file extension.

            mediainfo (libmediainfo):   mediainfo derived from libmediainfo

            is_wanted_file (bool):            Returns True if the file is valid and wanted.

            is_video (bool):            Returns True if the film is a file and has a valid video file extension.

            is_subtitle (bool):         Returns True if the file is a subtitle.

            is_duplicate (bool):        Returns True if this file is marked as a duplicate of another.

            duplicate (Should or None): Returns None, or one of Should enum to describe what should happen when
                                        this file encounters a duplicate.

            upgrade_reason (str):       Returns the reason this file should be upgraded, or an empty string.
            
            did_move (bool):            Returns true when the file has been successfully moved.
        """
        
        def __init__(self, path: Union[str, Path, 'FilmPath'], film: 'Film'):

            super().__init__(path)

            self._src = Path(self)
            self.film: Film = film
            self.did_move: bool = False
            self.is_duplicate: bool = False
            self.duplicate: Should or None = None
            self.upgrade_reason: str = ''
            
        @property
        def title(self) -> str:
            return self.film.title

        @property
        def title_the(self) -> str:
            return self.film.title_the

        @property
        def year(self) -> int:
            return self.film.year
        
        @lazy
        def edition(self) -> str:
            return Parser(self.filmrel).edition

        @lazy
        def media(self) -> Media:
            return Parser(self.filmrel).media
        
        @lazy
        def part(self) -> Media:
            return Parser(self.filmrel).part
        
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
        def new_filename(self, ext: str = None) -> str:
            """Builds a new filename for this file.

            Args:
                ext (str, optional): Overload the extension of this file. Defaults to ''.
                                     Must be preceded by a ., e.g. '.mkv'

            Returns:
                str: The new filename.
            """
            # Ensure the passed ext string always starts with a single .
            ext = '.' + ext.lstrip('.') if ext else self.ext
            return Path(formatter.new_basename(self, Rename.FILE).build()).with_suffix(ext)._str
        
        @property
        def new_filename_stem(self) -> str:
            return Path(self.new_filename).stem

        @property
        def new_dirname(self) -> str:
            return formatter.new_basename(self, Rename.DIR).build()

        @property
        def destination_path(self) -> str:
            # If 'rename_only' is enabled, we need to override the configured
            # destination dir with the source dir.
            return str(PurePath(
                self.original_path if config.rename_only else Film.Utils.destination_root_dir(self), 
                self.destination_rel_path))

        @property
        def destination_rel_path(self) -> str:
            return self.new_filename if config.use_folders is False else str(PurePath(
                self.new_dirname, self.new_filename))
            
        @lazy
        def is_wanted_file(self) -> bool:
            # A valid file must have a valid extension
            return Info.is_wanted_file(self)

        @property
        def is_subtitle(self):
            return self.ext == '.srt' or self.ext == '.sub'

    class zInfo:
        # TODO: Most of these should be in FilmPath or ops
        """A collection of helper functions for Film objects."""

        
            
        

        

        

        
