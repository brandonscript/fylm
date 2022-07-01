#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

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

"""File/directory and size utilities for Fylm operations

A collection of class methods that handles file system CRUD operations, like
get, move, rename, and delete. Also includes filesize detector methods.

    dirops: directory operations exported by this module.
    fileops: file operations exported by this module.
    size: file and dir size calculator
"""

import os
import shutil
import sys
import re
import itertools
import time
import asyncio
import multiprocessing
from pathlib import Path
from typing import List, Union, Iterable

import fylmlib.config as config
import fylmlib.patterns as patterns
from .tools import *
from .enums import *
from .console import Tinta
from . import FilmPath
from . import Console
from . import Cursor
from . import Format

class Create:
    """Utilities for making files/dirs on the filesystem."""

    @staticmethod
    def dirs(*paths: Union[str, Path, 'FilmPath']):
        """Deeply create the specified path and any required parent paths.

        Using recursion, create a directory tree as specified in the path
        param.

        Args:
            path (str, Path, or FilmPath) path to create.
        """

        # Because this is a destructive action, we will not create the
        # path tree if running in test mode.
        if not config.test:

            # If the path exists, there's no point in trying to create it.
            try:
                for path in paths:
                    Console.debug(f"Creating dir '{path}'")
                    Path(path).mkdir(parents=True, exist_ok=True)
            # If the dir creation fails, raise an Exception.
            except OSError as e:
                Console.error(f"Unable to create '{path}'", e)

class Delete:
    """Utilities for deleting files/dirs on the filesystem."""

    @staticmethod
    def dir(path=Union[str, Path, 'FilmPath'],
            max_size: int = 50*1024, force: bool = False) -> bool:
        """Recursively delete dir path and all its contents, if the total dir
        size is less than max_size (default 50 KB).

        Args:
            path (str, Path, or FilmPath): Path to be recursively deleted.
            max_size (int, optional): Max size in Bytes a folder can be to
                                      allow for deletion. Default=50000.
            force (bool): Force deletion by setting max_size to -1

        Bool:
            Return True if the delete operation was successful.

        """

        if not path.is_dir():
            return 0

        path = Path(path)
        # Check to make sure path isn't a source dir
        if str(path).lower() in [
                str(x).lower() for x in set(
                    config.source_dirs + list(config.destination_dirs.values()))]:
            raise OSError(
                f"Unwilling to delete '{path}', it is a source or destination dir.")

        if max_size == -1:
            force = True

        # Get count of files
        files_count = len([f.is_file() for f in Find.deep(path)])

        # First we ensure the dir is less than the max_size threshold, or empty,
        # otherwise abort. If max_size is -1 or force is enabled, do it anyway.
        if files_count == 0 or force or Size(path).value < max_size:

            Console.debug(f"Recursively deleting '{path}' which contains {files_count} file(s).")

            # Only perform destructive actions if we're running in live mode.
            if config.test:
                return True
            try:
                shutil.rmtree(path)
                return True
            # Catch resource busy error
            except OSError as e:
                if e.args[0] == 16:
                    Console.error(
                        f"{INDENT}Failed to remove '{path}', it is in use.")
        else:
            Console.error(
                f"{INDENT}Will not delete '{path}' ({'not empty' if files_count > 0 else Size.pretty(max_size)})"
            )
        return False

    @staticmethod
    def files(
            *paths: Union[str, Path, 'FilmPath'],
            count: int = 0,
            ignore_exts: List[str] = None,
            max_filesize: Union[int, None] = 0) -> int:
        """Delete all files in the specified paths list or generator

        Count helps keep track of the number of files that were deleted, for reporting
        and recursion.

        Args:
            path (list or Iterable of str, Path, or FilmPath): Path to search for files to delete.
            count (int, optional): Current number of deleted files, for external tracking.
            ignore_exts (list, optional): List of file extensions to exclude from deletion.
            max_filesize (int, optional): Max file size in bytes to allow for deletion. Files larger 
                         than this will not be deleted. If both ignore_exts and max_filesize are set, 
                         files with extensions in ignore_exts will still be deleted if they are smaller 
                         than max_filesize.

        Returns:
            int: Number of files that were deleted successfully.
        """
        
        deleted_files = count

        for f in paths:
            if not isinstance(f, FilmPath):
                f = FilmPath(f)
            if f.is_file():
                # If it is an ignored extension, skip it unless it is smaller than max_filesize.
                # If there are no ignored extensions, skip it unless it is smaller than 
                # max_filesize irrespective of extension.
                if not ignore_exts or f.suffix in ignore_exts:
                    if max_filesize is not None and f.size.value > max_filesize:
                        continue
                
            if not config.test:
                deleted_files += Delete.file(f)
            else:
                deleted_files += 1

        return deleted_files

    @staticmethod
    def file(path: Union[str, Path, 'FilmPath']) -> int:
        """Attempts to delete the specified file, and returns a number that can be used to
        increment a counter if the deletion was successful.

        Args:
            path (str, Path, or FilmPath): Path of file to delete.

        Returns:
            int: 1 if the file was deleted successfully, or 0.
        """

        Console.debug(f"Deleting file '{path}'")

        try:
            p = Path(path)
            if not p.exists():
                Console.error(f"{INDENT}Could not delete '{p}'; it does not exist.")
            else:
                if not config.test:
                    p.unlink()
                # If successful, return 1 for a successful op.
                return 1
        except Exception as e:
            Console.error(f"{INDENT}Unable to remove '{path}': {e}")

        # Default return 0
        return 0

    @staticmethod
    def path(path: Union[str, Path, 'FilmPath'], force: bool = False) -> bool:
        """Attempts to delete the specified path (file or dir)
        and fails gracefully if it does not.

        Args:
            path (str, Path, or FilmPath): Path to delete
            force (bool): Forces the path to be deleted even if it is above
                          size safety threshold.

        Returns:
            bool: True if the path exists and was deleted successfully.
        """

        Console.debug(f"Deleting path '{path}'")

        try:
            p = Path(path)
            if p.is_file():
                return bool(Delete.file(path))
            elif p.is_dir():
                return bool(Delete.dir(path, force=force))
        except Exception as e:
            Console.error(f"{INDENT}Unable to remove '{path}': {e}")
        return False

    @staticmethod
    def paths(*paths: Union[str, Path, 'FilmPath'], force=False) -> int:
        """Passthrough to Delete.path to delete multiple paths.

        Args:
            paths (str, Path, or FilmPath): Paths to delete
            force (bool): Forces the paths to be deleted even if they are above
                          size safety threshold.

        Returns:
            int: Number of paths deleted
        """
        return sum(int(Delete.path(p, force=force)) for p in paths)

