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

"""File/directory and size utilities for Fylm operations

A collection of class methods that handles file system CRUD operations, like
get, move, rename, and delete. Also includes filesize detector methods.

    dirops: directory operations exported by this module.
    fileops: file operations exported by this module.
    size: file and dir size calculator
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
import shutil
import sys
import unicodedata
import itertools
from itertools import islice
from multiprocessing import Pool

import fylmlib.config as config
from fylmlib.console import console
from fylmlib.cursor import cursor
import fylmlib.formatter as formatter

class dirops:
    """Directory-related class method operations.
    """

    _existing_films = None

    @classmethod
    def verify_root_paths_exist(cls, paths):
        """Verifies that the specified paths (array) exist.

        Loops through an array of paths to check that each one exists. If any do not,
        raise an Exception. Primarily used at app initiation time to verify that source
        and destination paths are in working order.

        Args:
            paths: (list) paths to verify existence.
        """
        for d in (d for d in paths if not os.path.exists(d)):
            console.error(f"'{d}' does not exist; check source path in config.yaml")

    @classmethod
    def is_same_partition(cls, f1, f2):
        """Determine if f1 and f2 are on the same partition.

        Args:
            f1: (str, utf-8) path of source file/folder
            f2: (str, utf-8) path of destination file/folder
        Returns:
            True, if f1 and f2 are on the same parition, or force_move is True, else False.
        """

        if config.force_move is True:
            return True

        while not os.path.exists(f1):
            f1 = os.path.dirname(f1)

        while not os.path.exists(f2):
            f2 = os.path.dirname(f2)

        return os.stat(os.path.dirname(f1)).st_dev == os.stat(os.path.dirname(f2)).st_dev

    @classmethod
    def get_existing_films(cls, paths):
        """Get a list of existing films.

        Scan one level deep of the target paths to get a list of existing films. Since
        this is used exclusively for duplicate checking, this method is skipped when
        duplicate checking is disabled.

        Args:
            paths: (dict) a set of unicode paths to search for existing films.
                   Must be passed in the form of: { "<quality>": "<path>" }
        Returns:
            A list of existing Film objects.
        """

        # If existing films has already been loaded and the list has
        # more than one film:
        if cls._existing_films is not None and len(cls._existing_films) > 0:
            return cls._existing_films

        # Import Film here to avoid circular import conflicts.
        from fylmlib.film import Film

        # If check_for_duplicates is disabled, we don't care about duplicates, and
        # don't need to spend cycles processing duplicates. Return an empty array.
        if config.duplicate_checking.enabled is False:
            return []

        # Fix paths being a str
        if isinstance(paths, str):
            paths = { 'default': paths }

        # Enumerate the destination directory and check for duplicates.
        console.debug('Loading existing films from disk...')

        cls._existing_films = []

        # Map a list of valid and sanitized files to Film objects by iterating
        # over paths for 720p, 1080p, 4K, and SD qualities.
        for path in list(set(os.path.normpath(path) for _, path in paths.items())):
            if os.path.normpath(path) not in config.source_dirs:
                xfs = [os.path.normpath(os.path.join(path, file)) for file in cls.sanitize_dir_list(os.listdir(path))]
                with Pool(processes=25) as pool:                    
                    cls._existing_films += pool.map(Film, xfs)

        # Strip bad duplicates
        cls._existing_films = list(filter(lambda x: x.should_ignore is False, cls._existing_films))

        files_count = list(itertools.chain(*[f.video_files for f in cls._existing_films]))
        console.debug(f'Loaded {len(cls._existing_films)} existing unique Film objects containing {len(files_count)} video files')

        # Uncomment for verbose debugging. This can get quite long.
        # for f in sorted(cls._existing_films, key=lambda s: s.title.lower()):
        #     console.debug(f' - {f.source_path} {f.all_valid_films}')
        
        # Sort the existing films alphabetically, case-insensitive, and return.
        return sorted(cls._existing_films, key=lambda s: s.title.lower())

    @classmethod
    def get_new_films(cls, paths):
        """Get a list of new potenial films we want to tidy up.

        Scan one level deep of the target path to get a list of potential new files/folders.

        Args:
            paths: (Array[str, utf-8]) paths to search for new films.
        Returns:
            An array of potential films.
        """

        # Import Film here to avoid circular import conflicts.
        from fylmlib.film import Film

        films = []

        for path in paths:
            # Enumerate the search path(s) for files/subfolders, sanitize them, then finally sort
            # the resulting list of files alphabetically, case-insensitive.
            sorted_files = sorted(cls.sanitize_dir_list(os.listdir(path)), key=lambda s: s.lower())

            # If using the `limit` option, create a sliced list to limit the number of
            # files to be processed.
            limited_files = islice(sorted_files, config.limit if config.limit > 0 else None)

            # Map the sorted/filtered list to Film objects.
            films.append(list(map(Film, [os.path.join(path, file) for file in limited_files])))

        return sum(films, [])

    @classmethod
    def get_valid_files(cls, path) -> [str]:
        """Get a list valid files inside the specified path.

        Scan deeply in the specified path to get a list of valid files, as
        determined by the config.video_exts and config.extra_exts properties.

        Args:
            path: (str, utf-8) path to search for valid files.
        Returns:
            An array of valid file paths.
        """

        # Call dirops.find_deep to search for files within the specified path.
        # Filter the results using a lambda function.
        valid_files = cls.find_deep(path, lambda x:

            # A valid file must have a valid extension
            fileops.has_valid_ext(x)

            # It must not contain an ignored string (e.g. 'sample')
            and not fileops.contains_ignored_strings(x)

            # And it must be at least a certain filesize if it is a film,
            # or not 0 bytes if it's a supplementary file.
            and fileops.is_acceptable_size(x))

        # If debugging, print the resulting list of files and sizes.
        # This is a very noisy output, so is commented out.

        # if config.debug is True:
        #     import inspect
            # for f in list(set(valid_files)):
            #     console.debug(f'\n`{inspect.stack()[0][3]}`' \
            #                   f' found "{os.path.basename(f)}"' \
            #                   f' ({formatter.pretty_size(size(f))})' \
            #                   f' \nin {path}')

        return sorted(valid_files, key=os.path.getsize, reverse=True)


    @classmethod
    def get_invalid_files(cls, path):
        """Get a list of invalid files inside the specified dir.

        Scan deeply in the specified dir to get a list of invalid files, as
        determined by the config.video_exts and config.extra_exts properties.
        We do not check filesize here, because while we may not want to
        rename and move vide/extra files that are too small, we probably
        don't want to delete them.

        Args:
            path: (str, utf-8) path to search for invalid files.
        Returns:
            An array of invalid files.
        """

        # Call dir.find_deep to search for files within the specified dir.
        # Filter the results using a lambda function.
        return cls.find_deep(path, lambda x:

            # An invalid file might contain an ignored string (e.g. 'sample')
            fileops.contains_ignored_strings(x)

            # Or it may not have a valid file extension
            or not fileops.has_valid_ext(x)

            # Or if it does, it might not be large enough
            or not fileops.is_acceptable_size(x))

    @classmethod
    def sanitize_dir_list(cls, files):
        """Sanitize a directory listing using unicode normalization and by
        omitting system files.

        On macOS, unicode normalization must take place for loading files with
        unicode chars. This method correctly normalizes these strings.
        It also will remove .DS_Store and Thumbs.db from the list, since we
        don't ever care to count, or otherwise observe, these system files.

        Args:
            files: (str, utf-8) list of files in dir.
        Returns:
            A sanitized, unicode-ready array of files.
        """
        return list(filter(lambda f: 
            not any([f.lower() in map(lambda x: x.lower(), config.ignore_strings)])
            and not f.endswith('.DS_Store') and not f.endswith('Thumbs.db'),
            [unicodedata.normalize('NFC', file) for file in files]))
        
    @classmethod
    def create_deep(cls, path):
        """Deeply create the specified path and any required parent paths.

        Using recursion, create a directory tree as specified in the path
        param.

        Args:
            path: (str, utf-8) path to create.
        """

        # Because this is a destructive action, we will not create the
        # path tree if running in test mode.
        if not config.test:

            # If the path exists, there's no point in trying to create it.
            if not os.path.exists(path):
                try:
                    console.debug(f'Creating destination {path}')
                    os.makedirs(path)
                # If the dir creation fails, raise an Exception.
                except OSError as e:
                    console.error(f'Unable to create {path}', OSError)

    @classmethod
    def find_deep(cls, root_dir, func=None):
        """Deeply search the specified dir and return all files.

        Using recursion, search the specified path for files.
        Pass an optional function to filter results.

        Args:
            root_path: (str, utf-8) path to search for files.
            func: (function) user-defined or lambda function to use as a filter.
        Returns:
            A filtered list of files.
        """

        # Use os.walk() to recursively search the dir and return full path of each file.
        results = [os.path.join(root, f) for root, dirs, files in os.walk(root_dir) for f in files]

        # Sanitize the resulting file list, then call the (optional) filter function that was passed.
        return list(filter(func, cls.sanitize_dir_list(results)))

    @classmethod
    def delete_dir_and_contents(cls, path, max_size=50*1024):
        """Recursively delete dir path and all its contents, if less than max_size.

        Using recursion, delete all files and folders in the specified dir and
        itself if the total dir size is less than max_size (default 50 KB).

        Args:
            path: (str, utf-8) path to be recursively deleted.
            max_size: (int) optional max size in Bytes a folder can be to qualify for deletion. Default=50000.
        """

        # Get count of files
        files_count = len(cls.find_deep(path))

        # First we ensure the dir is less than the max_size threshold, otherwise abort.
        if _size_dir(path) < max_size or max_size == -1 or files_count == 0:

            console.debug(f'Recursively deleting {path}')

            # An emergency safety check in case there's an attempt to delete / (root!) or one of the source_paths.
            if dir == '/' or dir in config.source_dirs:
                raise OSError(f"Somehow you tried to delete '{path}' by calling delete.dir_recursive()... Don't do that!")

            # Otherwise, only perform destructive actions if we're running in live mode.
            elif config.test is False:
                try:
                    shutil.rmtree(path)

                # Catch resource busy error
                except OSError as e:
                    if e.args[0] == 16:
                        console.error(f'Tried to remove "{path}" but file is in use')
        elif config.test is False:
            console().red().indent(
                f"Will not delete {path} ({'not empty' if files_count > 0 else formatter.pretty_size(max_size)})"
            )

    @classmethod
    def delete_unwanted_files(cls, path):
        """Delete all unwanted files in the specified dir.

        Using recursion, delete all invalid (unwanted) files and folders in the specified dir,
        keeping track of the number of files that were deleted.
        This could be dangerous, be careful not to accidentally run it on something like... /

        Args:
            path: (str, utf-8) root path where contents will be deleted.
            count: (int) optional current number of deleted files (in case this is called multiple times
        Returns:
            Number of files that were deleted successfully.
        """

        deleted_files = 0

        # Only perform destructive actions if in live mode.
        if not config.test:
            # Only delete unwanted files if enabled in config
            if config.remove_unwanted_files:
                # Search for invalid files, enumerate them, and delete them.
                for f in [f for f in cls.get_invalid_files(path) if os.path.isfile(f)]:
                    # Increment deleted_files if deletion was successful.
                    # `fileops.delete` has test check built in, so
                    # no need to check here.
                    deleted_files += fileops.delete(f)
        return deleted_files

class fileops:
    """File-related class method operations.
    """
    @classmethod
    def has_valid_ext(cls, path):
        """Check if file has a valid extension.

        Check the specified file's extension against config.video_exts and config.extra_exts.

        Args:
            path: (str, utf-8) path of file to check.
        Returns:
            True if the file has a valid extension, else False.
        """
        return any([path.endswith(ext) for ext in config.video_exts + config.extra_exts])

    @classmethod
    def is_acceptable_size(cls, file_path):
        """Determine if a file_path is an acceptable size.

        Args:
            file: (str, utf-8) path to file.
        Returns:
            True, if the file is an acceptable size, else False.
        """
        s = size(file_path)
        min = cls.min_filesize_for_resolution(file_path)
        is_video = any([file_path.endswith(ext) for ext in config.video_exts])
        is_extra = any([file_path.endswith(ext) for ext in config.extra_exts])

        return ((s >= min * 1024 * 1024 and is_video)
                or (s >= 0 and is_extra))

    @classmethod
    def min_filesize_for_resolution(cls, file_path):
        """Determine the minimum filesize for the resolution for file path.

        Args:
            file: (str, utf-8) path to file.
        Returns:
            int: The minimum file size, or default if resolution could not be determined
        """
        min = config.min_filesize
        if isinstance(min, int):
            return min

        # If the min filesize is not an int, we assume
        # that it is an AttrMap of resolutions.
        from fylmlib.parser import parser
        res = parser.get_resolution(file_path)
        if res is None:
            return min.default
        if res == '720p' or res == '1080p' or res == '2160p':
            return min[res]
        elif res.lower() == 'sd' or res.lower() == 'sdtv':
            return min.SD
        else:
            return min.default

    @classmethod
    def safe_move(cls, src: str, dst: str):
        """Performs a 'safe' move operation.

        Performs some additional checks before moving files. Optionally supports
        config.safe_copy, which forcibly copies files from one folder to the next
        instead of moving them, even if the files exist on the same partition.
        
        Args:
            src: (str, utf-8) path of file to move.
            dst: (str, utf-8) destination for file to move to.

        Returns:
            True if the file move was successful, else False.
        """

        # Abort if src does not exist in live mode. We can't raise this error in 
        # test mode, because the file would never have been renamed.
        if not os.path.exists(src) and config.test is False:
            raise OSError(f'Path does not exist: {src}')

        # Silently abort if the src and dst are the same.
        if src == dst:
            console.debug('Source and destination are the same, nothing to move')
            return False

        # Try to create destination folders if they do not exist.
        dirops.create_deep(os.path.dirname(dst))

        console.debug(f"\n  Moving: '{src}'")
        console.debug(f"      To: '{dst}'\n")

        # Check if a file already exists with the same name as the one we're moving.
        # By default, abort here (otherwise shutil.move would silently overwrite it)
        # and print a warning to the console. If overwrite_existing is enabled, 
        # proceed anyway, otherwise forcibly prevent accidentally overwriting files.
        if os.path.exists(dst):
            # If overwrite_existing is turned off, we can't overwrite this file.
            if config.overwrite_existing is False and config.interactive is False:
                # If we're not overwriting, return false
                console().red().indent(f'Unable to move; a file with the same name already exists ({dst})').print()
                return False
                
            # File overwriting is enabled and not marked to replace, so warn, 
            # and proceed continue.
            console().yellow().indent(f'Replacing existing file ({dst})').print()

        # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
        # Credit: https://stackoverflow.com/a/34504896/1214800
        if sys.platform == 'darwin':
            dst = os.path.join(os.path.dirname(dst), os.path.basename(dst).replace(r'/', '-'))

        # Only perform destructive changes if running in live mode, so we can short-circuit
        # the rest by returning True here and presuming it was successful.
        if config.test is True:
            return True

        try:

            # If we're overwriting, first try and rename the existing (identical) 
            # duplicate so we don't lose it if the move fails
            if os.path.exists(dst):
                os.rename(dst, f'{dst}.dup')

            # If safe_copy is enabled, or if partition is not the same, copy instead.
            if config.safe_copy is True or not dirops.is_same_partition(src, dst): 

                # Store the size of the source file to verify the copy was successful.
                expected_size = size(src)
                
                # Generate a new filename using .partial~ to indicate the file
                # has not be completely copied.
                partial_dst = f'{dst}.partial~'

                # Copy the file using progress bar
                cls.copy_with_progress(src, partial_dst)

                # Verify that the file is within one byte of the original.
                dst_size = size(partial_dst)
                if abs(dst_size - expected_size) <= 1:
                    os.rename(partial_dst, partial_dst.rsplit('.partial~', 1)[0])
                    os.remove(src)

                # If not, then we print an error and return False.
                else:
                    console().red().indent(f"Size mismatch: file is {dst_size:,} bytes, expected {expected_size:,} bytes")
                    return False
            
            # Otherwise, move the file instead.
            else: 
                shutil.move(src, dst)

            # Clean up any backup duplicate that might have been created, if the move was successful
            if os.path.exists(dst) and os.path.exists(f'{dst}.dup'):
                os.remove(f'{dst}.dup')

            return True

        except (IOError, OSError) as e:

            # Catch exception and soft warn in the console (don't raise Exception).
            console().red().indent(f'Failed to move {src} to {dst}')
            console.debug(e)
            print(e)

            # If we're overwriting and a duplicate was created, undo its renaming
            if os.path.exists(f'{dst}.dup'):
                os.rename(f'{dst}.dup', dst)

            return False

    @classmethod
    def copy_with_progress(cls, src, dst, follow_symlinks=True):
        """Copy data from src to dst and print a progress bar.

        If follow_symlinks is not set and src is a symbolic link, a new
        symlink will be created instead of copying the file it points to.

        Args:
            src: (str, utf-8) path to source file.
            dst: (str, utf-8) path to destionation.
            follow_symlinks: (bool) follows symbolic links to files and re-creates them.

        """

        # Hide the cursor
        cursor.hide()

        # If the destination is a folder, include the folder
        # in the destination copy.
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        # If the source and destination are the same, abort.
        if shutil._samefile(src, dst):
            return

        for fn in [src, dst]:
            try:
                st = os.stat(fn)
            except OSError:
                # File most likely does not exist.
                pass
            else:
                if shutil.stat.S_ISFIFO(st.st_mode):
                    raise shutil.SpecialFileError(f"`{fn}` is a named pipe")

        # Handle symlinks.
        if not follow_symlinks and os.path.islink(src):
            os.symlink(os.readlink(src), dst)
        else:
            size = os.stat(src).st_size
            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    cls._copyfileobj(fsrc, fdst, callback=console().print_copy_progress_bar, total=size)
        
        # Perform a low-level copy.
        shutil.copymode(src, dst)

        # Show the cursor.
        cursor.show()

        # Clear the progress bar from the console.
        console.clearline()

    @classmethod
    def _copyfileobj(cls, fsrc, fdst, callback, total, length=16*1024):
        """Internal method for low-level copying.

        Executes low-level file system copy and calls back progress
        to progress bar function.

        Args:
            fsrc: (str, utf-8) path to source file.
            fdst: (str, utf-8) path to destionation.
            callback: (function) callback function to be called when progress is changed.
            total: (int) total expected size of file in B.
            length: (int) total length of buffer.

        """
        copied = 0
        while True:
            buf = fsrc.read(length)
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            callback(copied, total=total)

    @classmethod
    def rename(cls, src, new_filename_and_ext):
        """Renames a file using shutil.move.

        Renames a file using shutil.move, which under the hood, intelligently determines
        whether or not to use os.rename or shutil.copy. Normally this wouldn't matter, but
        this allows the function to be flexible enough to support srt/dst being on
        different partitions.

        Args:
            src: (str, utf-8) full path (including filename) of file to move.
            new_filename_and_ext: (str, utf-8) new filename.ext (not including path).
        """

        # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
        # If we don't do this, the filesystem will try and create a new folder instead
        # of the correct filename.
        # Credit: https://stackoverflow.com/a/34504896/1214800
        new_filename_and_ext = new_filename_and_ext.replace(r'/', '-')

        # Generate a destination string based on src's path and the new filename
        dst = os.path.normpath(os.path.join(os.path.dirname(src), new_filename_and_ext))

        # Silently abort if the src==dst (we don't need to waste cycles renaming files
        # that are already correctly named). This also allows us to check for identically
        # named files that may already exist, in order to not overwrite them.
        if src == dst:
            return

        # Check if a file already exists (case sensitive) with the same name as the
        # one we're renaming. If it does, abort (otherwise shutil.move would
        # silently overwrite it) and print a warning to the console.
        if os.path.exists(dst) and os.path.basename(src) == os.path.basename(dst):
            console().red().indent(f'Unable to rename {dst} (identical file already exists)')
            return

        console.debug(f'Renaming: {src}')
        console.debug(f'      To: {dst}')

        # Only perform destructive changes if we're in live mode.
        if not config.test:

            # Rename the file using shutil.move (instead of os.rename). (os.rename won't work if the
            # src/dst are on different partitions, so we use shutil.move instead). There is also
            # some funky (untested) Windows-related stuff that makes .move the obvious choice.
            os.rename(src, dst)

    @classmethod
    def contains_ignored_strings(cls, path):
        """Determines of a file contains any of the ignored substrings (e.g. 'sample').

        Checks a path string and determines if it contains any of the forbidden substrins.
        A word of caution: if you add anything common to the config, you may prevent some
        files from being moved.

        Args:
            path: (str, utf-8) full path (including filename) of file to check for ignored strings.
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
            file: (str, utf-8) full path (including filename) of file to check for ignored strings.
        """
        console.debug(f"Deleting file {file}")

        # If we're running in test mode, return a mock success (we assume the deletion
        # would have been successful had it actually run).
        if config.test:
            return 1
        # Only perform destructive changes if running in live mode.
        try:
            # Try to remove the file
            os.remove(file)
            # If successful, return 1, for a successful op.
            return 1
        except Exception:
            # Handle any exceptions gracefully and warn the console.
            console().red().indent(f'Unable to remove {file}')
            # Return 0 because we don't want a success counter to increment.
            return 0

def largest_video(path):
    """Determine the largest video file in dir.

    Args:
        path: (str, utf-8) file or folder to determine size of video file.
    Returns:
        Path of largest video file, or None if path does not exist.
    """

    # First check that the path actually exists before we try to determine its size.
    if os.path.exists(path):

        # If it's a directory, we need to find the largest video file, recursively.
        if os.path.isdir(path):
            
            try:
                video_files = list(filter(lambda f: os.path.splitext(f)[1] in config.video_exts, dirops.get_valid_files(path)))

                # Re-populate list with (filename, size) tuples
                for i, file in enumerate(video_files):
                    video_files[i] = (file, os.path.getsize(file))

                # Sort list by file size from largest to smallest and return the first file.
                video_files.sort(key=lambda v: v[1], reverse=True)

                # Return path (first value -- second value is size) of first file in sorted array.
                return video_files[0][0]

            # If an out of range error is encountered, something went wrong and the file
            # probably doesn't exist.
            except IndexError:
                return None

        # If it's a file, return the path.
        else:
            return path

    # If the path doesn't exist, we return None
    else:
        return None

def size(path) -> int:
    """Determine the size of a file or dir.

    Args:
        path: (str, utf-8) file or folder to determine size.
    Returns:
        Size of file or folder, in bytes (B), or None if path does not exist.
    """

    # First check that the path actually exists before we try to determine its size.
    if path is not None:
        if not os.path.exists(path):
            raise Exception(f'Cannot calculate size for a path that does not exist ({path})')

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
        path: (str, utf-8) folder to determine size.
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
