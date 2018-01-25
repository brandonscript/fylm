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

"""File/directory and size utilities for Fylm operations

A collection of class methods that handles file system CRUD operations, like
get, move, rename, and delete. Also includes filesize detector methods.

    dirops: directory operations exported by this module.
    fileops: file operations exported by this module.
    size: file and dir size calculator
"""

from __future__ import unicode_literals

import os
import shutil
import sys
import errno
import unicodedata
from itertools import islice

from fylmlib.config import config
from fylmlib.console import console
import fylmlib.formatter as formatter

class dirops:
    """Directory-related class method operations.
    """
    @classmethod
    def verify_paths_exist(cls, paths):
        """Verifies that the specified paths (array) exist.

        Loops through an array of paths to check that each one exists. If any do not,
        raise an Exception. Primarily used at app initiation time to verify that source
        and destination paths are in working order.

        Args:
            paths: (list) paths to verify existence.
        """
        for d in (d for d in paths if not os.path.exists(d)):
            console.error("'{}' does not exist; check folder path in config.yaml".format(d))

    @classmethod
    def get_existing_films(cls, path):
        """Get a list of existing films.

        Scan one level deep of the target path to get a list of existing films. Since
        this is used exclusively for duplicate checking, this method is skipped when
        duplicate checking is disabled. Sets the global property `existing_films.cache`
        when complete.

        Args:
            path: (unicode) path to search for existing films.
        Returns:
            A list of existing Film objects.
        """

        # Import Film here to avoid circular import conflicts.
        from fylmlib.film import Film

        # If check_for_duplicates is disabled, we don't care about duplicates, and
        # don't need to spend cycles processing duplicates. Return an empty array.
        if config.check_for_duplicates is False:
            return

        # Enumerate the destination directory and check for duplicates.
        console.debug('Checking for existing films...')

        # Map a list of valid and sanitized files to Film objects
        existing_films = map(
            Film,
            [os.path.normpath(os.path.join(config.destination_dir, file)) for file in cls.sanitize_dir_list(os.listdir(path))]
        )
        console.debug('Found {}'.format(len(existing_films)))
        return existing_films

    @classmethod
    def get_new_films(cls, path):
        """Get a list of new potenial films we want to tidy up.

        Scan one level deep of the target dpathir to get a list of potential new files/folders.

        Args:
            path: (unicode) path to search for new films.
        Returns:
            An array of potential films.
        """

        # Import Film here to avoid circular import conflicts.
        from fylmlib.film import Film

        # Enumerate the search path for files/subfolders, sanitize them, then finally sort
        # the resulting list of files alphabetically, case-insensitive.
        sorted_files = sorted(cls.sanitize_dir_list(os.listdir(path)), key=lambda s: s.lower())

        # If using the `limit` option, create a sliced list to limit the number of
        # files to be processed.
        limited_files = islice(sorted_files, config.limit if config.limit > 0 else None)

        # Map the sorted/filtered list to Film objects.
        return map(Film, [os.path.join(path, file) for file in limited_files])

    @classmethod
    # Check for valid file types inside this path
    def get_valid_files(cls, path):
        """Get a list valid files inside the specified path.

        Scan deeply in the specified path to get a list of valid files, as
        determined by the config.video_exts and config.extra_exts properties.

        Args:
            path: (unicode) path to search for valid files.
        Returns:
            An array of valid files.
        """

        # Call dirops.find_deep to search for files within the specified path.
        # Filter the results using a lambda function.
        valid_files = cls.find_deep(path, lambda x:

            # A valid file must have a valid extension
            fileops.has_valid_ext(x)

            # It must not contain an ignored string (e.g. 'sample')
            and not fileops.contains_ignored_strings(x)

            # And it must be at least a certain filesize
            and size(x) >= config.min_filesize * 1024 * 1024)

        # If debugging, print the resulting list of files
        for f in valid_files:
            console.debug('   Found "{}" ({}) in {}'.format(
                os.path.basename(f),
                formatter.pretty_size(size(f)), path))
        return valid_files

    @classmethod
    def sanitize_dir_list(cls, files):
        """Sanitize a directory listing using unicode normalization and by
        omitting system files.

        On macOS, unicode normalization must take place for loading files with
        unicode chars. This method correctly normalizes these strings.
        It also will remove .DS_Store and Thumbs.db from the list, since we
        don't ever care to count, or otherwise observe, these system files.

        Args:
            files: (unicode) list of files in dir.
        Returns:
            A sanitized, unicode-ready array of files.
        """
        return filter(lambda f: f != '.DS_Store' and f != 'Thumbs.db', [unicodedata.normalize('NFC', file) for file in files])

    @classmethod
    def get_invalid_files(cls, path):
        """Get a list of invalid files inside the specified dir.

        Scan deeply in the specified dir to get a list of invalid files, as
        determined by the config.video_exts and config.extra_exts properties.
        We do not check filesize here, because while we may not want to
        rename and move vide/extra files that are too small, we probably
        don't want to delete them.

        Args:
            path: (unicode) path to search for invalid files.
        Returns:
            An array of invalid files.
        """

        # Call dir.find_deep to search for files within the specified dir.
        # Filter the results using a lambda function.
        return cls.find_deep(path, lambda x:

            # An invalid file might contain an ignored string (e.g. 'sample')
            fileops.contains_ignored_strings(x)

            # Or it may not have a valid file extension
            or not fileops.has_valid_ext(x))

    @classmethod
    def create_deep(cls, path):
        """Deeply create the specified path and any required parent paths.

        Using recursion, create a directory tree as specified in the path
        param.

        Args:
            path: (unicode) path to create.
        """

        # Because this is a destructive action, we will not create the
        # path tree if running in test mode.
        if not config.test:

            # If the path exists, there's no point in trying to create it.
            if not os.path.exists(path):
                try:
                    console.debug("Creating destination {}".format(path))
                    os.makedirs(path)
                # If the dir creation fails, raise an Exception.
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        console.error('Unable to create {}'.format(path))

    @classmethod
    def find_deep(cls, root_dir, func=None):
        """Deeply search the specified dir and return all files.

        Using recursion, search the specified path for files.
        Pass an optional function to filter results.

        Args:
            root_path: (unicode) path to search for files.
            func: (function) user-defined or lambda function to use as a filter.
        Returns:
            A filtered array of files.
        """

        # Use os.walk() to recursively search the dir and return full path of each file.
        results = [os.path.join(root, f) for root, dirs, files in os.walk(root_dir) for f in files]

        # Sanitize the resulting file list, then call the (optional) filter function that was passed.
        return filter(func, cls.sanitize_dir_list(results))

    @classmethod
    def delete_dir_and_contents(cls, path, max_size=50000):
        """Recursively delete dir path and all its contents, if less than max_size.

        Using recursion, delete all files and folders in the specified dir and
        itself if the total dir size is less than max_size (default 50 KB).

        Args:
            path: (unicode) path to be recursively deleted.
            max_size: (int) optional max size in Bytes a folder can be to qualify for deletion. Default=50000.
        """

        # First we ensure the dir is less than the max_size threshold, otherwise abort.
        if _size_dir(path) < max_size:

            console.debug("Recursively deleting {}".format(path))

            # An emergency safety check in case there's an attempt to delete / (root!) or one of the source_paths.
            if dir == '/' or dir in config.source_dirs:
                raise Exception("Somehow you tried to delete '{}' by calling delete.dir_recursive()... Don't do that!".format(path))

            # Otherwise, only perform destructive actions if we're running in live mode.
            elif not config.test:
                try:
                    shutil.rmtree(path)

                # Catch resource busy error
                except OSError as e:
                    if e.args[0] == 16:
                        console.error('Tried to remove {} but file is in use'.format(path))
        else:
            console.debug("Will not delete {} because it is not empty".format(path))

    #
    @classmethod
    def delete_unwanted_files(cls, path, count=0):
        """Delete all unwanted files in the specified dir.

        Using recursion, delete all invalid (unwanted) files and folders in the specified dir,
        keeping track of the number of files that were deleted.
        This could be dangerous, be careful not to accidentally run it on something like... /

        Args:
            path: (unicode) root path where contents will be deleted.
            count: (int) optional current number of deleted files (in case this is called multiple times
        Returns:
            Number of files that were deleted successfully.
        """

        # Only delete unwanted files if enabled in config
        if config.remove_unwanted_files:
            # Search for invalid files, enumerate them, and delete them.
            for f in [f for f in cls.get_invalid_files(path) if os.path.isfile(f)]:
                # Increment count if deletion was successful
                count += fileops.delete(f)
        return count

    @classmethod
    def count_files_deep(cls, path):
        """Deeply count the number of files in the specified dir.

        Recursively count the number of files inside the specified dir.

        Args:
            path: (unicode) path to be recursively searched
        Returns:
            Number of files, recursively, that exist in the specified dir.
        """
        if os.path.exists(path) and os.path.isdir(path):
            # If it's a directory, we count the files inside, deeply
            return len(cls.find_deep(path))
        else:
            # If it's not a dir or doesn't exist, return False
            return False