class Find:
    """A collection of methods to search for files and dirs."""

    NEW = None # Cached list from Find.new()
    EXISTING = None # Cached list from Find.existing()

    @staticmethod
    def deep(path: Union[str, Path, 'FilmPath'],
             hide_sys_files=True) -> Iterable['FilmPath']:
        """Deeply search the specified path and return all files and dirs
        (using os.walk), mapped to FilmPath objects that maintain a
        hierarchical matrix of pathlib.Path objects. Note: the original
        path root will always be included in this list. If sorting
        alphabetically, use [1:] to remove the first element (root).
        If path provided is a single file, return a list with it.

        Args:
            path (str or Path): Root path to search for files.
            hide_sys_files (bool): Hide system files. Default is True.

        Returns:
            A filtered list of files or an empty list.
        """

        origin = FilmPath(path)
        if not origin.is_dir():
            raise NotADirectoryError(
                f"Cannot use Find.deep on '{path}', it is not a dir.")
        else:
            for root,dirs,files in os.walk(path):

                if hide_sys_files:
                    files = filter(lambda f: not is_sys_file(f), files)

                this = FilmPath(root, origin=origin)

                this._dirs = [this.joinpath(d) for d in dirs]
                this._files = [this.joinpath(f) for f in files]

                dirs = this.dirs
                files = this.files

                if not this == origin:
                    yield this
                yield from files or []

    @staticmethod
    def deep_sorted(path: Union[str, Path, 'FilmPath'],
                    sort_key=lambda p: p.name.lower(),
                    hide_sys_files=True) -> Iterable['FilmPath']:
        found = Find.deep(path, hide_sys_files=hide_sys_files)
        if sort_key:
            yield from sorted(found, key=sort_key)
        else:
            yield from found

    @staticmethod
    def deep_files(path: Union[str, Path, 'FilmPath'],
                   sort_key=lambda p: p.name.lower(),
                   hide_sys_files=True) -> Iterable['FilmPath']:
        found = filter(lambda x: x.is_file(),
                       Find.deep(path, hide_sys_files=hide_sys_files))
        if sort_key:
            yield from sorted(found, key=sort_key)
        else:
            yield from found

    @staticmethod
    def shallow(path: Union[str, Path, 'FilmPath'],
                sort_key=lambda p: p.name.lower(),
                hide_sys_files=True) -> Iterable['FilmPath']:
        """Return a list of all files and dirs contained in a path,
        one-level deep, mapped to FilmPath objects. Note: the original
        path root will always be included in this list. If sorting
        alphabetically, use [1:] to remove the first element (root).
        If path provided is a single file, return a list with it.

        Args:
            path (str or Path): Root path to search for files.
            sort_key (lambda, optional): Sort function, defaults
                                         to name alpha case-insensitive.
            hide_sys_files (bool): Hide system files. Default is True.

        Returns:
            A filtered list of files or an empty list.
        """
        origin = FilmPath(path)
        if not origin.is_dir():
            raise NotADirectoryError(
                f"Cannot use Find.shallow, '{path}' is not a dir.")
        else:
            found = origin.iterdir()
            if sort_key:
                found = sorted(found, key=sort_key)
            for p in found:
                if hide_sys_files and is_sys_file(p):
                    continue
                yield FilmPath(p, origin=origin)

    @staticmethod
    def glob(*paths, search: str) -> List['FilmPath']:
        """Takes an input string and searches the filesystem
        for a likely match.

        Args:
            search (str): Search string

        Returns:
            [FilmPath]: List of matching FilmPaths
        """
        Console.debug(f"Searching for glob string '{search}'...")
        Console.debug(f"Searching in paths: {paths}")

        # Make sure we filter out None paths because Path() will throw
        paths = list(filter(lambda p: p is not None, paths))

        paths = list(map(Path, set(paths)))
        globstr = re.sub(patterns.ALL_NONWORD_CHARS, '*', search) + '*'

        # Ensure paths exist
        for p in paths:
            if not p.exists():
                try:
                    Create.dirs(p)
                except Exception as e:
                    raise FileNotFoundError(
                        f"Path '{p}' does not exist. Tried to create it, but could not.")

        found_iter = itertools.chain.from_iterable(
            Path(p).glob(globstr) for p in paths)

        return list(found_iter)


    @classmethod
    def existing(cls,
                 *paths,
                 sort_key=None) -> List['FilmPath']:
        """Get a list of existing films from destination dirs.

        Scan one level deep of the target paths to get a list of existing films.
        # TODO: Took dupe checking ignoring calling this out of this method

        Args:
            paths (str, Path, or FilmPath): Path or paths to search for existing films.
            sort_key (lambda, optional): Sort function, defaults to None

        Returns:
            A list of existing films mapped to FilmPath objects.
        """

        # If existing films has already been loaded and the list has
        # more than one film:
        if cls.EXISTING:
            return cls.EXISTING


        Console.debug('Searching for existing films...')

        paths = cls._map_str_paths_to_path(paths or config.destination_dirs.values())

        # Ensure paths exist
        for p in paths:
            if not p.exists():
                raise FileNotFoundError(
                    f"Path '{p}' does not exist. Check config.destination_dirs.")

        # Shallow scan the target dirs
        found_iter = itertools.chain.from_iterable(
            Find.shallow(p, sort_key=sort_key) for p in paths)

        # Set the class var
        cls.EXISTING = list(found_iter)

        return cls.EXISTING

    @classmethod
    def new(cls,
            *paths,
            sort_key=lambda p: p.name.lower()) -> List['FilmPath']:
        """Get a list of potential new films from source dirs.

        Args:
            Paths (str, Path, or FilmPath): Path or paths to search for new films.
            sort_key (lambda, optional): Sort function, defaults
                                         to name alpha case-insensitive.

        Returns:
            A list of potential new films mapped to FilmPath objects.
        """

        # If new films has already been loaded and the list has
        # more than one film:
        if cls.NEW:
            return cls.NEW

        Console.debug('Loading new films...')

        # Coerce list path objects to Path set
        if paths and isinstance(paths[0], list):
            paths = tuple(paths[0])

        # Coerce str path objects to Path set
        paths = cls._map_str_paths_to_path(paths or config.source_dirs)
        
        # Ensure paths exist
        for p in paths:
            if not p.exists():
                raise FileNotFoundError(
                    f"Path '{p}' does not exist. Check config.source_dirs or your -s flag.")

        # Shallow scan the target dirs, then sync the maybe_film attr.
        found_iter = itertools.chain.from_iterable(
            Find.deep_sorted(p, sort_key=sort_key) for p in paths)
        
        # Set the class var
        cls.NEW = list(found_iter)

        return cls.NEW

    @staticmethod
    def _map_str_paths_to_path(paths: List[Union[str, None]]) -> List[Path]:
        """Coerce a list of str paths to Path objects.

        Args:
            paths (List[Union[str, None]]): List of str paths.

        Returns:
            List[Path]: List of Path objects.
        """
        # Make sure we filter out None paths because Path() will throw
        paths = list(filter(lambda p: p is not None, paths))

        # Coerce str path objects to Path set
        return list(map(Path, set(paths)))


    @staticmethod
    def sync_parallel(paths: Iterable['FilmPath'], attrs: List[str] = None) -> List['FilmPath']:

        from fylmlib import app

        if not app.POOL:
            raise shutil.ExecError("Multiprocessing Pool was not initalized before trying to process files.")

        app.POOL.worker_count = min(
            multiprocessing.cpu_count(), len(list(paths)) or 1)
        yield from app.POOL.starmap(FilmPath.sync, zip(paths, itertools.repeat(attrs)))

