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
from pathlib import Path, PurePath
from typing import Union

from pymediainfo import MediaInfo
from lazy import lazy

from fylmlib.enums import *
import fylmlib.config as config
import fylmlib.parser as Parser
import fylmlib.formatter as formatter
import fylmlib.patterns as patterns
import fylmlib.tmdb as tmdb
import fylmlib.operations as ops

class Film:
    """A Film object contains basic details about the a film, references to the individual 
    File objects it contains (or just one, if it's a single file). Using regular expressions 
    and themoviedb.org APIs, it can intelligently identify key attributes of a film from 
    a standard file naming convention.

    Attributes:

        original_path (str):        Original (immutable) abs source path of film's root dir,
                                    or file, if it's a file, e.g.
                                     - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene

        original_basename (str):    Original (immutable) basname of film's root dir,
                                    or file, if it's a file, e.g.
                                     - Avatar.2009.BluRay.1080p.x264-Scene or
                                     - Avatar.2009.BluRay.1080p.x264-Scene.mkv

        current_path (str):         Current abs source path of film's root dir,
                                    or file, if it's a file, e.g.
                                     - /volumes/movies/HD/Avatar (2009) or
                                     - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene

        destination_path (str):     Desired abs path to this film's new root dir, 
                                    or file, if using file-based naming, e.g.
                                     - /volumes/movies/HD/Avatar (2009) or
                                     - /volumes/movies/HD/Avatar (2009) Bluray-1080p.mkv

        title (str):                Title of the film.

        title_the (str):            For titles that begin with 'The', move it to the
                                    end of the title, e.g. 'Chronicles of Narnia, The'.

        year (int):                 Primary release year.

        tmdb_id (int):              TMDb ID for film.

        tmdb_verified (bool):       Set to True once a TMDb result is verified in interactive mode.

        tmdb_similarity (float):    Float value between 0 and 1 representing the Levenshtein 
                                    distance similarity between parsed title and proposed title.

        tmdb_matches (list):        A list of TmdbResult possible matches from TMDb, 
                                    ordered most to least likely to match.

        overview (str):             A short description of the film from TMDb.

        poster_url (str):           URL for the TMDb film poster.

        size (int):                 Size of film (file or dir) in bytes.

        is_file (bool):             Returns True if the path loaded is a file.

        is_dir (bool):              Returns True if the path loaded is a dir.

        exists (bool):              Returns True if the path loaded exists, otherwise sets 
                                    the ignore_reason and returns False.

        main_file (Film.File):      Returns the largest wanted file in a Film folder (or if there 
                                    is only a single file, that file). In most cases, this will be
                                    the primary video file
                                    Be careful when using this, as a folder could
                                    have multiple versions of the same film.

        all_files (list):           A list of all Film.File objects in the film's folder, or a
                                    list of exactly one if it's a file.

        wanted_files (list):        A subset of all_files that have wanted file extensions.

        video_files (list):          A subset of all_files that have a valid video extension.

        bad_files (list):           A subset of all_files that are not wanted.

        duplicate_files (list):     A list of Film objects from the cached list of 
                                    existing films that are duplicates of this film.

        should_ignore (bool):       Returns True if this film should be ignored and Updates
                                    ignore_reason with an explanation, if necessary.

        ignore_reason (str):        If applicable, a reason describing why this film was ignored.

        should_hide (bool):         Return True if this Film should be hidden
                                    when printing to the console.
    """

    def __init__(self, current_path: Union[str, Path, 'FilmPath']):        
        self._original_path = current_path
        self.current_path = current_path
        self._title = None
        self._year = None
        self.tmdb_id: int = None
        self.tmdb_verified: bool = False
        self.tmdb_similarity: float = 0
        self.tmdb_matches: [tmdb.TmdbResult] = []
        self.overview: str = ''
        self.poster_url: str = None
        self._ignore_reason: IgnoreReason = None
        self.parser = Parser(self.main_file.current_path)

    # title needs a getter and setter, because a TMDb search can update it
    @property
    def title(self) -> str:
        if not self._title:
            self._title = self.parser.title
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def title_the(self) -> str:
        return (f'{formatter.strip_the(self.title)}, The'
                if re.search(patterns.begins_with_or_comma_the, self.title) else self.title)

    # year needs a getter and setter, because a TMDb search can update it
    @property
    def year(self) -> int:
        if not self._year:
            self._year = self.parser.year
        return self._year
    
    @year.setter
    def year(self, value: str) -> int:
        self._year = value

    @property
    def original_path(self) -> str:
        return self._original_path

    @lazy
    def original_basename(self) -> str:
        return Path(self.current_path).name

    @property
    def destination_path(self) -> str:
        # If 'rename_only' is enabled, we need to override the configured
        # destination dir with the source dir.
        if config.rename_only is True:
            return self.original_path
        return os.path.normpath(os.path.join(
            Film.Utils.destination_root_dir(self.main_file), 
            self.main_file.new_dirname if config.use_folders else None))
    
    @lazy
    def size(self) -> int:
        return ops.size(self.current_path)

    @lazy
    def is_file(self) -> bool:
        return Path(self.current_path).is_file()

    @lazy
    def is_dir(self) -> bool:
        return Path(self.current_path).is_dir()

    @property
    def exists(self) -> bool:
        # This should be called after should_ignore and before a file operation is performed,
        # but it is kept separate, because it is an expensive function.
        if not Path(self.current_path).exists():
            self._ignore_reason = IgnoreReason.NO_LONGER_EXISTS
            return False
        return True
 
    @property
    def main_file(self) -> 'Film.File':
        try:
            assert(self.all_files)
        except:
            raise AssertionError(f"'{self.current_path}'\ndoes not have any files.")
        return self.all_files[0]

    @property    
    def all_files(self) -> ['Film.File']:
        # Get all files, map them to File(), then sort by size
        # inversely so that the largest file is first in the list
        # TODO: This size calc/map can be replaced completely with FilmPath
        found = [Film.File(p, self) for p in ops.dirops.find_deep(self.current_path)]
        return list(self.Utils.sort_files(found))

    @property
    def video_files(self) -> ['Film.File']:
        return list(self.Utils.video_files(self.wanted_files))

    @property
    def wanted_files(self) -> ['Film.File']:
        return list(self.Utils.wanted_files(self.all_files))

    @property
    def bad_files(self) -> ['Film.File']:
        return list(self.Utils.bad_files(self.all_files))

    @lazy
    def duplicate_files(self) -> ['Film.File']:
        # Import duplicates here to avoid circular imports.
        import fylmlib.duplicates.find as find
        return find(self)

    @property
    def should_ignore(self) -> bool:
        if re.search('^_UNPACK_', self.original_basename):
            self._ignore_reason = IgnoreReason.UNPACKING

        elif ops.FilmPath.Utils.has_ignored_string(self.original_path):
            self._ignore_reason = IgnoreReason.IGNORED_STRING

        elif bool(re.search(patterns.tv_show, self.original_basename)):
            self._ignore_reason = IgnoreReason.TV_SHOW

        elif self.is_file and not self.main_file.is_video:
            self._ignore_reason = IgnoreReason.INVALID_EXT

        elif self.is_dir and not self.video_files:
            self._ignore_reason = IgnoreReason.NO_VIDEO_FILES

        elif bool(re.search(patterns.tv_show, self.original_basename)):
            self._ignore_reason = IgnoreReason.TV_SHOW

        elif self.title is None:
            self._ignore_reason = IgnoreReason.UNKNOWN_TITLE

        elif self.year is None and (config.force_lookup is False or config.tmdb.enabled is False):
            self._ignore_reason = IgnoreReason.UNKNOWN_YEAR

        elif len(self.video_files) > 0 and self.size < Film.Utils.is_acceptable_size(self.main_file):
            self._ignore_reason = IgnoreReason.SIZE_TOO_SMALL

        return self._ignore_reason is not None

    @property
    def ignore_reason(self) -> Union[str, None]:
        if self._ignore_reason is IgnoreReason.SIZE_TOO_SMALL:
            return f"{self._ignore_reason.str} - {formatter.pretty_size(self.size)}"
        return self._ignore_reason.str if self._ignore_reason else None

    @property
    def should_hide(self) -> bool:
        if (self.should_ignore is True and config.interactive is True
                # In interactive mode, these three exceptions should be ignored because the
                # user may want to manually match them anyway.
                and not self.ignore_reason is IgnoreReason.UNKNOWN_TITLE
                and not self.ignore_reason is IgnoreReason.UNKNOWN_YEAR
                and not self.ignore_reason is IgnoreReason.SIZE_TOO_SMALL):
            return True
        elif self.should_ignore is True and config.interactive is False and config.hide_ignored is True:
            return True
        else:
            return False

    def search_tmdb_sync(self):
        """A synchronous wrapper for search_tmdb().
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.search_tmdb())

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
        self.tmdb_matches = await tmdb.search(self.tmdb_id or self.title, None if self.tmdb_id else self.year)
        best_match = next(iter(self.tmdb_matches or []), None)
        if best_match is not None:
            # If we find a result, update title, tmdb_id, year, and the tmdb_similarity.
            self.update_with_match(best_match)
        else:
            # If not, we update the ignore_reason
            self._ignore_reason = IgnoreReason.NO_TMDB_RESULTS

    def update_with_match(self, match: 'TmdbResult'):
        """Updates all of this film's properties witch those 
        from a TmdbResult match object.

        Args:
            match (TmdbResult): Search result as a TmdbResult object.
        """
        self.title = match.proposed_title
        self.year = match.proposed_year
        self.overview = match.overview
        self.poster_url = match.poster_url
        self.tmdb_id = match.tmdb_id
        self.tmdb_similarity = match.tmdb_similarity  

    class File:
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

        Invalid or unwanted files can still be mapped to a File object, but self.is_valid will return False.

        Attributes:
        
            title (str):                Title of the parent Film object.

            title_the (str):            Title, The of the parent Film object.

            year (str):                 Year of the parent Film object.

            edition (str):              Special edition.

            media (Media):              Original release media (see enums.Media)
            
            resolution (Resolution):    Original pixel depth (see enums.Resolution)

            is_hdr (bool):              Indicates whether this version is HDR.

            is_proper (bool):           Indicates whether this version is a proper release.

            parent_film:                Parent Film containing the file.

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

            ext (str):                  File extension.

            size (int):                 Size of file, in bytes.

            mediainfo (libmediainfo):   mediainfo derived from libmediainfo

            is_valid (bool):            Returns True if the file is valid and wanted.

            is_video (bool):            Returns True if the film is a file and has a valid video file extension.

            is_subtitle (bool):         Returns True if the file is a subtitle.

            is_duplicate (bool):        Returns True if this file is marked as a duplicate of another.

            duplicate (Should or None): Returns None, or one of Should enum to describe what should happen when
                                        this file encounters a duplicate.

            upgrade_reason (str):       Returns the reason this file should be upgraded, or an empty string.
            
            did_move (bool):            Returns true when the file has been successfully moved.
        """

        def __init__(self, current_path: str, parent_film: 'Film'):
            self._original_path: str = current_path
            self.current_path: str = current_path
            self.parent_film: Film = parent_film
            self.did_move: bool = False
            self.is_duplicate: bool = False
            self.duplicate: Should or None = None
            self.upgrade_reason: str = ''
            
        @property
        def title(self) -> str:
            return self.parent_film.title

        @property
        def title_the(self) -> str:
            return self.parent_film.title_the

        @property
        def year(self) -> int:
            return self.parent_film.year
        
        @lazy
        def edition(self) -> str:
            return self.parent_film.parser.edition

        @lazy
        def media(self) -> Media:
            return self.parent_film.parser.media
        
        @lazy
        def is_hdr(self) -> bool:
            return self.parent_film.parser.is_hdr
        
        @lazy
        def is_proper(self) -> bool:
            return self.parent_film.parser.is_proper

        @lazy
        def mediainfo(self) -> Union['Track', None]:
            if not self.is_video:
                return None

            media_info = MediaInfo.parse(self.current_path, library_file=str(PurePath(
                Path(__file__).resolve().parent,
                'libmediainfo.0.dylib')))

            for track in media_info.tracks:
                if track.track_type == 'Video':
                    return track
                
        @lazy
        def resolution(self) -> Resolution:
            if not self.parent_film.parser.mediainfo:
                self.parent_film.parser.mediainfo = self.mediainfo
            return self.parser.resolution

        @property
        def original_path(self) -> str:
            return self._original_path
        
        @lazy
        def original_filename(self) -> str:
            return Path(self.original_path).name

        @lazy
        def original_rel_path(self) -> str:
            return str(PurePath(Path(self.original_filename).parent.name, Path(self.original_filename).name))

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
        def ext(self) -> str:
            return Path(self.current_path).suffix if self.is_file else None

        @lazy
        def size(self) -> int:
            return ops.size(self.current_path)

        @lazy
        def is_file(self) -> bool:
            return Path(self.current_path).is_file()
            
        @lazy
        def is_valid(self) -> bool:
            # A valid file must have a valid extension
            return (Film.Utils.has_valid_ext(self)

            # It must not contain an ignored string (e.g. 'sample')
            and not ops.FilmPath.Utils.has_ignored_string(self.original_path)

            # It must be large enough
            and Film.Utils.is_acceptable_size(self))

        @property
        def is_video(self) -> bool:
            return self.is_file and any([self.ext in config.video_exts])

        @property
        def is_subtitle(self):
            return self.ext == '.srt' or self.ext == '.sub'

    class Utils:
        """A collection of helper functions for Film objects."""
        
        @classmethod
        def sort_files(cls, files: ['Film.File']) -> ['Film.File']:
            """Sort a list of files by size, reverse

            Returns:
                A sorted list of files.
            """
            return sorted(files, key=lambda f: f.size, reverse=True)

        @classmethod
        def wanted_files(cls, files: ['Film.File']) -> ['Film.File']:
            """Filter valid files from a list of files.

            Args:
                files: [(Film.File)]
            Returns:
                A list of valid files.
            """

            # Sort by file size, in reverse, so the largest file is first
            return filter(lambda f: f.is_valid, files)

        @classmethod
        def video_files(cls, files: ['Film.File']) -> ['Film.File']:
            """Filter all valid feature film files from the list of films.
            
            Returns:
                Array of Film.File objects that are valid video files."""

            return filter(lambda f: f.is_video, files)
            
            # TODO: Do we need this functionality somewhere else? Or is this covered by
            # ignore reason?
            # return list(filter(lambda f: f.is_video and (
            #         f.year is not None 
            #         or f.resolution is not None 
            #         or f.media is not None), files))

        @classmethod
        def bad_files(cls, files: ['Film.File']) -> ['Film.File']:
            """Filter a list of invalid files from a list of files.

            Args:
                files: [(Film.File)]
            Returns:
                A list of invalid files.
            """
            print('bad_files', files)
            return filter(lambda f: not f.is_valid, files)

        @classmethod
        def has_valid_ext(cls, file: 'Film.File') -> bool:
            """Check if file has a valid extension.

            Check the specified file's extension against config.video_exts and config.extra_exts.

            Args:
                file: (Film.File)
            Returns:
                True if the file has a valid extension, else False.
            """
            return file.is_file and (file.ext.lower() in 
                        config.video_exts + config.extra_exts)

        @classmethod
        def is_acceptable_size(cls, file: 'Film.File') -> bool:
            """Determine if a file_path is an acceptable size.

            Args:
                file: (Film.File)
            Returns:
                True, if the file is an acceptable size, else False.
            """
            return file.size >= cls.min_filesize(file)

        @classmethod
        def min_filesize(cls, file: 'Film.File') -> int:
            """Determine the minimum filesize for the resolution for file path.

            Args:
                file: (str, utf-8) path to file.
            Returns:
                int: The minimum file size in bytes, or default in bytes
                     if resolution could not be determined.
            """

            # If the file is valid but not a video, we can't expect 
            # it to be too large (e.g., .srt)
            if not file.is_video:
                return 10
            
            # If the config is simple, just an int, return that in MB
            min = config.min_filesize
            if isinstance(min, int):
                return min

            # If the min filesize is not an int, we assume
            # that it is an Addict of resolutions.
            size = min.default
            
            if file.resolution is None:
                size = min.default
            elif file.resolution.value > 3: # 3 and higher are SD res
                size = min.SD
            else:
                size = min[file.resolution.display_name]                

            # If we're running tests, files are in MB instead of GB
            t = 1 if 'pytest' in sys.argv[0] else 1024
            return size * 1024 * t

        @classmethod
        def destination_root_dir(cls, file: 'Film.File') -> str:
            """Returns the destination root path based on the file's resolution.

            Args:
                file (Film.File): File to check

            Returns:
                str: A root path string, e.g. /volumes/movies/HD or /volumes/movies/SD
            """
            try:
                # Resolution Enum values > 3 are all SD
                res_key = 'SD' if file.resolution.value > 3 else file.resolution.display_name
                return config.destination_dirs[res_key]
            except:
                return config.destination_dirs.default