class fileops:
    """File-related class method operations.
    """
    @classmethod
    def has_valid_ext(cls, path):
        """Check if file has a valid extension.

        Check the specified file's extension against config.video_exts and config.extra_exts.

        Args:
            path: (unicode) path of file to check.
        Returns:
            True if the file has a valid extension, else False.
        """
        return any([path.endswith(ext) for ext in config.video_exts + config.extra_exts])

    @classmethod
    def safe_move(cls, src, dst):
        """Performs a 'safe' move operation.

        Performs some additional checks before moving files. Optionally supports
        config.safe_copy, which forcibly copies files from one folder to the next
        instead of moving them, even if the files exist on the same partition.
        TODO: Add in copy/move verification (filesize matches)
        TODO: delete original source file after copying.
        TODO: catch IOError

        Args:
            src: (unicode) path of file to move.
            dst: (unicode) destination for file to move to.
        Returns:
            True if the file move was successful, else False.
        """

        # Silently abort if the src and dst are the same.
        if src == dst:
            return

        console.debug("\nWill move '{}'".format(src))
        console.debug("       To '{}'\n".format(dst))

        # Check if a file already exists with the same name as the one we're moving.
        # By default, abort here (otherwise shutil.move would silently overwrite it)
        # and print a warning to the console. If check_for_duplicates is disabled AND
        # overwrite_duplicates is enabled, proceed anyway, otherwise forcibly prevent
        # app from accidentally overwriting files.
        if os.path.exists(dst):
            if config.check_for_duplicates is True or config.overwrite_duplicates is False:
                console.warn('Unable to move {} (identical file already exists)'.format(dst))
                return
            else:
                # Duplicate checking was disabled and overwrite was enabled, so warn,
                # and proceed.
                console.warn('Overwriting existing file {}')

        # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
        # Credit: https://stackoverflow.com/a/34504896/1214800
        if sys.platform == 'darwin':
            dst = os.path.join(os.path.dirname(dst), os.path.basename(dst).replace(r'/', ':'))

        # Only perform destructive changes if running in live mode.
        if not config.test:
            try:
                # If safe_copy is enabled, copy instead of move.
                # Files will always be copied even if they're on a different partition, but this behavior can be
                # forced by enabling safe_copy in config.
                if config.safe_copy: shutil.copy(src, dst)

                # Otherwise, move the file instead.
                else: shutil.move(src, dst)
                return True
            except IOError:

                # Catch exception and soft warn in the console (don't raise Exception).
                console.warn('Failed to move {} to {}'.format(src, dst))
                return False

    @classmethod
    def rename(cls, src, new_filename):
        """Renames a file using shutil.move.

        Renames a file using shutil.move, which under the hood, intelligently determines
        whether or not to use os.rename or shutil.copy. Normally this wouldn't matter, but
        this allows the function to be flexible enough to support srt/dst being on
        different partitions.

        Args:
            src: (unicode) full path (including filename) of file to move.
            new_filename: (unicode) new filename (not including path).
        """

        # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
        # Credit: https://stackoverflow.com/a/34504896/1214800
        if sys.platform == 'darwin':
            new_filename = new_filename.replace(r'/', ':')

        # Generate a destination string based on src's path and the new filename
        dst = os.path.normpath(os.path.join(os.path.dirname(src), new_filename))

        console.interesting('⌥', os.path.basename(dst).replace(r':', '/'))

        # Silently abort if the src==dst (we don't need to waste cycles renaming files
        # that are already correctly named). This also allows us to check for identically
        # named files that may already exist, in order to not overwrite them.
        if src == dst:
            return

        # Check if a file already exists (case sensitive) with the same name as the
        # one we're renaming. If it does, abort (otherwise shutil.move would
        # silently overwrite it) and print a warning to the console.
        if os.path.exists(dst) and os.path.basename(src) == os.path.basename(dst):
            console.warn('Unable to rename {} (identical file already exists)'.format(dst))
            return

        # Only perform destructive changes if we're in live mode.
        if not config.test:

            # Rename the file using shutil.move (instead of os.rename). (os.rename won't work if the
            # src/dst are on different partitions, so we use shutil.move instead). There is also
            # some funky (untested) Windows-related stuff that makes .move the obvious choice.
            shutil.move(src, dst)

    @classmethod
    def contains_ignored_strings(cls, path):
        """Determines of a file contains any of the ignored substrings (e.g. 'sample').

        Checks a path string and determines if it contains any of the forbidden substrins.
        A word of caution: if you add anything common to the config, you may prevent some
        files from being moved.

        Args:
            path: (unicode) full path (including filename) of file to check for ignored strings.
        Returns:
            True if any of the ignored strings are found in the file path, else False.
        """
        return any(word.lower() in path.lower() for word in config.ignore_strings)

    @classmethod
    def delete(cls, file):
        """Deletes a file.

        Attempts to delete the specified file, and returns a number that can be used to
        increment a counter if the deletion was successful.

        Args:
            file: (unicode) full path (including filename) of file to check for ignored strings.
        """
        console.debug("Deleting file {}".format(file))

        # Only perform destructive changes if running in live mode.
        if not config.test:
            try:
                # Try to remove the file
                os.remove(file)
                # If successful, return 1, for a successful op.
                return 1
            except Exception:
                # Handle any exceptions gracefully and warn the console.
                console.warn('Unable to remove {}'.format(file))
                # Return 0 because we don't want a success counter to increment.
                return 0

        # If we're running in test mode, return a mock success (we assume the deletion
        # would have been successful had it actually run).
        else: return 1