class IO:
    """Move, rename, and copy filesystem utils"""

    @staticmethod
    def move(src: Union[str, Path, 'FilmPath'],
             dst: Union[str, Path, 'FilmPath'],
             overwrite=False):
        """Performs a 'safe' move operation, with some additional checks before moving
        files.

        Args:
            src (str, Path, or Filmpath): Path of file to move.
            dst (str, Path, or Filmpath): New path for this file.
            overwrite: (Bool) True if this file is OK to replace an existing one
                                  as determined by checking for identical duplicates
                                  that meet upgrade criteria.

        Returns:
            True if the file move was successful, otherwise False.
        """

        src = src if isinstance(src, FilmPath) else Path(src)
        dst = dst if isinstance(dst, FilmPath) else Path(dst)

        if not src.exists():
            raise OSError(f"Error moving '{src}', path does not exist.")

        # Silently abort if the src and dst are the same.
        if src == dst:
            Console.debug('Source and destination are the same, nothing to move')
            return False

        # Try to create dst's container dirs if they do not exist.
        Create.dirs(dst.parent)

        Console.debug(f"\n  Moving: '{src}'")
        Console.debug(  f"      To: '{dst}'\n")

        # Check if a file already exists with the same name as the one we're moving.
        # By default, abort here (otherwise shutil.move would silently overwrite it)
        # and print a warning to the console. If force_overwrite is enabled,
        # proceed anyway, otherwise forcibly prevent accidentally overwriting files.
        # If we determined it's OK to upgrade the detination, we can skip this.
        if dst.exists() and not overwrite:
            # If force_overwrite is turned off, we can't overwrite this file.
            # If interactive is on, the user has some more flexibility and can choose to
            # overwrite, so we can skip this.
            if config.duplicates.force_overwrite is False and config.interactive is False:
                # If we're not overwriting, return false
                Console.io_reject('move', dst)
                return False

            # File overwriting is enabled and not marked to upgrade, so warn but continue
            Tinta().yellow(
                f"{INDENT}Replacing existing file '{dst.parent}'").print()

        # Only perform destructive changes if running in live mode, so we can short-circuit
        # the rest by returning True here and presuming it was successful.
        if config.test is True:
            time.sleep(0.05)
            return True

        # Store the size of the source file to verify the copy was successful.
        expected_size = Size(src).value

        # Do we need to copy, or move?
        copy = config.always_copy is True or not FilmPath.Info.is_same_partition(
            src, dst)

        # Generate a new filename using .partial~ to indicate the file
        # has not be completely copied.
        dst_tmp = dst.parent / f'{dst.name}.partial~'

        # Do the same for dup
        dst_dup = dst.parent / f'{dst.name}.dup~'

        try:
            # If we're overwriting, first try and rename the existing (identical)
            # duplicate so we don't lose it if the move fails
            if dst.exists():
                dst.rename(dst_dup)

            # If copy is enabled, or if partition is not the same, copy with
            # progress bar instead.
            if copy:

                # Copy the file using progress bar
                IO.copy_with_progress(src, dst_tmp)

            # Just move
            else:
                # Otherwise, move the file instead.
                shutil.move(src, dst_tmp)

            # Make sure the new file exists on the filesystem.
            if not dst_tmp.exists():
                Console().red(INDENT,
                    f"Failed to move '{src}'.")
                return False

            # Check the size of the destination file.
            dst_size = Size(dst_tmp).value
            size_diff = abs(dst_size - expected_size)

            # Verify that the file is within 10 bytes of the original.
            if size_diff <= 10:

                # If we're running a test, we need to delay the rename
                if 'pytest' in sys.argv[0]:
                    time.sleep(0.02)

                # Then rename the partial to the correct name
                dst_tmp.rename(dst)

                if src.exists():
                    # Delete the source file if it still exists
                    Delete.file(src)

                if dst_dup.exists():
                    Delete.file(dst_dup)

                return True

            # If not, then we print an error and return False.
            else:
                Console.error(
                    f"{INDENT}Size mismatch when moving '{src}', off by {Size.pretty(size_diff)}.")
                return False

        except (IOError, OSError) as e:

            # Catch exception and soft warn in the console (don't raise Exception).
            Console.error(f"{INDENT}Failed to move '{src}'.")
            Console.debug(e)
            print(e)

            # If we're overwriting and a duplicate was created, undo its renaming
            if dst_dup.exists():
                Delete.file(dst)

            return False

    @staticmethod
    def copy_with_progress(src: Union[str, Path, 'FilmPath'],
                           dst: Union[str, Path, 'FilmPath'],
                           follow_symlinks=True):
        """Copy data from src to dst and print a progress bar.

        If follow_symlinks is not set and src is a symbolic link, a new
        symlink will be created instead of copying the file it points to.

        Args:
            src (str, Path, FilmPath): Path to source file.
            dst (str, Path, FilmPath): Path to destination file.
            follow_symlinks (bool): Follows symbolic links to files and re-creates them.

        """

        def _copyfileobj(fsrc: str, fdst: str, callback, total, length=16*1024):
            copied = 0
            while True:
                buf = fsrc.read(length)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                callback(copied, total=total)

        # Hide the cursor
        Cursor.hide()

        src = Path(src)
        dst = Path(dst)

        if not src.exists():
            raise OSError(f"Error copying '{src}', path does not exist.")

        # If the destination is a folder, append src filename to
        # in the destination.
        if dst.is_dir():
            dst =  dst / src.name

        if dst.exists():
            Console.io_reject('copy', dst)
            return

        # Silently abort if the src and dst are the same.
        if src == dst:
            Console.debug(
                f"Source and destination are the same for '{src}', nothing to copy.")
            return

        # Only perform destructive changes if running in live mode, so we can short-circuit
        # the rest by returning True here and presuming it was successful.
        if config.test is True:
            time.sleep(0.05)
            return

        for f in [src, dst]:
            try:
                st = f.stat()
            except OSError:
                # File most likely does not exist.
                pass
            else:
                if shutil.stat.S_ISFIFO(st.st_mode):
                    raise shutil.SpecialFileError(f"'{f}' is a named pipe.")

        # Handle symlinks.
        if not follow_symlinks and src.is_symlink():
            src.symlink_to(dst)
        else:
            size = os.stat(src).st_size
            with open(src, 'rb') as fsrc:
                with open(dst, 'wb') as fdst:
                    _copyfileobj(fsrc, fdst, callback=Console(
                    ).copy_progress_bar, total=size)

        Tinta().print() # newline
        Tinta.clearline()

        # Perform a low-level copy.
        shutil.copymode(src, dst)

        # Show the cursor.
        Cursor.show()

    @staticmethod
    def rename(src: Union[str, Path, 'FilmPath'],
               new_name: Union[str, Path, 'FilmPath']):
        """Renames a file using Path.rename, with safety checks and test mode support.

        Args:
            src (str, Path, FilmPath): Path to source file.
            new_name (str, Path, FilmPath): New name (or could be a full path, but only
                                            the name will be used.)
        """

        src = Path(src)
        if not src.exists():
            raise OSError(f"Error copying '{src}', path does not exist.")

        # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
        # If we don't do this, the filesystem will try and create a new folder instead
        # of the correct filename.
        # Credit: https://stackoverflow.com/a/34504896/1214800
        if isinstance(new_name, str):
            new_name = new_name.replace(r'/', '-')

        # Whether or not new name is a path or a file, extract the name
        # and apply it to source's parent dir.
        dst = src.parent / (Path(new_name).name)

        # Silently abort if the src and dst are the same.
        if src == dst:
            return

        # Check if a file already exists and abort.
        if dst.exists():
            Tinta().red(INDENT,
                f"Unable to rename, '{dst.name}' already exists in '{dst.parent}'.").print()
            return

        Console.debug(f"\n  Renaming: '{src}'")
        Console.debug(  f"        To: '{dst}'\n")

        # Only perform destructive changes if we're in live mode.
        if not config.test:

            # Rename
            src.rename(dst)

