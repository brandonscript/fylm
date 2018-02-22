# -*- coding: utf-8 -*-
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

from fylmlib.config import config
from fylmlib.parser import parser
import fylmlib.formatter as formatter
import fylmlib.tmdb as tmdb
import fylmlib.operations as ops

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

        edition:            Special edition.

        media:              Original release media, e.g. BluRay.

        quality:            Original quality of media: 720p, 1080p,
                            or 2160p.

        title_similarity:   Similarity between parsed title and TMDb
                            title.

        source_path:        Current source path of film.

        original_path:      (Immutable) original path of film.

        original_filename:  Original folder name (or filename without
                            extension).

        ext:                File extension, if film is a file.

        size:               Size of file or folder contents belonging
                            to the film.

        size_of_largest_video:      Size of file or largest video file inside
                            a film folder.

        new_filename:       Uses the configured templating pattern to
                            generate a new filename.

        new_filename__ext:  (optional param: ext)
                            Returns the new filename with original
                            extension, or value of ext.

        destination_dir:    Destination dir where this file will be
                            moved.

        has_valid_ext:      Returns true if the film is a file and
                            has avalid file extension.

        is_video_file:      Returns true if the film is a file and
                            has a valid video file extension.

        is_tv_show:         Returns true if the film is actually a
                            TV show.

        is_file:            Returns true if the film was loaded from
                            a file.

        is_dir:             Returns true if the film was loaded from
                            a folder.

        valid_files:        If the film is a dir, returns a list of
                            valid files (including full path).

        is_duplicate:       Determines if the film is a duplicate,
                            when compared to an array of existing
                            films.

        duplicates:         Get a list of duplicates from the cached
                            list of existing films.

        should_ignore:      Returns true if the film should be ignored,
                            and sets the ignore_reason.

        ignore_reason:      If applicable, the reason why this film
                            was ignored.
    """

    def __init__(self, source_path):
        self.source_path = source_path
        self.title = parser.get_title(source_path)
        self.year = parser.get_year(source_path)
        self.overview = ''
        self.edition = parser.get_edition(source_path)
        self.media = parser.get_media(source_path)
        self.quality = parser.get_quality(source_path)
        self.tmdb_id = None
        self.tmdb_verified = False
        self.matches = []
        self.title_similarity = 0
        self.ignore_reason = None

        # Internal setter for `duplicates`.
        self._duplicates = None

        # Internal setter for `ext`.
        # We use this because at times `source_path` is overwritten.
        self._ext = None

        # Internal setter for `size`.
        self._size = None

        # Internal setter for `size_of_largest_video`.
        self._size_of_largest_video = None

        # Internal setter for `valid_files`.
        self._valid_files = None

        # Internal setter for (immutable) `original_path`.
        # Do not change even if the file is renamed, moved, or copied.
        self._original_path = source_path

    @property
    def original_path(self):
        return self._original_path

    @property
    def original_filename(self):
        return os.path.basename(os.path.splitext(self.source_path)[0] if os.path.isfile(self.source_path) else self.source_path)

    @property
    def ext(self):
        if not self._ext:
            self._ext = os.path.splitext(self.source_path)[1] if os.path.isfile(self.source_path) else None
        return self._ext

    @property
    def size(self):
        if not self._size:
            self._size = ops.size(self.source_path)
        return self._size

    @property
    def size_of_largest_video(self):
        if not self._size_of_largest_video:
            self._size_of_largest_video = ops.size_of_largest_video(self.source_path)
        return self._size_of_largest_video

    @property
    def title_the(self):
        if re.search(r'(^the\b|, the)', self.title, re.I):
            return '{}{}'.format(formatter.strip_the(self.title), ', The')
        else:
            return self.title

    @property
    def has_valid_ext(self):
        return ops.fileops.has_valid_ext(self.source_path) if self.is_file else False

    @property
    def is_video_file(self):
        return any([self.ext in config.video_exts]) if self.is_file else False

    @property
    def is_tv_show(self):
        return bool(re.search(r"\bS\d{2}(E\d{2})?\b", self.original_filename, re.I))

    @property
    def is_file(self):
        return os.path.isfile(self.source_path)

    @property
    def is_dir(self):
        return os.path.isdir(self.source_path)

    @property
    def valid_files(self):
        if self._valid_files is None:
            self._valid_files = ops.dirops.get_valid_files(self.source_path)
        return self._valid_files

    @property
    def new_filename(self):
        """Build a new file name from the specified renaming pattern.

        Use regular expressions and a { } templating syntax to construct
        a new filename by mapping available properties to config.rename_pattern.

        # Permitted rename pattern objects:
        # {title}, {title-the}, {year}, {quality}, {edition}, {media}. For
        # using other characters with pattern objects, place chars inside {}
        # e.g. { - edition}. For escaping templating characters, use \{ \},
        # e.g. {|{edition\}}.

        Returns:
            A new filename based on config.rename_pattern.
        """
        return formatter.build_new_filename(self)

    def new_filename__ext(self, ext=''):
        return '{}{}'.format(self.new_filename, self.ext or ext)

    @property
    def destination_dir(self):
        # If 'rename_only' is enabled, we need to override the configured
        # destination dir with the source dir.
        
        dst = ''
        if config.rename_only is True:
            dst = os.path.dirname(self.source_path)
        else:
            try:
                dst = config.destination_dirs[self.quality] if self.quality else config.destination_dirs['SD']
            except KeyError:
                dst = config.destination_dirs['default']
        return os.path.normpath(os.path.join(dst, self.new_filename)) if config.use_folders else dst

    @property
    def should_ignore(self):
        if ops.fileops.contains_ignored_strings(self.original_filename):
            self.ignore_reason = 'Ignored string'

        elif self.is_file and not self.has_valid_ext:
            self.ignore_reason = 'Not a valid file extension'

        elif self.is_tv_show:
            self.ignore_reason = 'Appears to be a TV show'

        elif self.is_dir and len(self.valid_files) == 0:
            self.ignore_reason = 'No valid files found in this folder'

        elif self.title is None:
            self.ignore_reason = 'Unknown title'

        elif self.year is None and (config.force_lookup is False or config.tmdb.enabled is False):
            self.ignore_reason = 'Unknown year'

        elif self.size < config.min_filesize * 1024 * 1024 and self.is_video_file:
            self.ignore_reason = '%s is too small' % formatter.pretty_size(self.size)

        return self.ignore_reason is not None

    @property
    def duplicates(self):
        """Get a list of duplicates from a list of existing films.

        Compare the film objects to an array of existing films in
        order to determine if any duplicates exist at the destination.
        Criteria for a duplicate: title, year, and edition must match (case insensitive).

        Returns:
            A an array of duplicate films.
        """
        # Import duplicates here to avoid circular imports.
        from fylmlib.duplicates import duplicates

        if self._duplicates is None:
            self._duplicates = duplicates.find(self)
        return self._duplicates

    @property
    def is_duplicate(self):
        """Returns true if the current film is a duplicate of an existing one.

        Compares the current film to a list of existing films and returns true
        if 1 or more duplicates are found.

        Returns:
            True if 1 or more duplicates are found, else False.
        """
        return len(self.duplicates) > 0

    def search_tmdb(self):
        """Performs a TMDb search on the existing film.

        Calls the tmdb.search() method, passing the current film
        as params. If a result is found, the current film's properties
        are updated with the values from TMDb.
        """

        # Only perform lookups if TMDb searching is enabled.
        if config.tmdb.enabled is True:

            # Perform the search and save the first 10 results to the matches list. 
            # If ID is not None, search by ID.
            self.matches = (tmdb.search(self.tmdb_id) if (self.tmdb_id is not None) else tmdb.search(self.title, self.year))[:10]
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
        self.tmdb_id = match.tmdb_id
        self.year = match.proposed_year
        self.title_similarity = match.title_similarity