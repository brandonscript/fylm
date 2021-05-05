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
from pathlib import Path

from fylmlib.enums import *
from fylmlib.tools import *
import fylmlib.config as config
from fylmlib import Console, Compare, Find, FilmPath, TMDb

class Duplicates:
    """Class for finding, discovering, and handling duplicates
    
    Args:
        film (Film): A film to check for duplicates.
    """
    
    ALL = []
    
    def __init__(self, film: 'Film'):
        self._init = False
        self.film = film
        self.duplicates = []
        
    def __repr__(self):        
        if len(self) == 0:
            return "Duplicates(None)"
        x = f"Duplicates('{self.film.main_file.new_name}')\n"
        x += '\n–'.join([f'{f}' for f in (self.files if self._init else self.duplicates)])
        return x
    
    def __len__(self):
        if not self._init:
            self.find()
        return len(self.duplicates)
        
    def find(self) -> ['Film']:
        """Gets all copies of the specified film that exist in any dst dir.
        
        Returns:
            A list of duplicates film objects
        """
        
        from fylmlib import Film
        
        if not config.duplicates.enabled or config.rename_only:
            Console.debug('Duplicate checking is disabled, skipping.')
            return []
        
        Console.debug(f"Looking for duplicates of '{self.film.title} ({self.film.year})'")

        self.duplicates = list(map(Film, Find.glob(*set(config.destination_dirs.values()), 
                               search=f"{self.film.title} {self.film.year}")))
        
        self._init = True
        # Only return duplicate films if they have video files (no empty dirs)
        return [d for d in self.duplicates if iterlen(d.video_files) > 0]
        

    @classmethod #DEPRECATED:
    def find_old(cls, film: 'Film') -> ['Film.File']:
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
        # DANGER ZONE:
        # With check_for_duplicates disabled and force_overwrite enabled, any files
        # with the same name at the destination will be silently overwritten.
        if config.duplicates.enabled is False or config.rename_only is True:
            Console.debug('Duplicate checking is disabled, skipping.')
            return []

        existing_films = dirops.get_existing_films(config.destination_dirs)

        Console.debug(f'Checking list of duplicates for "{film.new_basename}"')
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
        Console.debug(f'Total duplicate copies of this film found: {len(duplicate_videos)}')

        for v in film.video_files:
            for d in duplicate_videos:
                # Mark each duplicate in the record
                if cls.decide(v, d) == Should.IGNORE:
                    film.ignore_reason = "Not an upgrade for existing version"

        # Sort so that ignores are first, so console can skip printing the rest
        sort_order = [Should.IGNORE, Should.UPGRADE, Should.KEEP_BOTH]
        duplicate_videos = [d for x in sort_order for d in duplicate_videos if d.duplicate_action == x]

        # Reverse the order in interactive mode and return
        return duplicate_videos if not config.interactive else duplicate_videos[::-1]

    @property
    def files(self) -> ('Film.File', ['Film.File']):
        """Retrieves a list of duplicate files in all dst paths,
        and markes the 'duplicate_action' attribute of each.

        Returns:
            tuple (Film.File, [Film.File]): Tuple list of duplicate files mapped 
            to the current film's video files
        """
        # Identify sets of files that are exact quality matches. While resolution, media,
        # or quality could be missing from a duplicate's filename, so we check these attrs.
        # Only YOU can prevent data loss!
        
        if not self._init:
            self.find()
        
        dupes = [v for f in self.duplicates for v in f.video_files]
        return [(Duplicates.File(d, v)) for d in dupes for v in f.video_files]
        
        d = [Film(dv).main_file for d in self.duplicates for dv in d.video_files]
        return [Duplicates.File(self.film, dv) for dv in d]

    @property
    def exact(self):
        """A subset of duplicates that are exact (except size) matches.

        Returns:
            list: [Film.File] of upgradeable duplicate files.
        """
        return [d for d in self.files if d.duplicate_result == ComparisonResult.EQUAL]
    
    @property
    def upgradable(self):
        """A subset of duplicates that are lower quality than the current file.

        Returns:
            list: [Film.File] of upgradeable duplicate files.
        """
        return [d for d in self.files if d.duplicate_action == Should.UPGRADE]

    @classmethod
    def decide(cls, current: 'Film.File', duplicate: 'Film.File') -> Should:
        """Determines how to handle the current file when a duplicate is detected.

        Config settings govern whether a duplicate can be upgraded if it is of
        a specific quality, e.g. a 1080p can be allowed upgrade a 720p, but a
        2160p cannot. Bluray can also upgrade WEBDL, for example.

        The return value of this method is an Enum, the result of which should
        incicate which action the src file should take against the duplicate:
            - upgrade: the current file should upgrade the duplicate
            - ignore: the current file should be skipped and the duplicate left intact
            - keep_both: both files should be kept, as they are treated as unique
        
        Args:
            current (Film.File): The current Film (file) object.
            duplicate (Film.File): Verified duplicate file that the current file 
            will be compared to.
       
        Returns:
            Enum, one of 'Should.UPGRADE', '.KEEP', or '.KEEP_BOTH'.
        """

        # If duplicate replacing is disabled, don't replace.
        if config.duplicates.automatic_upgrading is False:
            return cls._mark(Should.KEEP, duplicate, because=r.UPGRADING_DISABLED)

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

        r = ComparisonReason
        
        def upgrade_table(f): return config.duplicates.upgrade_table[f.resolution.key]
        
        (result, this) = Compare.quality(current, duplicate)
        
        duplicate.duplicate_result = result

        # If they're equal or not comparable, do nothing.
        if this == r.IDENTICAL:
            return cls._mark(Should.KEEP, duplicate, because=this)

        if result == ComparisonResult.NOT_COMPARABLE:
            return cls._mark(Should.KEEP_BOTH, duplicate, because=this)

        if this == r.HIGHER_RESOLUTION:
            if current.resolution in upgrade_table(duplicate):
                return cls._mark(Should.UPGRADE, duplicate, because=r.LOWER_RESOLUTION)
            else:
                return cls._mark(Should.KEEP_BOTH, duplicate, because=r.DIFFERENT_RESOLUTIONS)
            
        elif this == r.LOWER_RESOLUTION:
            if not duplicate.resolution in upgrade_table(current):
                return cls._mark(Should.KEEP_BOTH, duplicate, because=r.DIFFERENT_RESOLUTIONS)
            else:
                return cls._mark(Should.KEEP, duplicate, because=r.HIGHER_RESOLUTION)

        if this == r.HIGHER_QUALITY:
            return cls._mark(Should.UPGRADE, duplicate, because=r.LOWER_QUALITY)
        elif this == r.LOWER_QUALITY:
            return cls._mark(Should.KEEP, duplicate, because=r.HIGHER_QUALITY)
    
        if this == r.PROPER:
            return cls._mark(Should.UPGRADE, duplicate, because=r.NOT_PROPER)
        elif this == r.NOT_PROPER: 
            return cls._mark(Should.KEEP, duplicate, because=r.PROPER)
        
        if this == r.BIGGER:
            return cls._mark(Should.UPGRADE, duplicate, because=r.SMALLER)
        elif this == r.SMALLER: 
            return cls._mark(Should.KEEP, duplicate, because=r.BIGGER)

        # If up to this point we can't determine if we should upgrade or keep both, 
        # ignore the current file because it cannot be safely moved without risk of 
        # data loss. Chances are at this point everything is the same, except the 
        # current file is the same or smaller size than the duplicate.        
        return cls._mark(Should.KEEP, duplicate, r.NOT_COMPARABLE)

    @classmethod
    def _mark(cls, should: Should, d: 'Film.File', because: ComparisonReason = None) -> Should:
        """Update a file with the results of the comparison, including the action to be taken.
        
        Args:
            should (Should): Action to be taken against the duplicate
            duplicate (Film.File): Duplicate the current file was compared to
            reason (ComparisonReason): Reason why this file should or shouldn't be upgraded
        Returns:
            Enum, one of 'Should.UPGRADE', 'Should.IGNORE', or 'Should.KEEP_BOTH'.
        """
        d.duplicate_action = should
        d.duplicate_reason = because
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

    class File:
        """A class to retain a list of duplicate files in the dst dirs
        mapped to the action the current src film should take.
        
        Attributes:
            src_film (Film): Source film object
            dup_file (Film.File): Duplicate file
            action (Should): Action the src film should take against the file
            comparison (ComparisonResult): (Left) src primary file compared to (right) dst
        """
        
        def __init__(self, current: 'Film.File', duplicate: 'Film.File'):
            
            self.current = current
            self.duplicate = duplicate
            self.action = Duplicates.decide(current.main_file, duplicate)
            self.reason = duplicate.duplicate_reason
            
        def __repr__(self):
            return f"DuplicateFile('{self.duplicate.dst.parent}') " \
                   f"{self.action.name} " \
                   f"Because.{self.reason.name} " \
                   f"{self.duplicate.size.pretty()}"
