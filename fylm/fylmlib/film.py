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
# import concurrent.futures
from copy import copy
from pathlib import Path
from typing import Union
from timeit import default_timer as timer

from pymediainfo import MediaInfo
from lazy import lazy
import nest_asyncio

import fylmlib.config as config
import fylmlib.patterns as patterns
from fylmlib.tools import *
from fylmlib.enums import *
from fylmlib import FilmPath
from fylmlib import Console
from fylmlib import Parser
from fylmlib import Format
from fylmlib import TMDb
from fylmlib import Info
from fylmlib import IO

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

        duplicates ([Film])             List of duplicate film objects on the dst dirs.
        
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
                
        wanted_files ([Film.File]):     A subset of files that have wanted file extensions.

        bad_files ([Film.File]):        A subset of files that are not wanted.

        should_ignore (bool):           Returns True if this film should be ignored.

        ignore_reason (IgnoreReason):   If applicable, a reason describing why this film was ignored.

        should_hide (bool):             Return True if this Film should be hidden
                                        when printing to the console.
    """

    def __init__(self, path: Union[str, Path, 'FilmPath'], origin: 'Path' = None):
        
        super().__init__(path, origin=origin)
        
        self._src = Path(self)
        self.tmdb: TMDb.Result = TMDb.Result()
        self.tmdb_matches: [TMDb.Result] = []

    def __repr__(self):
        return f"Film('{self}')\n" + str(tuple([str(x) for x in [
            Path(self.title).name,
            self.year,
            self.tmdb.id] if x]))

    @property
    def bad_files(self) -> Iterable['Film.File']:
        return filter(lambda f: f.should_ignore, self.files)

    @property
    def dst(self) -> Path:
        root = (config.destination_dir(self.main_file.resolution)
                if not config.rename_only
                else self.src.parent)
        return (root / self.new_name)
    
    @property
    def duplicates(self) -> ['Film']:
        from fylmlib import Duplicates
        return Duplicates(self)

    @lazy
    def new_name(self) -> Path:
        name = Format.Name(self.main_file)
        return name.dirname if config.use_folders else name.filename

    @lazy # @Override(files)
    def files(self) -> ['Film.File']:
        if super().files:
            return sorted([Film.File(f, film=self) for f in super().files],
                             key=lambda f: f.size.value, reverse=True)
        else:
            return [Film.File(self, film=self)]

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
        elif not Info.is_acceptable_size(self): return i.TOO_SMALL
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
        
    def move(self) -> 'Film':
        """Moves all the film's wanted files.

        Returns:
            Film: A new copy of this film with updated path.
        """
        # Move all wanted files and update files
        self.files = [f.move() for f in self.wanted_files]
        success = all([f.did_move for f in self.files])
        if success:
            self.setpath(Path(self.dst))
        return self
        
    def rename(self) -> 'Film':
        """Renames all the film's wanted files.

        Returns:
            Film: A new copy of this film with updated path.
        """
        # Rename all wanted files and update files
        assert(self.dst == self.src.parent / self.new_name)
        return self.move()

    async def search_tmdb(self):
        """Performs a TMDb search on the existing film.

        Calls the tmdb.search() method, passing the current film
        as params. If a result is found, the current film's properties
        are updated with the values from TMDb.
        """
        
        # Don't perform a lookup if it should be ignored.
        if self.should_ignore:
            return

        # Only perform lookups if TMDb searching is enabled.
        if config.tmdb.enabled is False:
            return
    
        # Perform the search and save the first 10 sresults to the matches list.
        # If ID is not None, search by ID.
        Console.debug(f"Searching '{self.title}'")
        start = timer()
        self.tmdb_matches = await TMDb.Search(self.title, self.year, self.tmdb.id).do()
        best_match = first(iter(self.tmdb_matches or []), None)
        if best_match:
            # If we find a result, update title and year.
            best_match.update(self)
        else:
            # If not, we update the ignore_reason
            self.ignore_reason = IgnoreReason.NO_TMDB_RESULTS
        
        end = timer()
        if round(end - start) > 1:
            Console.slow(f"Took a long time searching for '{self.title}'", end - start)

    def search_tmdb_sync(self):
        """A synchronous wrapper for search_tmdb().
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.search_tmdb())

    @property
    def should_hide(self) -> bool:
        if not config.hide_bad:
            return False
        return self.should_ignore

    @property
    def should_ignore(self) -> bool:
        # In automatic mode, we can't redeem a bad match, so we must skip.
        if not config.interactive:
            return self.ignore_reason is not None
        # In interactive mode, we can still lookup a file even if it's
        # missing year, too small, or didn't find an automatic match.
        else:
            return self.ignore_reason and not self.ignore_reason in [
                IgnoreReason.UNKNOWN_YEAR,
                IgnoreReason.TOO_SMALL,
                IgnoreReason.NO_TMDB_RESULTS]

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
                if re.search(patterns.THE_PREFIX_SUFFIX, self.title) 
                else self.title)

    @property
    def video_files(self) -> Iterable['Film.File']:
        return filter(lambda f: Info.is_video_file(f), self.files)

    @property
    def wanted_files(self) -> Iterable['Film.File']:
        return filter(lambda f: not f.should_ignore, self.files)
    
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

        Invalid or unwanted files can still be mapped to a File object, but self.should_ignore will return False.

        Attributes:

            FIXME: Do we still need action?
            action (Should):                Action to be taken against this file, if any. Most often set
                                            as a result of duplicate checking.
            
            did_move (bool):                Returns true when the file has been successfully moved.
                                            Set manually from the return value (T/F) of IO.move().

            dst (FilmPath):                 Desired abs path to this file's new root, e.g.
                                            - /volumes/movies/HD/Avatar (2009) Bluray-1080p.mkv

            duplicates: ([Film.File])       List of duplicate files and relationships

            edition (str):                  Special edition.

            film:                           Parent Film containing the file.
            
            hdr (str):                      Returns 'HDR" if is_hdr is True.

            ignore_reason (IgnoreReason):   If applicable, a reason describing why this film was ignored.

            is_hdr (bool):                  Indicates whether this version is HDR.

            is_proper (bool):               Indicates whether this version is a proper release.

            is_subtitle (bool):             Returns True if the file is a subtitle.

            media (Media):                  Original release media (see enums.Media)
            
            mediainfo (libmediainfo):       mediainfo derived from libmediainfo

            new_name (Path):                New name of the file, including file extension.
            
            part (int):                     Part number of the file if it has multiple parts.

            resolution (Resolution):        Original pixel depth (see enums.Resolution)
            
            should_ignore (bool):           Returns True if this film should be ignored.
        
            src (FilmPath):                 Original (immutable) abs source path of the file's root, e.g.
                                            - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene.mkv

            title (str):                    Ref to film.title.

            title_the (str):                Ref to film.title.the.
            
            tmdb (TMDb.Result):             Ref to film.tmdb.

            year (str):                     Ref to film.year.
        """
        
        def __init__(self, path: Union[str, Path, 'FilmPath'], film: 'Film', origin: 'Path' = None):

            super().__init__(path, origin=origin or film.origin)

            self._src = Path(self)
            self.action: Should = None
            self.film: Film = film
            self.did_move: bool = False
        
        def __repr__(self):
            return f"File('{self}')\n" + str(tuple([str(x) for x in [
                Path(self.title).name,
                self.year,
                self.media.display_name,
                self.resolution.display_name,
                self.hdr,
                self.edition,
                'Proper ' if self.is_proper else None,
                self.tmdb.id] if x]))
        
        # @overrides(__reduce__)
        def __reduce__(self):
            
            lazy.invalidate(self.film, 'main_file')

            args = {**{'_parts': self._parts}, **self.__dict__}
            return (self.__class__._from_kwargs, tuple(args.items()))
        
        # @Override(_from_kwargs) 
        @classmethod
        def _from_kwargs(cls, *args):

            # Support init from kwargs passed in a tuple from reduce.

            try:
                kwargs = dict(*args)
            except:
                kwargs = dict(args)

            new = cls(super().__new__(
                cls, *kwargs['_parts']), 
                      origin=kwargs['_origin'],
                      film=kwargs['film'])
            new.__dict__ = {**new.__dict__, **kwargs}
            return new

        @property
        def dst(self) -> Path:
            root = (config.destination_dir(self.resolution) 
                    if not config.rename_only 
                    else self.film.src.parent)
            if config.use_folders:
                return (root / self.film.new_name / self.new_name)
            else:
                return (root / self.new_name)     
                
        @property
        def duplicates(self) -> ['Film']:
            return self.film.duplicates.files
        
        @lazy
        def edition(self) -> str:
            return Parser(self.filmrel).edition

        @lazy
        def hdr(self) -> bool:
            return 'HDR' if self.is_hdr else ''
        
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
        def is_hdr(self) -> bool:
            return Parser(self.filmrel).is_hdr

        @lazy
        def is_proper(self) -> bool:
            return Parser(self.filmrel).is_proper

        @lazy
        def is_subtitle(self):
            return self.suffix.lower() in constants.SUB_EXTS

        @lazy
        def media(self) -> Media:
            return Parser(self.filmrel).media

        @lazy
        def mediainfo(self) -> Union['Track', None]:
            if 'mediainfo' in self.__dict__:
                return self.mediainfo
            loop = asyncio.get_event_loop()
            if loop.is_running():
                nest_asyncio.apply(loop)
            return loop.run_until_complete(self.mediainfo_async())

        async def mediainfo_async(self) -> Union['Track', None]:
            if not self.is_video_file or not self.exists():
                return None

            media_info = MediaInfo.parse(str(self), library_file=str(
                Path(__file__).resolve().parent / 'libmediainfo.0.dylib'))

            for track in media_info.tracks:
                if track.track_type == 'Video':
                    return track
                
        def move(self) -> 'Film.File':
            """Moves the file.

            Returns:
                File: A new copy of this file with updated path.
            """
            self.did_move = IO.move(self.src, self.dst)
            if self.did_move:
                self.setpath(Path(self.dst))
            return self

        @lazy
        def new_name(self) -> Path:
            name = Format.Name(self)
            return f'{name.filename}{self.suffix}'
        
        @lazy
        def part(self) -> str:
            return Parser(self.name).part
        
        def rename(self) -> 'Film.File':
            """Renames the file.

            Returns:
                File: A new copy of this file with updated path.
            """
            # Rename all wanted files and update files
            assert(self.dst == self.src.parent / self.new_name)
            return self.move()
                
        @lazy
        def resolution(self) -> Resolution:
            res = Parser(self.filmrel).resolution
            if res is not Resolution.UNKNOWN:
                return res
            elif self.mediainfo:
                try:
                    if self.mediainfo.width == 3840: return Resolution.UHD_2160P
                    elif self.mediainfo.width == 1920: return Resolution.HD_1080P
                    elif self.mediainfo.width == 1280: return Resolution.HD_720P
                    elif self.mediainfo.width == 1024: return Resolution.SD_576P
                    elif self.mediainfo.width == 852: return Resolution.SD_480P
                except:
                    pass
            return Resolution.UNKNOWN

        @property
        def should_ignore(self) -> bool:
            # If the file doesns't have an ignore reason, we
            # can assume it is wanted.
            return self.ignore_reason

        @lazy
        def src(self) -> FilmPath:
            return self._src

        @lazy
        def title(self) -> str:
            return self.film.title

        @property
        def title_the(self) -> str:
            return self.film.title_the

        @property
        def tmdb(self) -> TMDb.Result:
            return self.film.tmdb

        @lazy
        def year(self) -> int:
            return self.film.year
