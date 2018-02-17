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

"""Main application logic.

This module scans for and processes films.

    process: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os

from fylmlib.config import config
from fylmlib.console import console
from fylmlib.subtitle import Subtitle
from fylmlib.duplicates import duplicates
import fylmlib.operations as ops
import fylmlib.counter as counter
import fylmlib.notify as notify

class process:
    """Main class for scanning for and processing films.

    All methods are class methods, thus this class should never be instantiated.
    """

    # TODO: (Possible) handle multiple editions stored in the same folder.
    @classmethod
    def file(cls, film):
        """Process a single file film object.

        Args:
            film: (Film) film object to process.
        """

        # Rename the source file to its new filename
        ops.fileops.rename(film.source_path, film.new_filename__ext())

        # Update the source path of the film if we're running in live mode
        # to its new name, otherwise the move will fail (because it will 
        # be looking for its original filename).
        if config.test is False:
            film.source_path = os.path.normpath(os.path.join(os.path.dirname(film.source_path), film.new_filename__ext()))

        # Generate a new source path based on the new filename and the
        # destination dir.
        dst = os.path.normpath(os.path.join(film.destination_dir, film.new_filename__ext()))

        if film.source_path != dst:
            console.info(cls._console_move_string(film.source_path, dst))
        else:
            console.dim('Already moved and renamed')

        # Move the file. (Only executes in live mode).
        # If this film is a duplicate and is set to replace an existing film, suppress
        # the overwrite warning.
        should_replace = film.is_duplicate and duplicates.should_replace(film, dst)
        if ops.fileops.safe_move(film.source_path, dst, expected_size=film.size, should_replace=should_replace):

            # If move was successful, update the counter.
            counter.add(1)

            # Notify Pushover
            notify.pushover(film)

        # Update the film's source_path again with its final destination.
        film.source_path = dst

    @classmethod
    def dir(cls, film):
        """Process a directory film object.

        Args:
            film: (Film) film object to process.
        """

        # Create a local counter to track deleted (unwanted) files.
        deleted_files_count = 0

        # Create a list to hold queued files. This is used to guarantee
        # uniqueness in name.
        queued_files = []

        # Create a counter to track successfully copied files.
        copied_files = 0
        expected_files = len(film.valid_files)

        # Enumerate valid files.
        for file in film.valid_files:

            # Split filename and ext for inner file.
            src = file
            ext = os.path.splitext(file)[1]

            # Generate a new filename based on the film's title, and alter it
            # depending on whether the file is a subtitle, or if it needs to be
            # renamed to prevent clobbering.
            dst = os.path.normpath(os.path.join(film.destination_dir, film.new_filename__ext(ext)))

            # If it is a subtitle, we try to find the language.
            if Subtitle.is_subtitle(src):
                # Insert the language into the subtitle filename.
                dst = Subtitle(src).insert_lang(dst) or dst

            # Append the destination to the queued files list
            queued_files.append(dst)

            # Check if a file with the same name exists more than once in the queue.
            # If so, handle the filename conflict by appending a number to the filename.
            # e.g. My Little Pony.srt would become My Little Pony.1.srt if its already
            # in the queue.
            if queued_files.count(dst) > 1:
                new_filename, ext = os.path.splitext(dst)

                # If there's a duplicate filename, we need to rename each file
                # sequentially to prevent clobbering.
                dst = '{}.{}{}'.format(new_filename, queued_files.count(dst) - 1, ext)

            # Rename the source file to its new filename
            ops.fileops.rename(src, os.path.basename(dst))


            # Update source with the newly renamed path, derived from destination name, in 
            # case it was altered by subtitle or duplicate clobber prevention.
            src = os.path.normpath(os.path.join(os.path.dirname(src), os.path.basename(dst)))

            if src != dst:
                console.info(cls._console_move_string(src, dst))
            else:
                console.dim('Already moved and renamed')

            # Move the file. (Only executes in live mode).
            # If this film is a duplicate and is set to replace an existing film, suppress
            # the overwrite warning.
            should_replace = film.is_duplicate and duplicates.should_replace(film, dst)
            if ops.fileops.safe_move(src, dst, expected_size=film.size, should_replace=should_replace):

                # If move was successful, update the counter.
                counter.add(1)

                # Update the list of copied files
                copied_files += 1

        # If the number of copied files matches the number of valid files, then
        # we can send the pushover notification.
        if copied_files == expected_files:

            # Notify Pushover of successful move.
            notify.pushover(film)

        # Recursively delete unwanted files and update the count.
        deleted_files_count = ops.dirops.delete_unwanted_files(film.source_path, deleted_files_count)

        # Update the film's source_path to the new location of its parent folder at 
        # the destination once all files have been moved.
        film.source_path = film.destination_dir

        # Print results of removing unwanted files.
        if config.remove_unwanted_files and deleted_files_count > 0:
            console.dim('Cleaned {} unwanted file{}'.format(deleted_files_count, '' if deleted_files_count == 1 else 's'))

        # Remove the original source parent folder, if it is safe to do so (and
        # the feature is enabled in config). First check that the source folder is
        # empty, and that it is < 1 KB in size. If true, remove it. We also
        # don't want to try and remove the source folder if the original source
        # is the same as the destination.
        if config.remove_source and film.original_path != film.destination_dir:
            console.debug('Removing parent folder {}'.format(film.original_path))

            # Max size a dir can be to qualify for removal
            max_size = 1000
            if (ops.size(film.original_path) < max_size and len(ops.dirops.find_deep(film.original_path)) == 0) or config.test:

                # Check that the file is smaller than max_size, and deep count the number
                # of files inside. Automatically ignores system files like .DS_Store.
                # If running in test mode, we 'mock' this response by pretending the folder
                # was removed.
                console.dim('Removing parent folder')
                ops.dirops.delete_dir_and_contents(film.original_path, max_size)
            else:

                # If the parent folder fails the deletion qualification, print to console.
                console.warn('Will not remove parent folder because it is not empty')

    @classmethod
    def _console_move_string(cls, src, dst):
        return '{} to {}'.format(
            'Copying' if (config.safe_copy or not ops.dirops.is_same_partition(src, dst)) else 'Moving', 
            os.path.dirname(dst))


