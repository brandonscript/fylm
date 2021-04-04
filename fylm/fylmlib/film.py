# -*- coding: future_fstrings -*-
# Copyright 2018 Brandon Shelley. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Film descriptor object.

    Film: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
import re
import sys
import itertools
import asyncio
import concurrent.futures

from pymediainfo import MediaInfo

import fylmlib.config as config
from fylmlib.parser import parser
import fylmlib.formatter as formatter
import fylmlib.patterns as patterns
import fylmlib.tmdb as tmdb
import fylmlib.operations as ops
from fylmlib.enums import Should

class Film:
    """An object that identifies and processes film attributes.

    Using a combination of regular expressions and intelligent
    algorithms, determine the most likely attributes that
    pertain to a film. Also supports a passthrough lookup method
    for searching TMDb.

    Attributes:
        title:              Film title.

        title_the:          For titles that begin with 'The', move it
                            to the end of the title: ', The'.

        tmdb_id:            TMDb ID for film.

        tmdb_verified:      Is set to True once a TMDb result is verified in
                            interactive mode.

        matches:            A list of possible TmdbResults, ordered most to
                            least likely to match.

        year:               Primary release year.

        overview:           A short description of the film.

        poster_path:        URL for the film poster.

        part:               Part number of the original film, either
                            either a number or roman numeral

        title_similarity:   Similarity between parsed title and TMDb
                            title.

        source_path:        Current source path of film.

        destination_path:   Parent (root) dir where we assume all files will be
                            moved, based on quality-based sorting defined
                            in config.destination_dirs. Occassionally this could
                            be out of sync with some of a film's files, depending
                            on the destination path configuration.      

        original_path:      (Immutable) original path of film.

        original_basename:  Original folder name (or filename without
                            extension) before it was renamed.

        size:               Size of file or folder contents belonging
                            to the film.

        new_basename:       Uses the configured templating pattern to
                            generate a new base object name.

        is_tv_show:         Returns true if the film is actually a
                            TV show.

        is_file:            Returns true if the film was loaded from
                            a file. If true, the all_valid_files will contain
                            exactly one file, at position 0.

        is_folder:          Returns true if the film was loaded from
                            a folder.

        # is_video_file:      Returns true if the film is a file and
        #                     has a valid video file extension.

        all_valid_files:    If the film is a dir, returns a list of
                            all valid FilmFile objects. Invalid files 
                            are omitted.

        video_files:        A subset of all_valid_files that contains a
                            list of unique film versions, as determined
                            by comparing media, resolution, format, and
                            edition.

        primary_file:       The primary video file in folder, defined as
                            the largest file in the list of video_files.

        duplicates:         Get a list of duplicates from the cached
                            list of existing films.

        should_ignore:      Returns true if the film should be ignored,
                            and sets the ignore_reason.

        should_skip:        Return true if the film should be skipped
                            when printing to the console.

        ignore_reason:      If applicable, the reason why this film
                            was ignored.
    """

    def __init__(self, source_path):
        self.source_path = source_path

        # Internal setter for `duplicates`.
        self._duplicate_files = None

        # Internal setter for `metadata`.
        self._metadata = None

         # Internal setter for `size`.
        self._size = None

        # Internal setter for `valid_files`.
        self._all_valid_files = None

        # Internal setter for (immutable) `original_path`.
        # Do not change even if the file is renamed, moved, or copied.
        self._original_path = source_path

        # Initialize remaining properties
        
        try:
            name_path = self.all_valid_files[0].source_path
        except IndexError:
            name_path = source_path

        # Initialize remaining properties
        self.title = parser.get_title(name_path)
        self.year = parser.get_year(name_path)
        self.overview = ''
        self.poster_path = None
        self.part = parser.get_part(name_path)
        self.tmdb_id = None
        self.tmdb_verified = False
        self.matches = []
        self.title_similarity = 0
        self.ignore_reason = None
        self.should_ignore

    @property
    def original_path(self):
        return self._original_path

    @property
    def original_basename(self):
        return os.path.basename(os.path.splitext(self.source_path)[0] if os.path.isfile(self.source_path) else self.source_path)

    @property
    def size(self):
        if not self._size:
            self._size = ops.size(self.source_path)
        return self._size

    @property
    def title_the(self):
        if re.search(patterns.begins_with_or_comma_the, self.title):
            return f'{formatter.strip_the(self.title)}, The'
        else:
            return self.title

    @property
    def is_tv_show(self):
        return bool(re.search(patterns.tv_show, self.original_basename))

    @property
    def is_file(self):
        return os.path.isfile(self.source_path)

    @property
    def is_folder(self):
        return os.path.isdir(self.source_path)

    # @property
    # def is_video_file(self):
    #     return any([self.all_valid_files[0].ext in config.video_exts]) if self.is_file else False

    @property
    def all_valid_files(self) -> ['Film.File']:
        if self._all_valid_files is None:
            # Initialize an empty array, just in case there are no valid files
            self._all_valid_files = []
            if self.is_file:
                # It's a file, we can just return an array with the file as its only value
                self._all_valid_files = [Film.File(self.source_path, self)]
            else:
                # Get all valid files
                self._all_valid_files = list(Film.File(path, self) for path in ops.dirops.get_valid_files(self.source_path))
                # Sort by size, inversely so that the largest file is first in the list
                self._all_valid_files.sort(key=lambda f: f.size, reverse=True)

        return self._all_valid_files

    @property
    def video_files(self) -> ['Film.File']:
        """For files that have already been moved and renamed (i.e., exist on
        the target filesystem), we need to accomodate configurations supporting 
        multiple versions of the same file under the same parent folder. 
        These could be multiple editions of the same film, or different 
        qualities or media of the same film. In all other cases, this will will be
        an array of one at index 0 (the main video file). This excludes sample files
        or others that have been poorly named.
        
        Returns:
            Array of Film.File objects that are valid video files."""
        
        return list(filter(lambda f:
            f.is_video and (f.year is not None or f.resolution is not None or f.media is not None),
        self.all_valid_files))

    @property
    def primary_file(self) -> 'Film.File':
        """Returns the largest video file in a Film folder (or if there is only
        a single file, that file).
        
        Returns:
            The largest video file in the Film object, or None if there are no valid files"""

        return self.video_files[0] if len(self.video_files) > 0 else None

    @property
    def duplicate_files(self) -> ['Film.File']:
        """An array of duplicate files in existing films.

        Returns:
            An array of duplicate films file objects.
        """
        # Import duplicates here to avoid circular imports.
        from fylmlib.duplicates import duplicates

        if self._duplicate_files is None:
            self._duplicate_files = duplicates.find(self)
        
        return self._duplicate_files

    @property
    def verified_duplicate_files(self) -> ['Film.File']:
        """An array of duplicate files in existing films that are 
        verified to exist on the filesystem.

        Returns:
            A an array of duplicate films file objects.
        """
        return list(filter(lambda d: os.path.exists(d.source_path), self.duplicate_files))

    @property
    def new_basename(self):
        r"""Build a new path name from the specified renaming pattern.

        If using a folder-based file structure, this will be the base
        folder for all files for this film, and will use the 
        rename_pattern.folder config. If using file-based structure, 
        this will derive from rename_pattern.file.

        Use regular expressions and a { } templating syntax to construct
        a new filename by mapping available properties to config.rename_pattern.

        # Permitted rename pattern objects:
        # {title}, {title-the}, {year}, {edition}, {quality}, {quality-full}. For
        # using other characters with pattern objects, place chars inside {}
        # e.g. { - edition}. For escaping templating characters, use \{ \},
        # e.g. {|{edition\}}.

        Returns:
            A new new path name based on config.rename_pattern.
        """
        return formatter.build_new_basename(self.primary_file, 'file' if self.is_file else 'folder')

    @property
    def destination_path(self):
        # If 'rename_only' is enabled, we need to override the configured
        # destination dir with the source dir.
        
        root_dst_folder = ''
        if config.rename_only is True:
            root_dst_folder = os.path.dirname(self.source_path)
        else:
            try:
                root_dst_folder = config.destination_dirs[self.primary_file.resolution] if self.primary_file.resolution else config.destination_dirs['SD']
            except KeyError:
                root_dst_folder = config.destination_dirs['default']
        film_folder = formatter.build_new_basename(self.primary_file, 'folder') if config.use_folders else ''
        return os.path.normpath(os.path.join(root_dst_folder, film_folder))

    @property
    def should_ignore(self):
        if re.search('^_UNPACK_', self.original_basename):
            self.ignore_reason = 'Unpacking'

        elif ops.fileops.contains_ignored_strings(self.original_basename):
            self.ignore_reason = 'Ignored string'

        elif not os.path.exists(self.source_path):
            self.ignore_reason = 'Path no longer exists'

        elif self.is_file and len(self.video_files) == 0:
            self.ignore_reason = 'File does not a valid file extension'

        elif self.is_tv_show:
            self.ignore_reason = 'Appears to be a TV show'

        elif self.is_folder and len(self.video_files) == 0:
            self.ignore_reason = 'No video files found in this folder'

        elif self.title is None:
            self.ignore_reason = 'Unknown title'

        elif self.year is None and (config.force_lookup is False or config.tmdb.enabled is False):
            self.ignore_reason = 'Unknown year'

        elif len(self.video_files) > 0 and self.size < ops.fileops.is_acceptable_size(self.primary_file.source_path):
            self.ignore_reason = f'{formatter.pretty_size(self.size)} is too small'

        return self.ignore_reason is not None

    @property
    def should_skip(self):
        """Determines whether the film should be processed
        or be suppressed (including console suppression).

        Args:
            film: (Film) Film object to check for ignore_reason
        Returns:
            bool: True if the file/folder should be skipped, otherwise False
        """
        if (self.should_ignore is True and config.interactive is True
            and not self.ignore_reason.startswith("Unknown")
            and not self.ignore_reason == "Appears to be a TV show"
                and not self.ignore_reason.endswith("small")):
            return True
        elif self.should_ignore is True and config.interactive is False and config.hide_skipped is True:
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
        self.matches = await tmdb.search(self.tmdb_id or self.title, None if self.tmdb_id else self.year)

        best_match = next(iter(self.matches or []), None)
        
        if best_match is not None:
            # If we find a result, update title, tmdb_id, year, and the title_similarity.
            self.update_with_match(best_match)
        else:
            # If not, we update the ignore_reason
            self.ignore_reason = 'No results found'

    def update_with_match(self, match):
        """Updates existing properties from a TmdbResult match

        Updates all of a film's properties from a TmdbResult
        match object.

        Args:
            match: (TmdbResult) Search result as a TmdbResult object.
        """

        self.title = match.proposed_title
        self.overview = match.overview
        self.poster_path = match.poster_path
        self.tmdb_id = match.tmdb_id
        self.year = match.proposed_year
        self.title_similarity = match.title_similarity  

    class File:
        """An object that identifies an individual film file and its attributes.

        Using a combination of regular expressions and intelligent
        algorithms, determine the most likely attributes that
        pertain to a film.

        Attributes:
            title:              Title of the parent film.

            title_the:          Title, The of the  parent film.

            year:               Year of the  parent film.

            edition:            Special edition.

            media:              Original release media, e.g. Bluray, WEBDL, HDTV, None (unknown)
            
            resolution:         Original pixel depth: SD, 720p, 1080p, or 2160p.

            is_hdr:             Bool to indicate whether this version is HDR.

            is_proper:          Bool to indicate whether this version is a proper release.

            parent_film:        Parent film containing the file.

            source_path:        Current source path of file.

            destination_folder: Parent (root) dir where this file will be
                                moved, based on quality-based sorting defined
                                in config.destination_dirs.

            destination_path:   Full folder+file destination of the new file after
                                being renamed.

            original_path:      (Immutable) original path of file.

            original_basename:  Original filename before it was renamed.

            ext:                File extension.

            size:               Size of file, in bytes.

            metadata:           Media metadata derived from libmediainfo

            new_filename:       New filename generated using the defined templating pattern
                                in config.rename_pattern.file.

            new_foldername:     New foldername generated using the defined templating pattern
                                in config.rename_pattern.folder.

            new_filename_and_ext: 
                                Returns the new file name including file extension. Supports
                                an optinal second param to override ext.

            has_valid_ext:      Returns true if the film is a file and
                                has a valid file extension.

            is_file:            Returns true if the film was loaded from
                                a file.

            is_video_file:      Returns true if the film is a file and
                                has a valid video file extension.

            is_subtitle_file:   Returns ture if the file is a subtitle.

            is_duplicate:       Returns true if the file is marked as a duplicate.

            duplicate:          Returns None, or one of Should enum (UPGRADE, IGNORE, KEEP_BOTH, DELETE)

            upgrade_reason:     Returns the reason this file should be upgraded, or an empty string.
            
            did_move:           Returns true when the file has been successfully moved.
        """

        def __init__(self, source_path, parent_film: 'Film'):
            self.source_path = source_path
            self.parent_film = parent_film
            self.did_move = False
            self.is_duplicate = False
            self.duplicate = None
            self.upgrade_reason = ''

            # Internal setter for `ext`.
            # We use this because at times `source_path` is overwritten.
            self._ext = None

            # Internal setter for `metadata`.
            self._metadata = None

            # Internal setter for `size`.
            self._size = None

            # Internal setter for `source_path`.
            self._source_path = source_path

            # Internal setter for (immutable) `original_path`.
            # Does not change even if the file is renamed, moved, or copied.
            self._original_path = source_path

            # Internal setter for `resolution`.
            self._resolution = None

            # Parse quality
            self.edition = parser.get_edition(self.source_path)
            self.media = parser.get_media(self.source_path)
            self.is_hdr = parser.is_hdr(self.source_path)
            self.is_proper = parser.is_proper(self.source_path)

        @property
        def title(self):
            return self.parent_film.title

        @property
        def title_the(self):
            return self.parent_film.title_the

        @property
        def year(self):
            return self.parent_film.year

        @property
        def resolution(self):
            if self._resolution is None:
                self._resolution = parser.get_resolution(self.source_path)
            if self._resolution is None:
                # Try using the film's actual metadata
                try:
                    if self.metadata.width == 1920:
                        self._resolution = '1080p'
                    elif self.metadata.width == 1280:
                        self._resolution = '720p'
                    elif self.metadata.width == 3840:
                        self._resolution = '2160p'
                except Exception:
                    pass
            return self._resolution

        @property
        def original_basename(self):
            return os.path.basename(os.path.splitext(self.source_path)[0] if os.path.isfile(self.source_path) else self.source_path)

        @property
        def original_path(self):
            return self._original_path

        @property
        def ext(self):
            if not self._ext:
                self._ext = os.path.splitext(self.source_path)[1].replace('.', '') if os.path.isfile(self.source_path) else None
            return self._ext

        @property
        def size(self):
            if not self._size:
                self._size = ops.size(self.source_path)
            return self._size

        @property
        def metadata(self):
            if not self._metadata and self.is_video:
                media_info = MediaInfo.parse(self.source_path, 
                    library_file=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'libmediainfo.0.dylib'))
                for track in media_info.tracks:
                    if track.track_type == 'Video':
                        self._metadata = track
            return self._metadata

        @property
        def has_valid_ext(self):
            return ops.fileops.has_valid_ext(self.source_path) if self.is_file else False

        @property
        def is_file(self):
            return os.path.isfile(self.source_path)

        @property
        def is_video(self):
            return any([self.ext in [x.replace('.', '') for x in config.video_exts]])

        @property
        def is_subtitle(self):
            return self.ext == 'srt' or self.ext == 'sub'

        @property
        def new_filename(self):
            r"""Build a new file name from the specified renaming pattern.

            Use regular expressions and a { } templating syntax to construct
            a new filename by mapping available properties to config.rename_pattern.

            # Permitted rename pattern objects:
            # {title}, {title-the}, {year}, {edition}, {quality}, {quality-full}. For
            # using other characters with pattern objects, place chars inside {}
            # e.g. { - edition}. For escaping templating characters, use \{ \},
            # e.g. {|{edition\}}.

            Returns:
                A new filename based on config.rename_pattern.file, excluding file ext
            """
            return formatter.build_new_basename(self, 'file')

        @property
        def new_foldername(self):
            """Build a new folder name from the specified renaming pattern.

            This will be the same as new_filename, but deriving itself from 
            rename_pattern.folder instead.

            Returns:
                A new foldername based on config.rename_pattern.folder.
            """
            return formatter.build_new_basename(self, 'folder')

        @property
        def new_filename_and_ext(self, ext=''):
            """Return the new filemname plus ext.
            Supports an optional override for ext value.

            Returns:
                A new filename.ext based on new_filename method.
            """
            return f'{self.new_filename}.{(self.ext or ext).replace(".", "")}'

        @property
        def destination_folder(self):
            # If 'rename_only' is enabled, we need to override the configured
            # destination dir with the source dir.
            
            dst = ''
            if config.rename_only is True:
                dst = os.path.dirname(self.source_path)
            else:
                try:
                    dst = config.destination_dirs[self.resolution] if self.resolution else config.destination_dirs['SD']
                except KeyError:
                    dst = config.destination_dirs['default']
            return os.path.normpath(os.path.join(dst, self.new_foldername)) if config.use_folders else dst

        @property
        def destination_path(self):
            return os.path.normpath(os.path.join(self.destination_folder, self.new_filename_and_ext))
