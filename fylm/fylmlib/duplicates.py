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

import asyncio
from pathlib import Path

import nest_asyncio

from fylmlib.enums import *
from fylmlib.tools import *
import fylmlib.config as config
from fylmlib import Console, Compare, Find
from fylmlib import FilmPath, TMDb, Parallel
from fylmlib import IO, Delete
from fylmlib import Format as ƒ

class Duplicates:
    """Searches for copies of the specified film that exist in any dst dir.

    Args:
        film (Film): A film to check for duplicates.
    """

    TO_DELETE = []

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
    def rename_unwanted(cls, unwanted: ['Duplicates.Map']):
        """Rename duplicates pending upgrade to {name}.dup~.

        Args:
            unwanted [Duplicates.Map]: List of unwanted mappings to rename.
        """

        # Loop through each duplicate that should be replaced.
        for mp in unwanted:
            dst = FilmPath(f'{mp.duplicate}.dup~')
            if dst.exists():
                # Skip if it's already been renamed (edge case for when
                # there are multiple identical copies of the same film being moved)
                continue
            IO.rename(mp.duplicate, dst)
            cls.TO_DELETE.append(dst)

    @classmethod
    def handle(cls, film) -> bool:
        """Determines how to handle duplicates of the inbound film, either
        replacing, keeping both, or skipping.

        Args:
            film: (Film) Current film to process

        Returns:
            bool: Returns True if this film should be moved, otherwise False
        """

        if config.interactive is True:
            return

        if film.should_ignore:
            return False

        # Return immediately if the film is not a duplicate,
        # or if duplicates off, or rename on.
        if (len(film.duplicates) == 0
            or config.rename_only
            or not config.duplicates.enabled):
            return True

        Result = ComparisonResult

        move = []
        existing_to_delete = []

        # In case there are multiple video files in the original film,
        # we need to process each separately.
        for v in film.video_files:

            mp = film.duplicates.map(v)
            Console.print_duplicates(v, mp)

            exact = first(mp, where=lambda d: v.dst == d.duplicate.src, default=None)
            # same_quality = list(filter(lambda d: d.result == Result.EQUAL, mp))
            keep_existing = [d for d in mp if d.action == Should.KEEP_EXISTING]
            keep_both = [d for d in mp if d.action == Should.KEEP_BOTH]
            upgradable = [d for d in mp if d.action == Should.UPGRADE]

            if len(keep_existing) > 0 or (len(keep_both) == 0
                                          and len(upgradable) == 0):
                continue

            if exact and exact.action == Should.UPGRADE:
                existing_to_delete.append(exact)

            if len(upgradable) > 0 and len(keep_existing) == 0:
                existing_to_delete.extend(upgradable)

            Duplicates.rename_unwanted(list(set(existing_to_delete)))
            move.append(v)

        if len(move) == 0:
            film.ignore_reason = IgnoreReason.SKIP
            return False
        else:
            return True

    @classmethod
    def delete_upgraded(cls) -> int:
        """Delete upgraded duplicates on the destination dirs.

        If duplicates are found and the inbound film should replace them,
        we want to delete the copies on the destination dir that we don't
        want, and their parent folder, if it's empty.

        Args:
            film (Film): Film object to determine which duplicates to delete.

        Returns:
            The number of duplicate files deleted.
        """

        if len(cls.TO_DELETE) == 0:
            return 0

        d = Delete.files(*cls.TO_DELETE)
        for f in cls.TO_DELETE:
            if f.parent.exists() and f.parent.is_empty:
                Delete.dir(f.parent)
        Console().dim().blue(f'{INDENT}Removed {d} duplicate',
                       ƒ.pluralize('file', d)).print()
        cls.TO_DELETE = []
        return d

    def map(self, src: 'Film.File') -> ['Duplicates.Map']:
        """Maps the src Film.File against this object's duplicate files
        and returns a list of results, actions, and reasons as Map objects.

        Args:
            src (Film.File): Source file to compare against duplicates.

        Returns:
            [Map]: A list actions and reasons for each duplicate file.
        """

        loop = asyncio.get_event_loop()
        nest_asyncio.apply(loop)
        tasks = [loop.create_task(Duplicates.decide(src, d))
                 for d in self.files]
        mp = loop.run_until_complete(asyncio.gather(*tasks))
        return sorted(mp)

    @classmethod
    async def decide(cls, new: 'Film.File', duplicate: 'Film.File') -> 'Duplicates.Map':
        """Determines what action should be taken aginst a new or duplicate file.

        Args:
            new (Film.File): The new Film (file) object.
            duplicate (Film.File): Duplicate file in a dst dir.

        Returns:
            Duplicates.Map
        """

        Result = ComparisonResult
        Reason = ComparisonReason

        # If duplicate replacing is disabled, don't replace.
        if config.duplicates.automatic_upgrading is False:
            return cls.Map(new,
                           duplicate,
                           None,
                           Should.KEEP_EXISTING,
                           Reason.UPGRADING_DISABLED)

        def rez_can_upgrade(l, r):
            key = r.resolution.key if r.resolution.value <= 3 else 'SD'
            t = config.duplicates.upgrade_table[key]
            return t and l.resolution.key in t

        # Read as 'new' is {rslt} {reason} than 'duplicate', e.g.
        # 'new' is HIGHER RESOLUTION than 'duplicate'.
        (rslt, reason) = Compare.quality(new, duplicate)
        should = Should.KEEP_EXISTING  # Default, it is the least destructive choice

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

        return cls.Map(new, duplicate, rslt, should, reason)

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

        def __init__(self,
                     new: 'Film.File',
                     duplicate: 'Film.File',
                     result: ComparisonResult,
                     action: Should,
                     reason: ComparisonReason):
            self.new = new
            self.duplicate = duplicate
            (self.result, self.action, self.reason) = (result, action, reason)

        def __repr__(self):
            return f"DuplicateMap('{self.new.dst.name}' || '{self.duplicate.name}') " \
                   f"new is {self.result.name} " \
                   f"{self.reason.name}, " \
                   f"should {self.action.name} " \
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

