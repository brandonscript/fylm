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

"""Duplicate handling for films.

This module handles all the duplicate checking and handling logic for Fylm.
"""

import os
import itertools

from fylmlib.enums import *
import fylmlib.config as config
# from fylmlib.operations import fileops, dirops
from fylmlib import Console, Compare

class Duplicates:
    """Class for handling duplicate checking and governance.

    All methods are class methods, thus this class should never be instantiated.
    """

    @classmethod
    def find(cls, film: 'Film') -> ['Film.File']:
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
        # DANGER ZONE: With check_for_duplicates disabled and force_overwrite enabled, any files
        # with the same name at the destination will be silently overwritten.
        if config.duplicates.enabled is False or config.rename_only is True:
            debug('Duplicate checking is disabled, skipping.')
            return []

        existing_films = dirops.get_existing_films(config.destination_dirs)

        debug(f'Checking list of duplicates for "{film.new_basename}"')
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
        debug(f'Total duplicate copies of this film found: {len(duplicate_videos)}')

        for v in film.video_files:
            for d in duplicate_videos:
                # Mark each duplicate in the record
                if cls.should(v, d) == Should.IGNORE:
                    film.ignore_reason = "Not an upgrade for existing version"

        # Sort so that ignores are first, so console can skip printing the rest
        sort_order = [Should.IGNORE, Should.UPGRADE, Should.KEEP_BOTH]
        duplicate_videos = [d for x in sort_order for d in duplicate_videos if d.duplicate_action == x]

        # Reverse the order in interactive mode and return
        return duplicate_videos if not config.interactive else duplicate_videos[::-1]

    @classmethod
    def find_exact(cls, film: 'Film') -> ['Film.File']:
        """Retrieves exact duplicates File object for a film.

        If no exact duplicate is detected, returns an empty list.

        Args:
            film: (Film) a film file to search for an exact duplicate.
        Returns:
            list: [Film.File] that is an exact match by quality (not size). 
                  Hopefully only ever be one file, but a user could have
                  more exact matches in multiple folders.
        """
        # Identify sets of files that are exact quality matches. While resolution, media,
        # or quality could be missing from a duplicate's filename, by checking these properties
        # we can prevent data loss. Only YOU can prevent data loss!

        return [d for v in film.video_files for d in film.duplicate_files if compare.is_exact_duplicate(v, d)]

    @classmethod
    def find_lower_quality(cls, film: 'Film') -> ['Film.File']:
        """Retrieves all File objects for a film that are a lesser quality.
        Size is not compared here, only quality attributes.
        If none are found, returns an empty list.

        Args:
            film: (Film) a film file to search for lower quality duplicates.
        Returns:
            list: [Film.File] of duplicates that are lower quality than the current file.
        """

        # Compares video files to duplicate files and returns all duplicates where 
        # the duplicate (d) is lower quality than the current film's video files (v).
        return [d for v in film.video_files for d in film.duplicate_files if compare.quality(d, v) == ComparisonResult.LOWER]

    @classmethod
    def find_upgradable(cls, film: 'Film'):
        """Finds duplicates on the destination dirs that will be upgraded.
        
        Args:
            film (Film): Film object used to search for upgradable duplicates.
        """

        # Loop through each duplicate that should be replaced.
        return [d for v in film.video_files for d in film.duplicate_files if cls.should(v, d) == Should.UPGRADE]

    @classmethod
    def should(cls, current: 'Film.File', duplicate: 'Film.File') -> Should:
        """Determines how to handle the current file when a duplicate is detected.

        Config settings govern whether a duplicate can be upgraded if it is of
        a specific quality, e.g. a 1080p can be allowed upgrade a 720p, but a
        2160p cannot.

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
        if config.duplicates.automatic_upgrading is False:
            return cls._mark(duplicate, Should.IGNORE)

        # Replace quality takes a dict of arrays for each quality, which governs whether
        # a specific quality has the ability to replace another. By default, this map
        # looks like:
        #   2160p: [] # Do not replace 2160p films with any other quality
        #   1080p: [] # Do not replace 1080p films with any other quality
        #   720p: ['1080p'] # Replace 720p films with 1080p
        #   SD: ['1080p', '720p'] # Replace standard definition (or unknown quality)
        #       with 1080p or 720p
        
        # HDR and different editions should be warned, but treated as distinct.
        # Media order of priority is "bluray", "webdl", "hdtv", "dvd", "sdtv"
        # Proper should always take preference over a non-proper.

        reason = None

        # If the resolutions don't match and the current resolution is in the
        # duplicate's upgrade table, upgrade, otherwise keep both.
        if compare.resolution(current, duplicate) != ComparisonResult.EQUAL:
            if (current.resolution in 
                config.duplicates.upgrade_table[duplicate.resolution.key]):
                # Duplicate is a lower resolution and is in the upgrade table
                return cls._mark(duplicate, 
                                 Should.UPGRADE, 
                                 IgnoreReason.LOWER_RESOLUTION)
            else:
                # Duplicate is a different resolution, but is not in the upgrade table
                # so we're going to keep both copies.
                return cls._mark(duplicate, 
                                 Should.KEEP_BOTH, 
                                 IgnoreReason.DIFFERENT_RESOLUTIONS)
                
        elif compare.resolution(current, duplicate) == ComparisonResult.LOWER:
            # Duplicate is a higher resolution than the current file 
            reason = IgnoreReason.BETTER_RESOLUTION

        # If the resolutions match, we need to do some additional comparisons.
        if compare.resolution(current, duplicate) == ComparisonResult.EQUAL:
            # For now, HDR will always be kept alongside SDR copies, so if one is an HDR, 
            # we will automatically keep both.
            if current.is_hdr != duplicate.is_hdr:
                return cls._mark(duplicate, 
                                 Should.KEEP_BOTH, 
                                 (IgnoreReason.HDR 
                                  if duplicate.is_hdr 
                                  else IgnoreReason.NOT_HDR))

            # If editions don't match, keep both unless the ignore_edition flag is enabled
            # Console should show a warning but the duplicate will remain intact.
            if current.edition != duplicate.edition and not config.duplicates.ignore_edition:
                return cls._mark(duplicate, 
                                 Should.KEEP_BOTH, 
                                 IgnoreReason.DIFFERENT_EDITIONS)

            # If the current is a better quality or proper, replace the same resolutions
            # This heuristic is quite complex, see code comments in compare.quality()
            if compare.quality(current, duplicate) == ComparisonResult.HIGHER:
                return cls._mark(duplicate, 
                                 Should.UPGRADE, 
                                 IgnoreReason.LOWER_QUALITY)
            else:
                reason = IgnoreReason.SAME_OR_BETTER_QUALITY

            # If the current file is of the same quality and the file size is larger, upgrade
            if (config.duplicates.automatic_upgrading is True and current.size > (duplicate.size or 0)):
                return cls._mark(duplicate, Should.UPGRADE)
            elif current.size == (duplicate.size or 0):
                reason = IgnoreReason.SAME_QUALITY

        # If up to this point we can't determine if we should upgrade or keep both, ignore the current file
        # because it cannot be safely moved without risk of data loss. Chances are at this point everything
        # is the same, except the current file is the same or smaller size than the duplicate.        
        return cls._mark(duplicate, Should.IGNORE, reason)

    @classmethod
    def _mark(cls, d: 'Film.File', should: Should, reason: UpgradeReason=None) -> Should:
        """Marks a duplicate file with the result of a should() call,
        then returns the original should() value. This can appear to be a little
        backwards, but if it is set to Should.UPGRADE, that means it is marked for upgrade.
        
        Args:
            current (Film.File): The current Film (file) object.
            duplicate (Film.File): Verified duplicate file that the current file will be compared to.
        Returns:
            Enum, one of 'Should.UPGRADE', 'Should.IGNORE', or 'Should.KEEP_BOTH'.
        """
        d.duplicate_action = should
        d.upgrade_reason = reason.display_name if reason else ''
        return should

    @classmethod
    def rename_unwanted(cls, film: 'Film', unwanted = None):
        """Rename duplicates on the destination dirs that will be upgraded.

        If duplicates are found and the inbound film should replace them,
        we want to prepare them for deletion by renaming them. If a move/copy
        is successful, we'll delete the dupes.
        
        Args:
            film: (Film) object to determine which duplicates to rename.
            unwanted: [Film.File] optional array of unwanted files to rename
        """

        # If unwanted is not specified, assume we need to search for upgradable files
        unwanted = cls.find_upgradable(film) if unwanted is None else unwanted
        
        # Loop through each duplicate that should be replaced.
        for d in unwanted:
            if os.path.exists(f'{d.source_path}.dup'):
                # Skip if it's already been renamed (edge case for when
                # there are multiple copies of the same film being moved)
                continue
            fileops.rename(d.source_path, f'{os.path.basename(d.source_path)}.dup')

    @classmethod
    def delete_upgraded(cls, film: 'Film'):
        """Delete upgraded duplicates on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete the copies on the destination dir that we don't
        want, and their parent folder, if it's empty.
        
        Args:
            film (Film): Film object to determine which duplicates to delete.
        """

        # Loop through each duplicate that should be replaced and delete it.
        for d in [u for u in film.duplicate_files if Should.UPGRADE == u.duplicate]:
            fileops.delete(f'{d.source_path}.dup')

        # Delete empty duplicate container folders
        cls.delete_leftover_folders(film)

        # Remove deleted duplicates from the film object
        film._duplicate_files = list(filter(lambda d: os.path.exists(d.source_path) or os.path.exists(f'{d.source_path}.dup'), film._duplicate_files))

    @classmethod
    def delete_leftover_folders(cls, film: 'Film'):
        """Delete empty duplicate folders on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete all the empty folders they leave behind.
        
        Args:
            film (Film): Film object to determine which duplicate deletions
                        might have left behind empty folders.
        """

        # Delete empty duplicate container folders
        for dup_film in [f.parent_film for f in film.duplicate_files]:
            if dup_film.is_folder and len(dirops.find_deep(dup_film.source_path)) == 0:
                # Delete the parent film dir and any hidden contents if it is less than 1 KB.
                dirops.delete_dir_and_contents(dup_film.source_path, max_size=1000)
