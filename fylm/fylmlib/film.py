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

from __future__ import unicode_literals

import os
import re
from itertools import ifilter

from fylmlib.config import config
from fylmlib.console import console
from fylmlib.parser import parser
import fylmlib.formatter as formatter
import fylmlib.tmdb as tmdb
import fylmlib.compare as compare
import fylmlib.operations as ops
import fylmlib.existing_films as existing_films

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

        year:               Primary release year.

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
        self.edition = parser.get_edition(source_path)
        self.media = parser.get_media(source_path)
        self.quality = parser.get_quality(source_path)
        self.tmdb_id = None
        self.title_similarity = 0
        self.ignore_reason = None

        # Internal setter for `ext`.
        # We use this because at times `source_path` is overwritten.
        self._ext = None

        # Internal setter for `size`.
        self._size = None

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
        return ops.dirops.get_valid_files(self.source_path)

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

        quality_map = [
            ['SD', 'SD'],
            ['720p', '720p'],
            ['1080p', '1080p'],
            ['2160p', '4K'],
            ['default', 'default']
        ]
        
        dst = ''
        if config.rename_only is True:
            dst = os.path.basename(self.source_path)
        else:
            try:
                dst = config.destination_dirs[quality_map[self.quality]] or config.destination_dirs['default']
            except KeyError:
                dst = config.destination_dirs['default']
        
        return os.path.normpath(os.path.join(dst, self.new_filename)) if config.use_folders else config.destination_dir

    @property
    def should_ignore(self):
        if ops.fileops.contains_ignored_strings(self.original_filename):
            self.ignore_reason = '(ignored string)'

        elif self.is_file and not self.has_valid_ext:
            self.ignore_reason = '(not a valid file extension)'

        elif self.is_tv_show:
            self.ignore_reason = '(appears to be a TV show)'

        elif self.is_dir and len(self.valid_files) == 0:
            self.ignore_reason = '(no valid files found in this folder)'

        elif self.title is None:
            self.ignore_reason = '(unknown title)'

        elif self.year is None and (config.force_lookup is False or config.tmdb.enabled is False):
            self.ignore_reason = '(unknown year)'

        elif self.size < config.min_filesize * 1024 * 1024 and self.is_video_file:
            self.ignore_reason = '({} is too small)'.format(formatter.pretty_size(self.size))

        return self.ignore_reason is not None

    @property
    def duplicates(self):
        """Get a list of duplicates from a list of existing films.

        Compare the film objects to an array of exsiting films in
        order to determine if any duplicates exist at the destination.
        Criteria for a duplicate: title, year, and edition must match (case insensitive).

        Returns:
            A an array of duplicate films.
        """

        # If check for duplicates is disabled, return an empty array (because we don't care if they exist).
        # DANGER ZONE: With check_for_duplicates disabled and overwrite_duplicates enabled, any files
        # with the same name at the destination will be silently overwritten.
        if config.check_for_duplicates is False:
            console.debug('Duplicate checking is disabled, skipping.')
            return []

        console.debug('Searching for duplicates of "{}" ({})'.format(self.title, self.year))

        # Filter the existing_films cache array to titles beginning with the first letter of the
        # current film, then use fast ifilter to check for duplicates. Then we filter out empty folder,
        # folders with no valid media folders, and keep only non-empty folders and files.
        # TODO: Add tests to ensure this works for 'title-the' naming convention as well.
        duplicates = list(ifilter(lambda d:
                # First letter of the the potential duplicate's title must be the same.
                # Checking this first allows us to have a much smaller list to compare against.
                d.title[0] == self.title[0]

                # Check that the film is actually a duplicate in name/year/edition
                and compare.is_duplicate(self, d)

                and ((
                    d.is_dir
                    # If the potential duplicate is a dir, check that it contains at least
                    # one valid file.
                    and len(ops.dirops.get_valid_files(d.source_path)) > 0)

                    # Or if it is a file, it is definitely a duplicate.
                    or d.is_file),

            # Perform the filter against the existing films cache.
            existing_films.cache))

        # Print any duplicates found to the console
        console.debug('   Total duplicate(s) found: {}'.format(len(duplicates)))
        if len(duplicates) > 0:
            console.warn('{} duplicate{} found ({}):'.format(
                len(duplicates),
                '' if len(duplicates) == 1 else 's',
                'overwriting' if config.overwrite_duplicates is True else 'aborting'))
            for d in duplicates:
                console.warn("  '{}' is {} ({})".format(
                    d.new_filename__ext(),
                    formatter.pretty_size_diff(self.source_path, d.source_path),
                    formatter.pretty_size(ops.size(d.source_path))))

        return duplicates

    @property
    def is_duplicate(self):
        """Returns true if the current film is a duplicate of an existing one.

        Compares the current film to a list of existing films and returns true
        if 1 or more duplicates are found.

        Returns:
            True if 1 or more duplicates are found, else False.
        """
        return len(self.duplicates) > 0

    # Perform TMDb lookup based on known title and year
    def search_tmdb(self):
        """Performs a TMDb search on the existing film.

        Calls the tmdb.search() method, passing the current film
        as params. If a result is found, the current film's properties
        are updated with the values from TMDb.
        """

        # Only perform lookups if TMDb searching is enabled.
        if config.tmdb.enabled is True:

            # Perform the search and save the result
            result = tmdb.search(self.title, self.year)

            if result is not None:
                # If we find a result, update title, tmdb_id, year, and the title_similarity.
                self.title = result.proposed_title
                self.tmdb_id = result.tmdb_id
                self.year = result.proposed_year
                self.title_similarity = result.title_similarity
            else:
                # If not, we update the ignore_reason
                self.ignore_reason = '(no results found)'