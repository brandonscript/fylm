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

        duplicate_files = list(itertools.chain(*[d.video_files for d in duplicates]))
        console.debug(f'Total duplicate files(s) found: {len(duplicate_files)}')
        return duplicate_files

    @classmethod
    def should_replace(cls, src: Film.File, duplicate: Film.File):
        """Determines if a duplicate file should be replaced.

        Config settings govern whether a duplicate can be replaced if it is of
        a specific quality, e.g. a 1080p can be allowed replace a 720p, but a
        2160p cannot. This method will be eventually expanded to handle quality
        upgrading and multiple media sources.
        
        Args:
            src (Film.File): Film object to determine if it should replace a duplicate.
            duplicate (Film.File): Verified duplicate file to check src against.
        Returns:
            True if `src` should replace `duplicate`.
        """

        # If duplicate replacing is disabled, don't replace.
        if config.duplicate_replacing.enabled is False:
            return False

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
        if src.resolution in config.duplicate_replacing.replace_quality[duplicate.resolution or 'SD']:
            return True

        # If the editions do not match, we want to warn, but not replace.
        if src.edition != duplicate.edition:
            return False

        # If the src is a better quality or proper, replace the same resolutions
        elif src.resolution == duplicate.resolution and compare.is_higher_quality(src, duplicate):
            return True

        # Or, if quality is the same and the size is larger, 
        elif (config.duplicate_replacing.replace_smaller is True
            and src.resolution == duplicate.resolution
            and src.size > (duplicate.size or 0)):
            return True

        # Otherwise it should not be replaced.
        else:
            return False

    @classmethod # deprecatd
    def should_keep_both(cls, film, duplicate):
        """Determines if both a film and a duplicate should be kept.

        Under certain conditions, both a film and a duplicte should be kept.
        
        Args:
            film (Film): Film object to determine if it should replace a duplicate.
            duplicate (Film or path): Duplicate object to check `film` against.
        Returns:
            True if `film` and `duplicate` should both be kept, else False.
        """

        # TODO: Why do we have this method if we already have should_replace?

        # If the duplicate is a path and not a film, we need to load it.
        # TODO: Don't really want to have to do this here.
        from fylmlib.film import Film
        if not isinstance(duplicate, Film):
            duplicate = Film(duplicate)

        # If the editions are not the same, we want to keep both, but warn.
        if film.edition != duplicate.edition:
            return True

        # If new and existing films have a different quality, and the new film is larger 
        # (better), if the new film doesn't qualify as a replacement, we can assume that 
        # we want to keep both the current film and the duplicate.
        return (film.resolution != duplicate.resolution 
            and not cls.should_replace(film, duplicate))

    @classmethod # deprecated
    def should_keep(cls, film):
        """Determines if a film should be kept, if there are duplicates.

        Under certain conditions, a film is not wanted. This function determines
        if the film should be ignored or kept.
        
        Args:
            film (Film): Film object to determine if it should be kept.
        Returns:
            True if `film` is wanted, else False.
        """

        # If all of the duplicates should not be replaced, and we don't want to keep
        # both this film and (any) of its duplicates, return false.
        return not all(
            not cls.should_replace(film, d) 
            and not cls.should_keep_both(film, d) 
            for d in film.duplicates)

    @classmethod
    def rename_unwanted(cls, film: Film):
        """Rename unwanted duplicates on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to prepare them for deletion by renaming them. If a move/copy
        is successful, we'll delete the dupes.
        
        Args:
            film (Film): Film object to determine which duplicates to rename.
        """

        # Loop through each duplicate that should be replaced.
        for file in film.video_files:
            for d in filter(lambda d: cls.should_replace(file, d), film.duplicate_files):
                ops.fileops.rename(d.source_path, f'{os.path.basename(d.source_path)}.dup')

    @classmethod
    def delete_unwanted(cls, film: Film):
        """Delete unwanted duplicates on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete the copies on the destination dir that we don't
        want, and their parent folder, if it's empty.
        
        Args:
            film (Film): Film object to determine which duplicates to delete.
        """

        # Loop through each duplicate that should be replaced.
        for file in film.video_files:
            for d in filter(lambda d: cls.should_replace(file, d), film.duplicate_files):
                ops.fileops.delete(f'{d.source_path}.dup')

        # Delete empty duplicate container folders
        cls.delete_leftover_folders(film)

        # Remove deleted duplicates from the film object
        for file in film.video_files:
            for d in filter(lambda d: cls.should_replace(file, d), film.duplicate_files):
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
