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
import asyncio
from pathlib import Path

from asyncinit import asyncinit
import nest_asyncio

from fylmlib.enums import *
from fylmlib.tools import *
import fylmlib.config as config
from fylmlib import Console, Compare, Find
from fylmlib import FilmPath, TMDb, Parallel
from fylmlib import IO

class Duplicates:
    """Searches for copies of the specified film that exist in any dst dir.
    
    Args:
        film (Film): A film to check for duplicates.
    """
    
    ALL = []
    
    def __init__(self, src: 'Film'):
        
        from fylmlib import Film
        
        self._init = False
        self.src = src
        
        if not config.duplicates.enabled or config.rename_only:
            Console.debug('Duplicate checking is disabled, skipping.')
            self.films = []

        Console.debug(
            f"Looking for duplicates of '{self.src.title} ({self.src.year})'")

        self.films = list(
            filter(lambda d: iterlen(d.video_files) > 0, 
                map(Film, Find.glob(*set(config.destination_dirs.values()),
                          search=f"{self.src.title} {self.src.year}"))
                )
            )
        
    def __repr__(self):        
        if len(self) == 0:
            return "Duplicates(None)"
        x = f"Duplicates('{self.src.new_name}')\n"
        segments = 3 if config.use_folders else 2
        x += '\n'.join([f" ﹂File('{Path(*f.parts[-segments:])}')" for f in self.files])
        return x
    
    def __len__(self):
        return len(self.films)
    
    @property
    def files(self) -> ['Film.File']:
        """Retrieves a list of duplicate files in all dst paths.
        Returns:
            List of duplicate Film.File objects.
        """
        return [v for f in self.films for v in f.video_files]
    
    def map(self, src: 'Film.File') -> ['Duplicates.Map']:
        """Maps the src Film.File against this object's duplicate files
        and returns a list of results, actions, and reasons as Map objects.

        Args:
            src (Film.File): Source file to compare against duplicates.

        Returns:
            [Map]: A list actions and reasons for each duplicate file.
        """

        loop = asyncio.get_event_loop()
        tasks = asyncio.gather(*[
            asyncio.ensure_future(Duplicates.Map(src, d))
            for d in self.files
        ])
        mp = loop.run_until_complete(tasks)

        # Reverse the order in interactive mode and return
        # return mp if not config.interactive else mp[::-1]
        return sorted(mp)

    # @classmethod #DEPRECATED:
    # def find_old(cls, film: 'Film') -> ['Film.File']:
    #     """From a list of existing films, return those that contain
    #     one or more duplicate files.

    #     Compare the film objects to an array of exsiting films in
    #     order to determine if any duplicates exist at the destination.
    #     Criteria for a duplicate: title and year must match.

    #     Returns:
    #         An array of duplicate films objects for the specified file.
    #     Args:
    #         film (Film): Film to check for duplicates.
    #     """

    #     # If check for duplicates is disabled, return an empty array (because we don't care if they exist).
    #     # DANGER ZONE:
    #     # With check_for_duplicates disabled and force_overwrite enabled, any files
    #     # with the same name at the destination will be silently overwritten.
    #     if config.duplicates.enabled is False or config.rename_only is True:
    #         Console.debug('Duplicate checking is disabled, skipping.')
    #         return []

    #     existing_films = dirops.get_existing_films(config.destination_dirs)

    #     Console.debug(f'Checking list of duplicates for "{film.new_basename}"')
    #     # Filter the existing_films cache array to titles beginning with the first letter of the
    #     # current film, then filter to check for duplicates. Then we filter out empty folder,
    #     # folders with no valid media folders, and keep only non-empty folders and files.

    #     duplicates = list(filter(lambda x:
    #             # First letter of the the potential duplicate's title must be the same.
    #             # Checking this first allows us to have a much smaller list to compare against.
    #             film.title[0] == x.title[0]

    #             # Check that the film is a legitimate duplicate
    #             and compare.is_duplicate(film, x)

    #             and ((
    #                 # If the potential duplicate is a folder, check that it contains at least
    #                 # one valid file.
    #                 x.is_folder and len(x.video_files) > 0)

    #                 # Or if it is a file, it is definitely a duplicate.
    #                 or x.is_file),

    #         # Perform the filter against the existing films cache.
    #        existing_films))

    #     duplicate_videos = list(itertools.chain(*[d.video_files for d in duplicates]))
    #     Console.debug(f'Total duplicate copies of this film found: {len(duplicate_videos)}')

    #     for v in film.video_files:
    #         for d in duplicate_videos:
    #             # Mark each duplicate in the record
    #             if cls.decide(v, d) == Should.IGNORE:
    #                 film.ignore_reason = "Not an upgrade for existing version"

    #     # Sort so that ignores are first, so console can skip printing the rest
    #     sort_order = [Should.IGNORE, Should.UPGRADE, Should.KEEP_BOTH]
    #     duplicate_videos = [d for x in sort_order for d in duplicate_videos if d.duplicate_action == x]

    #     # Reverse the order in interactive mode and return
    #     return duplicate_videos if not config.interactive else duplicate_videos[::-1]

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
    def decide(cls, new: 'Film.File', duplicate: 'Film.File') -> (ComparisonResult, 
                                                                  Should, 
                                                                  ComparisonReason):
        """Determines what action should be taken aginst a new or duplicate file.
        
        Args:
            new (Film.File): The new Film (file) object.
            duplicate (Film.File): Duplicate file in a dst dir.
       
        Returns:
            tuple(ComparisonResult, Should, ComparisonReason)
        """

        Result = ComparisonResult
        Reason = ComparisonReason

        # If duplicate replacing is disabled, don't replace.
        if config.duplicates.automatic_upgrading is False:
            return (None, 
                    Should.KEEP_EXISTING, 
                    Reason.UPGRADING_DISABLED)
                
        def rez_can_upgrade(l, r): 
            t = config.duplicates.upgrade_table[r.resolution.key]
            return t and l.resolution.key in t
        
        # Read as 'new' is {rslt} {reason} than 'duplicate', e.g.
        # 'new' is HIGHER RESOLUTION than 'duplicate'.
        (rslt, reason) = Compare.quality(new, duplicate)
        should = Should.KEEP_EXISTING # Default, it is the least destructive choice
        
        if reason == Reason.IDENTICAL:
            should = Should.KEEP_EXISTING

        elif rslt in [Result.NOT_COMPARABLE, Result.DIFFERENT]:
            should = Should.KEEP_BOTH
            
        elif reason == Reason.RESOLUTION:
            if rslt == Result.HIGHER and rez_can_upgrade(new, duplicate):
                should = Should.UPGRADE
            elif rslt == Result.LOWER and rez_can_upgrade(duplicate, new):
                should = Should.KEEP_EXISTING
            else:
                rslt = Result.DIFFERENT
                should = Should.KEEP_BOTH

        elif rslt == Result.HIGHER:
            should = Should.UPGRADE
        elif rslt == Result.LOWER:
            should = Should.KEEP_EXISTING
                
        return (rslt, should, reason)
    

    @staticmethod
    def rename_unwanted(unwanted: ['Duplicates.Map']):
        """Rename duplicates pending upgrade to {name}.dup.
        
        Args:
            unwanted [Duplicates.Map]: List of unwanted mappings to rename.
        """

        # Loop through each duplicate that should be replaced.
        for mp in unwanted:
            print(mp)
            dst = Path(f'{mp.duplicate}.dup')
            if dst.exists():
                # Skip if it's already been renamed (edge case for when
                # there are multiple identical copies of the same film being moved)
                continue
            IO.rename(mp.duplicate, dst)

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

    @asyncinit
    class Map:
        """A class to compare and retain a list of duplicate files in the dst dirs
        describing the action and rationale the current new film should take.
        
        Attributes:
            new (Film.File): Source file
            duplicate (Film.File): Duplicate file
            result (ComparisonResult): Quality difference between new and duplicate.
                                       Note that EQUAL does not compare size.
            action (Should): Action to take on the new or duplicate.
            reason (ComparisonReason): Reason why the action was chosen.
        """
        
        async def __init__(self, new: 'Film.File', duplicate: 'Film.File'):
            self.new = new
            self.duplicate = duplicate
            (self.result, self.action, self.reason) = Duplicates.decide(new, duplicate)
            
        def __repr__(self):
            return f"DuplicateMap('{self.new.dst.name}' || '{self.duplicate.name}') " \
                   f"{self.result.name} " \
                   f"{self.reason.name} " \
                   f"{self.action.name} " \
                   f"{self.duplicate.size.pretty()}"
                   
        def __lt__(self, other):
            return (
                (self.action == Should.KEEP_EXISTING
                 and other.action != Should.KEEP_EXISTING) or
                (self.result == ComparisonResult.HIGHER 
                 and other.result != ComparisonResult.HIGHER) or
                (self.result == ComparisonResult.EQUAL 
                 and other.result == ComparisonResult.LOWER) or
                (self.action == Should.UPGRADE
                 and other.action == Should.KEEP_BOTH) or
                (self.reason == ComparisonReason.SIZE
                 and other.reason != ComparisonReason.SIZE) or
                (self.reason == ComparisonReason.SIZE
                 and other.reason == ComparisonReason.SIZE
                 and self.duplicate.size.value > other.duplicate.size.value))
    
    class MapSync(Map):
        """Sync initalizer for Map"""
        
        def __init__(self, new: 'Film.File', duplicate: 'Film.File'):
            loop = asyncio.get_event_loop()
            if loop.is_running():
                nest_asyncio.apply(loop)
            mp = loop.run_until_complete(super().__init__(new, duplicate))
            self.__dict__ = mp.__dict__
