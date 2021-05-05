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

"""Main application logic.

This module scans for and processes films.

    processor: the main class exported by this module.
"""

import os
import sys
from typing import List
import asyncio
import time
from timeit import default_timer as timer

from halo import Halo

import fylmlib.config as config
import fylmlib.counter as counter
from fylmlib.enums import *
from fylmlib import Console
from fylmlib import Find
from fylmlib import Move
from fylmlib import Parallel
from fylmlib import Format as ƒ
from fylmlib import Notify
from fylmlib import TMDb
from fylmlib import Interactive
from fylmlib import Duplicates
from fylmlib import Subtitle
from fylmlib import Film
from fylmlib import Info
from fylmlib.tools import *
from fylmlib.constants import *

MOVE_QUEUE = []

class App:
    """Main class for scanning for and processing films.

    All methods are class methods, thus this class should never be instantiated.
    """

    @staticmethod
    def run():
        """Main entry point for Fylm."""
        
        filmroots = filter(lambda f: f.is_filmroot, map(Film, Find.new()))
        filmroots = Find.sync_parallel(filmroots, attrs=['filmrel', 'year', 'size'])
        
        NEW = sorted(filmroots, key=lambda f: f.name.lower())
        # NEW = list(Find.sync_parallel(iter(NEW), attrs=['filmrel', 'year', 'size']))
        
        if len(NEW) == 0:
            return  # TODO:

        potential = f"Found {len(NEW)} possible new {ƒ.pluralize('film', len(NEW))}"
        c = Console().pink(potential).print()
        if config.duplicates.enabled:
            Console().pink(f"Loading existing films...").print()
            Duplicates.ALL = Find.existing()
            Console.up().clearline()
            c = Console().pink(f'{potential}')
            c.add(f' and')
            c.add(f"{' no' if len(Duplicates.ALL) == 0 else len(Duplicates.ALL)}")
            c.add(f" existing {ƒ.pluralize('film', len(Duplicates.ALL))}")
            c.print()
        
        if config.tmdb.enabled:
            
            # Search TMDb
            start = timer() # TODO: This is yuck; separate out.
            spinner = Halo(text='Searching TMDb...',
                         spinner='dots',
                         color='yellow',
                         text_color='yellow')
            if not config.debug: spinner.start()
            
            TMDb.Search.parallel(*NEW)
            
            spinner.stop()
            Console().green(f'{CHECK} Done searching TMDb '
                            ).dark_gray(f'({round(timer() - start)} seconds)'
                            ).print()
            
            Console.wait(1.5)
            Console.clearline()
            
        QUEUE = []
        
        NEW = [f for f in NEW if not f.should_hide]
        
        for film in NEW:
            
            if not film.exists():
                film.ignore_reason = IgnoreReason.DOES_NOT_EXIST
                
            film.duplicates = Duplicates(film)
            
            Console.print_film_header(film) # TODO: Combine these into a single header
            if config.interactive:
                # TODO: interactive prompt
                # If the film is rejected via the interactive flow, skip.
                # Do an interactive lookup
                Interactive.lookup(film)
                Interactive.handle_duplicates(film)
                # if 
                # If interactive mode is enabled, a False return here
                # indicates we no longer want to keep this file, so
                # return.
                # TODO: duplicates.rename_unwanted(film)
            
            if film.should_ignore is True:
                Console().print_skip(film)
                continue
            
            if not config.interactive:
                Console.print_src_dst(film)    
                Console.print_duplicates(film)
            
            if config.rename_only:
                # TODO: print_rename()
                pass
            elif (config.always_copy or 
                    not Info.is_same_partition(film.src.parent, film.dst)):
                # TODO: print_copy()
                # add to move queue
                pass
            else:
                # Update the counter with a successful move
                film.move()
                if all([f.did_move for f in film.files]):
                    counter.COUNT += 1
                
                # Add this film to the moved duplicates
                Duplicates.ALL.append(film)
                                
        if len(QUEUE) > 0:
            Console().pink(
                f"\nPreparing to copy {len(QUEUE)} {ƒ.pluralize('film', len(QUEUE))}...").print()
                # TODO: process queue

        # # Route to the correct handler if the film shouldn't be skipped
        # [cls.route(film) for film in films if not film.should_skip]
                        
        # # If we are running in interactive mode, we need to handle the moves
        # # after all the lookups are completed in case we have long-running copy
        # # operations.
        # if config.interactive is True:

        #     # If we're moving more than one film, print the move header.
        #     queue_count = len(_move_queue)
        #     c = console().pink(f"\n{'Copying' if config.safe_copy else 'Moving'}")
        #     c.pink(f" {queue_count} {formatter.pluralize('file', queue_count)}...").print()

        #     # Process the entire queue
        #     cls.process_move_queue()

    @classmethod
    def route(cls, film: 'Film'):
        """Route film processing to the correct handler.

        Args:
            films: (Film) film object to route.
        """

        # Print film header to console.
        # console().print_film_header(film)
            
        # if config.interactive is True:
            
        # else:
        #     # If the film still should be ignored after looking up, skip.
            

        # If duplicate checking is enabled and the film is a duplicate, rename
        # all the duplicates we do not want to keep so they can be deleted later.
        # When getting `verified_duplicate_files`, duplicate upgrade/ignore checking
        # is also executed.
        if len(film.verified_duplicate_files) > 0:

            console().print_duplicates(film)

            if config.interactive is True:

                # If interactive mode is enabled, a False return here
                # indicates we no longer want to keep this file, so
                # return.
                if not interactive.handle_duplicates(film):
                    return
            else:
                duplicates.rename_unwanted(film)

        if not film.should_ignore or config.interactive is True or config.duplicates.force_overwrite:
            # If it is a file and as a valid extension, process it as a file
            if film.is_file and film.all_valid_files[0].has_valid_ext:
                cls.prepare_file(film)

            # Otherwise if it's a folder, process it as a folder containing
            # potentially multiple related files.
            elif film.is_folder:
                cls.prepare_folder(film)

        # If we're not running in interactive mode, do all the moving 
        # on a first-in-first out basis.
        if config.interactive is False:
            cls.process_move_queue()

    @classmethod
    def process_move_queue(cls):

        global _move_queue

        # Enumerate the move/copy queue and execute
        for film, queued_ops in _move_queue:

            if config.interactive is True:
                console().print_film_header(film)

            copied_files = 0

            # Determine the destination path for the film
            dst_path = queued_ops[0].dst

            if film.source_path == dst_path:
                console().indent().dark_gray('Already renamed').print()

            for move in queued_ops:

                # Execute the move/copy and print details
                console().print_move_or_copy(move.file.parent_film.source_path, dst_path, move.dst)
                copied_files += move.do()

            # If the move is successful...
            if copied_files == len(queued_ops):

                for file in film.all_valid_files:

                    # Update the counter
                    if file.is_video:
                        counter.add(1)

                        # Notify Pushover
                        notify.pushover(file.parent_film)

                    # Clean up the source dir (only executes if it's a dir)
                    cls.cleanup_dir(file.parent_film)

                    # Update the film's source_path its new location once all files have been moved.
                    file.source_path = dst_path

            if config.interactive is True:
                # Print blank line to separate next film
                console().print()

        # When move/copy operations are complete, empty the queue.
        _move_queue = []

    @classmethod
    def prepare_file(cls, film: 'Film'):
        """Process a single file film object.

        Args:
            film: (Film) film object to process.
        """

        global _move_queue

        # Get the main file
        file = film.all_valid_files[0]

        # Rename the source file to its new filename
        ops.fileops.rename(file.source_path, file.new_filename_and_ext)

        # Update the source path of the film if we're running in live mode
        # to its new name, otherwise the move will fail (because it will 
        # be looking for its original filename).
        if config.test is False:
            film.source_path = os.path.normpath(os.path.join(os.path.dirname(file.source_path), file.new_filename_and_ext))
            film.all_valid_files[0].source_path = film.source_path

        # In this case, we know that the first object in .all_valid_files is the only file reference.
        # Move the file. (Only executes in live mode).
        # If this film is a duplicate and is set to replace an existing film, suppress
        # the overwrite warning.
        _move_queue.append((film, [_QueuedMoveOperation(film.all_valid_files[0])]))

    @classmethod
    def prepare_folder(cls, film: 'Film'):
        """Process a directory film object containing one or more files.

        Args:
            film: (Film) film object to process.
        """

        # Create a list to hold queued files. This is used to guarantee
        # uniqueness in name.
        uniqueness_map = []

        move_constructor = (film, [])

        # Enumerate valid files.
        for file in film.all_valid_files:
            # Generate a new destination based on the film's title, and alter it
            # depending on whether the file is a subtitle, or if it needs to be
            # renamed to prevent clobbering.
            dst = file.destination_path

            # If it is a subtitle, we try to find the language.
            if file.is_subtitle:
                # Insert the language into the subtitle filename.
                dst = Subtitle(file.new_filename).insert_lang(dst) or dst

            # Append the destination to the queued files list
            uniqueness_map.append(dst)

            # Check if a file with the identical name exists more than once in the queue.
            # If so, handle the filename conflict by appending a number to the filename.
            # e.g. My Little Pony.srt would become My Little Pony.1.srt if its already
            # in the queue.
            if uniqueness_map.count(dst) > 1:
                new_filename, ext = os.path.splitext(dst)

                # If there's a duplicate filename, we need to rename each file
                # sequentially to prevent clobbering.   
                dst = f'{new_filename}.{uniqueness_map.count(dst) - 1}{ext}'
            
            # Rename the source file to its new filename
            ops.fileops.rename(file.source_path, os.path.basename(dst))

            # Update source with the newly renamed path, derived from destination name, in 
            # case it was altered by subtitle or duplicate clobber prevention. Only run
            # in live mode.
            if config.test is False:
                file.source_path = os.path.normpath(os.path.join(os.path.dirname(file.source_path), os.path.basename(dst)))

            # Move the file. (Only executes in live mode).
            # If this film is a duplicate and is set to replace an existing film, suppress
            # the overwrite warning.
            move_constructor[1].append(_QueuedMoveOperation(file, dst))

        # Add the current film's queued files to the move queue.
        _move_queue.append(move_constructor)

    @classmethod
    def cleanup_dir(cls, film: 'Film'):
        """Clean up a directory film object after it has been moved.

        Args:
            film: (Film) film object to process.
        """

        # Do not try to delete unwanted files if the film isn't in a folder.
        # That means it's the root src directory, and contains other files.
        if not film.is_folder:
            return

        # Recursively delete unwanted files and set the count.
        deleted_files_count = ops.dirops.delete_unwanted_files(film.source_path)

        # Print results of removing unwanted files.
        if config.remove_unwanted_files and deleted_files_count > 0:
            console().dim(f"Cleaned {deleted_files_count} unwanted {formatter.pluralize('file', deleted_files_count)}")

        # Remove the original source parent folder, if it is safe to do so (and
        # the feature is enabled in config). First check that the source folder is
        # empty, and that it is < 1 KB in size. If true, remove it. We also
        # don't want to try and remove the source folder if the original source
        # is the same as the destination.

        if config.remove_source and film.original_path != film.destination_path:
            console().dark_gray().indent().add('Removing parent folder').print()
            debug(f'Deleting {film.original_path}')

            # Delete the source dir and its contents
            ops.dirops.delete_dir_and_contents(film.original_path, max_size=1000)

