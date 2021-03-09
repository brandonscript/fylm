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

"""Main application logic.

This module scans for and processes films.

    processor: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
from typing import List

from fylmlib.film import Film
from fylmlib.console import console
from fylmlib.subtitle import Subtitle
from fylmlib.duplicates import duplicates
from fylmlib.interactive import interactive
import fylmlib.formatter as formatter
import fylmlib.operations as ops
import fylmlib.counter as counter
import fylmlib.notify as notify
import fylmlib.config as config

_move_queue = []

class processor:
    """Main class for scanning for and processing films.

    All methods are class methods, thus this class should never be instantiated.
    """

    @classmethod
    def iterate(cls, films: List[Film]):
        """Main entry point for processor, iterates a list of films.

        Args:
            films: (list(Film)) film objects to process.
        """

        for film in films:
            
            # Route film to correct handler
            cls.route(film)

            # Print blank line to separate next film
            console().print()

        # If we are running in interactive mode, we need to handle the moves
        # after all the lookups are completed in case we have long-running copy
        # operations.
        if config.interactive is True:

            # If we're moving more than one film, print the move header.
            queue_count = len(_move_queue)
            c = console().pink(f"{'Copying' if (config.safe_copy or not dirops.is_same_partition(src, dst)) else 'Moving'}")
            c.pink(f" {queue_count} {formatter.pluralize('file', queue_count)}...\n").print()

            # Process the entire queue
            cls.process_move_queue()

    @classmethod
    def route(cls, film: Film):
        """Route film processing to the correct handler.

        Args:
            films: (Film) film object to route.
        """

        # Print film header to console.
        console().print_film_header(film)
            
        if config.interactive is True and (not film.ignore_reason or film.ignore_reason.startswith('Unknown')):
            # If the film is rejected via the interactive flow, skip.
            if interactive.lookup(film) is False:
                return
        else:
            # Search TMDb for film details (if enabled).
            film.search_tmdb()

            # If the film still should be ignored after looking up, skip.
            if film.should_ignore is True:
                console().print_skip(film)
                return
            else:
                # If the lookup was successful, print the results to the console.
                console().print_search_result(film)

        # If duplicate checking is enabled and the film is a duplicate, rename
        # all the duplicates we do not want to keep so they can be deleted later.
        if len(film.existing_duplicate_files) > 0:

            console().print_duplicates(film)

            if config.interactive is True:

                # If interactive mode is enabled, a False return here
                # indicates we no longer want to keep this file, so
                # return.
                if not interactive.handle_duplicates(film):
                    return
            else:
                duplicates.rename_unwanted(film)

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

                    # Update the coujnter
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
    def prepare_file(cls, film: Film):
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

        # Generate a new source path based on the new filename and the
        # destination dir. In this case, we know that the first object
        # in .all_valid_files is the only file reference.
        dst = os.path.normpath(os.path.join(file.destination_path, file.new_filename_and_ext))

        # Move the file. (Only executes in live mode).
        # If this film is a duplicate and is set to replace an existing film, suppress
        # the overwrite warning.
        _move_queue.append((film, [_QueuedMoveOperation(film.all_valid_files[0], dst)]))

    @classmethod
    def prepare_folder(cls, film: Film):
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
            dst = os.path.normpath(os.path.join(file.destination_path, file.new_filename_and_ext))

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
    def cleanup_dir(cls, film: Film):
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
            console().indent().dark_gray('Removing parent folder').print()
            console.debug(f'Deleting {film.original_path}')

            # Delete the source dir and its contents
            ops.dirops.delete_dir_and_contents(film.original_path, max_size=1000)

class _QueuedMoveOperation(object):
    """A handler class for queued move operations.

    Each move operation contains a source and destination path that are passed
    as args to ops.fileops.safe_move()
    """
    def __init__(self, file: Film.File, dst: str):
        self.file = file
        self.dst = dst
    
    def do(self):
        """Passthrough function to call ops.fileops.safe_move()
        """

        if not os.path.exists(self.file.source_path):
            console().yellow().indent(f'\'{os.path.basename(self.file.source_path)}\' no longer exists or cannot be accessed').print()
            return False

        self.file.did_move = ops.fileops.safe_move(self.file.source_path, self.dst)

        # Clean up duplicates if all the files in the parent film have been moved
        if (len(self.file.parent_film.duplicate_files) > 0 
            and config.interactive is False 
            and len(list(filter(lambda m: m.did_move == False, self.file.parent_film.all_valid_files))) == 0):
            if config.interactive is False:
                duplicates.delete_unwanted(self.file.parent_film)

        return self.file.did_move

