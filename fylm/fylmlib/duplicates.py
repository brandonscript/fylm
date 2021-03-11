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

"""Duplicate handling for films.

This module handles all the duplicate checking and handling logic for Fylm.
"""
from __future__ import unicode_literals, print_function
from builtins import *

import os
import itertools

import fylmlib.config as config
from fylmlib.console import console
from fylmlib.film import Film
import fylmlib.compare as compare
import fylmlib.operations as ops
from fylmlib.enums import Should

class duplicates:
    """Class for handling duplicate checking and governance.

    All methods are class methods, thus this class should never be instantiated.
    """

    @classmethod
    def find(cls, film: Film) -> [Film.File]:
        """From a list of existing films, return those that contain
        one or more duplicate files.

        Compare the film objects to an array of exsiting films in
        order to determine if any duplicates exist at the destination.
        Criteria for a duplicate: title and year must match.

        Returns:
            An array of duplicate films objects for the specified file.
        Args:
            film (Film): Film to check for duplicates.
        """

        # If check for duplicates is disabled, return an empty array (because we don't care if they exist).
        # DANGER ZONE: With check_for_duplicates disabled and overwrite_existing enabled, any files
        # with the same name at the destination will be silently overwritten.
        if config.duplicate_checking.enabled is False or config.rename_only is True:
            console.debug('Duplicate checking is disabled, skipping.')
            return []

        existing_films = ops.dirops.get_existing_films(config.destination_dirs)

        console.debug(f'Checking list of duplicates for "{film.new_basename}"')
        # Filter the existing_films cache array to titles beginning with the first letter of the
        # current film, then filter to check for duplicates. Then we filter out empty folder,
        # folders with no valid media folders, and keep only non-empty folders and files.

        duplicates = list(filter(lambda x:
                # First letter of the the potential duplicate's title must be the same.
                # Checking this first allows us to have a much smaller list to compare against.
                film.title[0] == x.title[0]

                # Check that the film is a legitimate duplicate
                and compare.is_duplicate(film, x)

                and ((
                    # If the potential duplicate is a folder, check that it contains at least
                    # one valid file.
                    x.is_folder and len(x.video_files) > 0)

                    # Or if it is a file, it is definitely a duplicate.
                    or x.is_file),

            # Perform the filter against the existing films cache.
           existing_films))

        duplicate_videos = list(itertools.chain(*[d.video_files for d in duplicates]))
        
        for v in film.video_files:
            for d in duplicate_videos:
                # Mark each duplicate in the record
                should = cls.should(v, d)
                if should == Should.IGNORE:
                    film.ignore_reason = "Not an upgrade for existing version"

        # Sort to ensure ignored files are last, so that the console print order makes
        # sense. (E.g., you wouldn't want to 'ignore' first then say 'keep' when 
        # ignore should be the last in the list).
        sort_order = [Should.UPGRADE, Should.KEEP_BOTH, Should.IGNORE]
        duplicate_videos = [d for x in sort_order for d in duplicate_videos if d.duplicate == x]

        console.debug(f'Total duplicate files(s) found: {len(duplicate_videos)}')
        return duplicate_videos

    @classmethod
    def should(cls, current: Film.File, duplicate: Film.File) -> Should:
        """Determines how to handle the current file when a duplicate is detected.

        Config settings govern whether a duplicate can be upgraded if it is of
        a specific quality, e.g. a 1080p can be allowed upgrade a 720p, but a
        2160p cannot.

        Todo: Add media-based upgrading.

        The return value of this method is an Enum, the result of which should
        incicate which action to take:
            - upgrade: the current file should upgrade the duplicate
            - ignore: the current file should be skipped and the duplicate left intact
            - keep_both: both files should be kept, as they are treated as unique
        
        Args:
            current (Film.File): The current Film (file) object.
            duplicate (Film.File): Verified duplicate file that the current file will be compared to.
        Returns:
            Enum, one of 'Should.UPGRADE', 'Should.IGNORE', or 'Should.KEEP_BOTH'.
        """

        # If duplicate replacing is disabled, don't replace.
        if config.duplicate_replacing.enabled is False:
            return cls._mark(duplicate, Should.IGNORE)

        # If the duplicate is a path and not a film, we need to load it.
        # from fylmlib.film import Film
        # if not isinstance(duplicate, Film):
        #     duplicate = Film(duplicate)

        # Replace quality takes a dict of arrays for each quality, which governs whether
        # a specific quality has the ability to replace another. By default, this map
        # looks like:
        #   2160p: [] # Do not replace 2160p films with any other quality
        #   1080p: [] # Do not replace 1080p films with any other quality
        #   720p: ['1080p'] # Replace 720p films with 1080p
        #   SD: ['1080p', '720p'] # Replace standard definition (or unknown quality)
        #       with 1080p or 720p
        
        # HDR and different editions should be warned, but treated as distinct.
        # Media order of priority is ["bluray", "webdl", "hdtv", "dvd", "sdtv"]
        # Proper should always take preference over a non-proper.

        ignore_reason = ''

        # If the resolutions don't match and the current resolution is in the
        # duplicate's upgrade table, upgrade, otherwise keep both.
        if current.resolution != duplicate.resolution:
            if current.resolution in config.duplicate_replacing.replace_quality[duplicate.resolution or 'SD']:
                return cls._mark(duplicate, Should.UPGRADE, 'Lower resolution')
            else:
                return cls._mark(duplicate, Should.KEEP_BOTH, 'Different resolutions')
        else:
            ignore_reason = 'Better resolution'

        # If the resolutions match, we need to do some additional comparisons.
        if current.resolution == duplicate.resolution:
            # For now, HDR will always be kept alongside SDR copies, so if one is an HDR, 
            # we will automatically keep both.
            if current.is_hdr != duplicate.is_hdr:
                return cls._mark(duplicate, Should.KEEP_BOTH, 'HDR' if duplicate.is_hdr else 'Not HDR')

            # If editions don't match, keep both unless the ignore_edition flag is enabled
            # Console should show a warning but the duplicate will remain intact.
            if current.edition != duplicate.edition and not config.duplicate_replacing.ignore_edition:
                return cls._mark(duplicate, Should.KEEP_BOTH, 'Different editions')

            # If the current is a better quality or proper, replace the same resolutions
            # This heuristic is quite complex, see code comments in compare.is_higher_quality()
            if compare.is_higher_quality(current, duplicate):
                return cls._mark(duplicate, Should.UPGRADE, 'Lower quality')
            else:
                ignore_reason = 'Same or better quality'

            # If the current file is of the same quality and the file size is larger, upgrade
            if (config.duplicate_replacing.replace_smaller is True and current.size > (duplicate.size or 0)):
                return cls._mark(duplicate, Should.UPGRADE)
            elif current.size == (duplicate.size or 0):
                ignore_reason = "Files are identical"

        # If up to this point we can't determine if we should upgrade or keep both, ignore the current file
        # because it cannot be safely moved without risk of data loss. Chances are at this point everything
        # is the same, except the current file is the same or smaller size than the duplicate.
        
        return cls._mark(duplicate, Should.IGNORE, ignore_reason)

    @classmethod
    def _mark(cls, d: Film.File, should: Should, reason: str='') -> Should:
        """Marks a duplicate file with the result of a should() call,
        then returns the original should() value.
        
        Args:
            current (Film.File): The current Film (file) object.
            duplicate (Film.File): Verified duplicate file that the current file will be compared to.
        Returns:
            Enum, one of 'Should.UPGRADE', 'Should.IGNORE', or 'Should.KEEP_BOTH'.
        """
        d.duplicate = should
        d.upgrade_reason = reason
        return should

    @classmethod
    def rename_unwanted(cls, film: Film):
        """Rename duplicates on the destination dirs that will be upgraded.

        If duplicates are found and the inbound film should replace them,
        we want to prepare them for deletion by renaming them. If a move/copy
        is successful, we'll delete the dupes.
        
        Args:
            film (Film): Film object to determine which duplicates to rename.
        """

        # Loop through each duplicate that should be replaced.
        for file in film.video_files:
            # Only rename files that we want to upgrade
            for d in filter(lambda d: cls.should(file, d) == Should.UPGRADE, film.duplicate_files):
                if os.path.exists(f'{d.source_path}.dup'):
                    # Skip if it's already been renamed (edge case for when
                    # there are multiple copies of the same film being moved)
                    continue
                ops.fileops.rename(d.source_path, f'{os.path.basename(d.source_path)}.dup')

    @classmethod
    def delete_upgraded(cls, film: Film):
        """Delete upgraded duplicates on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete the copies on the destination dir that we don't
        want, and their parent folder, if it's empty.
        
        Args:
            film (Film): Film object to determine which duplicates to delete.
        """

        # Loop through each duplicate that should be replaced.
        for file in film.video_files:
            for d in filter(lambda d: cls.should(file, d) == Should.UPGRADE, film.duplicate_files):
                ops.fileops.delete(f'{d.source_path}.dup')

        # Delete empty duplicate container folders
        cls.delete_leftover_folders(film)

        # Remove deleted duplicates from the film object
        for file in film.video_files:
            for d in filter(lambda d: cls.should(file, d), film.duplicate_files):
                film._duplicate_files = list(filter(lambda d: os.path.exists(d.source_path) or os.path.exists(f'{d.source_path}.dup'), film._duplicate_files))

    @classmethod
    def delete_leftover_folders(cls, film: Film):
        """Delete empty duplicate folders on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete all the empty folders they leave behind.
        
        Args:
            film (Film): Film object to determine which duplicate deletions
                        might have left behind empty folders.
        """

        # Delete empty duplicate container folders
        for dup_film in [f.parent_film for f in film.duplicate_files]:
            if dup_film.is_folder and len(ops.dirops.find_deep(dup_film.source_path)) == 0:
                # Delete the parent film dir and any hidden contents if it is less than 1 KB.
                ops.dirops.delete_dir_and_contents(dup_film.source_path, max_size=1000)