class _QueuedMoveOperation():
    """A handler class for queued move operations.

    Each move operation contains a source and destination path that are passed
    as args to ops.fileops.safe_move()
    """
    def __init__(self, file: 'Film.File', dst: str=None):
        self.file = file
        self.dst = dst or file.destination_path
    
    def do(self):
        """Passthrough function to call ops.fileops.safe_move()
        """

        if not os.path.exists(self.file.source_path):
            console().yellow().indent(f'\'{os.path.basename(self.file.source_path)}\' no longer exists or cannot be accessed').print()
            return False

        # If an identically named duplicate exists, check the upgrade table to see if it is OK for upgrade
        should_upgrade = len(duplicates.find_exact(self.file.parent_film)) > 0 and len(duplicates.find_upgradable(self.file.parent_film)) > 0

        # Execute the move
        self.file.did_move = ops.fileops.safe_move(self.file.source_path, self.file.destination_path, should_upgrade)

        # Clean up duplicates if all the files in the parent film have been moved
        if (len(self.file.parent_film.duplicate_files) > 0 
            and config.interactive is False 
            and len(list(filter(lambda m: m.did_move == False, self.file.parent_film.all_valid_files))) == 0):
            duplicates.delete_upgraded(self.file.parent_film)

        return self.file.did_move