def size(path, mock_bytes=None):
    """Determine the size of a file or dir.

    Determine the size of a file or dir at the specified path. Also supports passing
    a 'mock_bytes' artifact for testing.

    Args:
        path: (unicode) file or folder to determine size.
    Returns:
        Size of file or folder, in bytes (B), or None if path does not exist.
    """

    # If the mock_bytes param is set, return it.
    # This is used only for testing.
    if mock_bytes:
        return mock_bytes

    # First check that the path actually exists before we try to determine its size.
    elif os.path.exists(path):

        # If it's a directory, we need to call the _size_dir func to recursively get
        # the size of each file inside.
        if os.path.isdir(path):
            return _size_dir(path)

        # If it's a file, we simply call getsize().
        else:
            return os.path.getsize(path)

    # If the path doesn't exist, we return None
    else:
        return None

def _size_dir(path):
    """Determine the total size of a directory.

    Determine the size of directory at the specified path by recursively calculating
    the size of each file contained within.

    Args:
        path: (unicode) folder to determine size.
    Returns:
        Combined size of folder, in bytes (B), or None if dir does not exist.
    """
    if not os.path.exists(path):
        return None

    # Start with a dir size of 0 bytes
    dir_size = 0

    # Call os.walk() to get all files, recursively in the dir, then add up the file
    # size for each file.
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            dir_size += (os.path.getsize(fp) if os.path.isfile(fp) else 0)

    # Return the total calculated size of the directory.
    return dir_size