class Parallel:
        """Performs asynchronous concurrent operation on an iterable.
        Once initialized, use the .call(func) method to execute ops."""
        def __init__(self, iterable, max_workers=50):
            self.iterable = iterable
            self.max_workers = max_workers

        def call(self, func, *args, **kwargs):
            loop = asyncio.get_event_loop()
            tasks = asyncio.gather(*[
                asyncio.ensure_future(self._worker(i, o, func, *args, **kwargs))
                for (i, o) in enumerate(self.iterable)
            ])
            return loop.run_until_complete(tasks)

        async def _worker(self, i, o, func, *args, **kwargs):
            # semaphore limits num of simultaneous calls
            async with asyncio.Semaphore(self.max_workers):
                await getattr(o, func.__name__)(*args, **kwargs)
                return o

class Size:
    """Calculates and stores the size of the specified path on the filesystem."""

    def __init__(self, path: Union[str, Path, 'FilmPath']):
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Cannot calculate size, '{path}' does not exist")
        self.path = Path(path)
        try:
            self._size = path._size
        except:
            self._size = None

    def __repr__(self):
        return self.pretty()

    @property
    def value(self) -> int:
        """Determine the size of a file or dir, or returns the cached
        value if it has been set.

        Returns:
            Size of file or folder, in bytes (B), or None.
        """

        if self._size is None:
            if not self.path.exists():
                Console.error(
                    f"{INDENT}Cannot calculate size, '{self.path}' does not exist.")
                self._size = 0
            else:
                self._size = self._calc()
        return self._size

    def _calc(self) -> int:
        """Determine the size of a file or dir.

        Returns:
            Size of file or folder, in bytes (B), or 0.
        """

        if not isinstance(self, Size):
            raise AttributeError("'_calc' was called before Size was initialized.")

        # If it's a directory, we need to call the _size_dir func to recursively get
        # the size of each file inside.
        if self.path.is_dir():
            return sum(f.stat().st_size for f in self.path.glob('**/*') if f.is_file())
        else:
            return self.path.stat().st_size

    def refresh(self) -> int:
        self._size = None
        self.value
        return self._size

    def pretty(self, units: Units = None, precision: int = None) -> str:
        """Formats a size in bytes as a human-readable string.

        Args:
            size (int or float): Size value to format
            units (Units): Size to force formatting to
            precision (int): Number of decimal places

        Returns:
            str: Size, formatted as pretty.
        """
        return Format.pretty_size(self.value or 0, units=units, precision=precision)
