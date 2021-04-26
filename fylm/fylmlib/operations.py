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
import pickle
import time
from itertools import chain, repeat
import multiprocessing as mp
from pathlib import Path
from typing import Union, Iterable

from lazy import lazy

import fylmlib.config as config
import fylmlib.patterns as patterns
from fylmlib.tools import *
from fylmlib.enums import *
from fylmlib import Console
from fylmlib import Parser
from fylmlib import Cursor
from fylmlib import Format

sys.setrecursionlimit(2000)

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
            max_size: int = 50*1024, force: bool = False):
        """Recursively delete dir path and all its contents, if the total dir 
        size is less than max_size (default 50 KB).

        Args:
            path (str, Path, or FilmPath): Path to be recursively deleted.
            max_size (int, optional): Max size in Bytes a folder can be to 
                                      allow for deletion. Default=50000.
            force (bool): Force deletion by setting max_size to -1
        """
        
        path = Path(path)
        # Check to make sure p isn't a source dir
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

            Console.debug(f"Recursively deleting '{path}' which contains {files_count} files.")

            # Only perform destructive actions if we're running in live mode.
            if config.test is False:
                try:
                    shutil.rmtree(path)

                # Catch resource busy error
                except OSError as e:
                    if e.args[0] == 16:
                        console.error(
                            f"Failed to remove '{path}', it is in use.")
        else:
            Console().red().indent(
                f"Will not delete '{path}' ({'not empty' if files_count > 0 else Size.pretty(max_size)})"
            )
            
    @staticmethod
    def files(paths: [Union[str, Path, 'FilmPath']], count: int = 0) -> int:
        """Delete all files in the specified paths list or generator

        Count helps keep track of the number of files that were deleted, for reporting
        and recursion. 

        Args:
            path (list or Iterable of str, Path, or FilmPath): Path to search for files to delete.
            count (int, optional): Current number of deleted files, for external tracking.

        Returns:
            int: Number of files that were deleted successfully.
        """
        # TODO: Removed 'if config.remove_unwanted_files:' from this method, needs to be elsewhere.

        deleted_files = count
        
        for f in paths:
            if not config.test:
                deleted_files += Delete.path(f)
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
                Console().error().indent(f"Could not delete 'p'; it does not exist.")
            else:
                if not config.test:
                    p.unlink()
                # If successful, return 1 for a successful op.
                return 1
        except Exception as e:
            Console().error().indent(f"Unable to remove '{path}': {e}")
        
        # Default return 0
        return 0
                         
class FilmPath(Path):
    """A collection of paths used to construct filenames, parseable strings, and locate 
    files. It tries to follow the os.walk() model as best as possible. FilmPath can 
    represent both a file and a dir, depending on whether it was initialized with a 
    file or dir path.
    
    Init args:
    
        origin
        dirs
        files
    
    Overrides:

        joinpath()
        parent
        parents
        relative_to()
    
    Attributes:
                                    
        branch (Path):              The nearest parent that contains one more films, e.g.
                                    
                                     - /volumes/downloads
                                     - /volumes/downloads/#done
        
        descendents ([FilmPath]):   Iterable of all files or dirs contained within the specified dir.
                                    Default (even for files) is an empty list.
        
        dirs ([FilmPath]):          List of subdirectories in this path object.
                                     
        files ([FilmPath]):         List of all files in the dir, or a list of one, if path is a 
                                    file. Does not return deeply nested files.
           
        filmrel (FilmPath):         Relative path between branch and self, e.g.

                                     - Avatar.2009.BluRay.1080p/Avatar.2009.BluRay.1080p.x264-Scene.mkv
                                     - Avatar.2009.BluRay.1080p.x264-Scene/av.bluray.1080p.mkv
                                     - Avatar.2009.BluRay.1080p.x264-Scene.mkv
                                     
        filmroot (FilmPath):        The root path of a file or dir.
                                    
        is_container (bool):        Returns True if the path contains multiple films and should 
                                    be investigated recursively.
                                    
        is_empty (bool):            True if the path does not contain any files or dirs. Exludes system files
                                    like 'thumbs.db' and '.DS_Store'.  
        
        is_origin (bool):           Returns True if the path matches the origin.
                                    
        is_branch (bool):           Returns True if the path is container, but not a film.  
        
        is_filmroot (bool):         Returns True if the path is the filmroot.
        
        is_terminus (bool):         True if the path is the last in a tree, i.e. is a file, or is a 
                                    directory but contains no dirs or files, or if we can safely determine 
                                    that all its files or subdirs belong to a single title.    
        
        is_video_file (bool):       True if the path is a file with a suffix matching video_exts.
              
        has_ignored_string (bool):  Returns True if this Path contains any ignored strings.
        
        has_valid_ext (bool):       Returns True if this Path is a file, and has a valid video ext
                                    (either in config.video_exts or config.extra_exts).                       
        
        maybe_film (bool):          Returns True if the path is a valid candidate for a possible 
                                    Film object. A candidate must either be a file immediately after
                                    a root path, or a dir containing at least one video file, and
                                    not nested dirs containing additional video files.
        
        origin (Path):              Origin path originally passed to find_deep, likely 
                                    provided by config or -s, e.g.
                                    
                                     - /volumes/downloads
                                     
        size (Size):                Size object containing size of the file or dir.
                                            
        siblings ([FilmPath]):      Iterable of all files or dirs that are adjacent to the current path.
                                            
        video_files ([FilmPath]):   Iterable subset of files that are valid video files.
        
        xyear (int or None):        Year detected in in the name segment.
        
    Methods:
    
        sync(fp: FilmPath, attrs):  Calls and sets lazy attributes to the passed FilmPath object.
                                    
    """
    
    _flavour = type(Path())._flavour
   
    def __init__(self, *args, origin: 'Path'=None, dirs: []=None, files: []=None):
        """Initialize FilmPath object.

        Args:
            origin (Path):      Origin top level path, inherited from args[0] if possible,
                                or self.
                                        
            dirs (list):        Dirs provided by os.walk(), defauls to []
                                         
            files (list):       Files provided by os.walk(), defaults to []
        """
        super().__init__()
        
        if origin:
            self._origin = Path(origin)
        elif len(args) > 0:
            try:
                self._origin = Path(args[0].origin) or Path(args[0])
            except:
                self._origin = Path(self)

        if not '_origin' in self.__dict__:
            raise AttributeError(
                f"Could not infer 'origin' when initializing 'FilmPath' for path '{args[0]}'")
                    
        self._dirs: [FilmPath] = list(map(FilmPath, dirs)) if dirs else None
        self._files: [FilmPath] = list(map(FilmPath, files)) if files else None
        self._size = None

    # @overrides(__reduce__)
    def __reduce__(self):

        # From super()

        # Using the parts tuple helps share internal path parts
        # when pickling related paths.

        # return (self.__class__, tuple(self._parts))

        # This override passes its parts to a Path object (which
        # natively pickles), then serializes and applies
        # its remaining attributes.

        # This is required in order to support pickling for async ops.
        # ---
        
        # We need to check all children of this object's __dict__ to make sure there
        # are no circular references to a type matching 'self'.

        for _, v in self.__dict__.items():
            try:
                for ki, vi in v.__dict__.items():
                    if type(vi) == type(self):
                        v.__dict__[ki] = Path(vi)
            except:
                pass

        args = {**{'_parts': self._parts}, **self.__dict__}
        return (self.__class__._from_kwargs, tuple(args.items()))

    # @overrides(_make_child)
    def _make_child(self, args):
        drv, root, parts = self._parse_args(args)
        drv, root, parts = self._flavour.join_parsed_parts(
            self._drv, self._root, self._parts, drv, root, parts)
        new = self._from_parsed_parts(drv, root, parts)
        new._origin = self._origin
        return new

    # @overrrides(iterdir)
    def iterdir(self) -> Iterable['FilmPath']:
        yield from [FilmPath(x, origin=self.origin) for x in super().iterdir()]
    
    # @overrides(joinpath)
    def joinpath(self, path) -> 'FilmPath':
        joined = FilmPath(super().joinpath(path), origin=self.origin)
        # TODO: I think we don't actually want this here.
        # self.__dict__ = joined.__dict__.copy()
        return joined
    
    # @overrrides(parent)
    @property
    def parent(self) -> 'FilmPath':
        return FilmPath(super().parent, origin=self.origin)
    
    # @overrrides(parents)
    @property
    def parents(self) -> ['FilmPath']:
        return [FilmPath(p, origin=self.origin) for p in super().parents]

    # @overrides(relative_to)
    def relative_to(self, path) -> 'FilmPath':
        return FilmPath(super().relative_to(path), origin=self.origin)

    @classmethod
    def _from_kwargs(cls, *args):

        # Support init from kwargs passed in a tuple from reduce.

        try:
            kwargs = dict(*args)
        except:
            kwargs = dict(args)
                    
        new = cls(super().__new__(cls, *kwargs['_parts']), origin=kwargs['_origin'])
        new.__dict__ = {**new.__dict__, **kwargs}
        return new

    @lazy
    def branch(self) -> 'Path':       
        # A relative path cannot have a branch.
        if not self.is_absolute():
            return
        
        # A branch is the first parent above a filmroot.
        # Default is origin.
        return Path(self.filmroot.parent if self.filmroot else 
                    first(iter(self.parents), where=lambda x: x.is_branch))

    @property
    def descendents(self) -> Iterable['FilmPath']:
        # Note that this is an expensive call, but intentionally performs a scan
        # each time it is called so that we always have a current list of descendents.
        if self.is_file():
            return []
        for d in Find.deep_sorted(self):
            d.origin = self.origin
            if d != self:
                yield d
    
    @property
    def dirs(self) -> ['FilmPath']:
        if self._dirs:
            return self._dirs
        if not self.is_dir() or not self.is_absolute():
            raise NotADirectoryError(
                f"No 'dirs' for '{self}', it is not a dir.")
        else:
            self._dirs = [FilmPath(d) for d in Find.shallow(self) if (
                d.is_dir() and not d == self)]
        return self._dirs

    @property
    def files(self) -> ['FilmPath']:
        if self._files:
            return self._files
        if not self.is_dir() or not self.is_absolute():
            raise NotADirectoryError(f"No 'files' for '{self}', it is not a dir.")
        else:
            self._files = [FilmPath(f) for f in Find.shallow(self) if f.is_file()]
        return self._files

    @lazy
    def filmrel(self) -> 'FilmPath':
        
        # If it doesn't exist, but is a video file or has a year, 
        # walk the parents to find the first path without year, then 
        # return the relative path between it and self.
        if self.is_video_file or (self.xyear or self.parent.xyear):
            fr = first(self.parents,
                       where=lambda x: not x.xyear,
                       default=None)
            return self.relative_to(fr) if fr else None

    @lazy
    def filmroot(self) -> 'Path':
        
        # The first in the list of self + self.parents where is_filmroot is True
        fr = first(iterunshift(self, to=self.parents),
                          where=lambda x: x.is_filmroot, 
                          default=None)
        return Path(fr) if fr else None

    @lazy
    def has_ignored_string(self) -> bool:
        return Info.has_ignored_string(self)

    @lazy
    def has_valid_ext(self) -> bool:
        return Info.has_valid_ext(self)

    @lazy
    def is_branch(self) -> bool:
        
        if self.is_file():
            return False
        
        # If it's a directory, without a year, and 
        # containing at least one non-empty dir
        if (self.is_dir() 
            and not self.xyear 
            and self.dirs 
            and any(not d.is_empty for d in self.dirs)):
            return True
        
        # Lambda: from all objects in x, create a list of years
        def get_years(x): return [o.xyear for o in x if o is not None]

        # Lambda: compare a list and see if they all match
        def all_match(x): return all(y == x[0] for y in x if y)

        # If it contains more than one video file with different years, or
        # dirs with multiple years, it must be a branch
        y = get_years(iterunshift(self, self.dirs, to=self.video_files))
        if len(y) > 1 and not all_match(y):
            return True
         
        return False

    @lazy
    def is_empty(self) -> bool:
        if not self.is_dir():
            raise NotADirectoryError(f"'is_empty' failed, '{self}' is not a dir.")
        return not first(self.iterdir(), where=lambda x: not is_sys_file(x))

    @lazy
    def is_filmroot(self) -> bool:
        
        # For relative paths, the top path part is considered the filmroot.
        if not self.is_absolute():
            if self.parent == Path('.'):
                self.filmroot = Path(self)
                return True
        
        # If it's not a terminus, it cannot be a filmroot.
        # Terminus criteria:
        # - Not origin, and
        #   - A file, or
        #   - A dir with no subdirs, or only empty ones
        if not self.is_terminus:
            return False

        # If it's a video file and its parent doens't have a year
        if self.is_video_file and not self.parent.xyear:
            self.filmroot = Path(self)
            return True
        
        # Lambda: from all objects in x, create a list of years if not None
        def get_years(x): return [y for y in [o.xyear for o in x] if y is not None]

        # Lambda: compare a list and see if they all match
        def all_match(x): return all(y == x[0] for y in x if y)

        # If it’s a video file, and its parent + parent’s video files years all match
        if self.is_video_file and all_match(get_years(
                iterunshift(self.parent, to=self.parent.video_files))):
            self.parent.is_filmroot = True
            self.filmroot = Path(self.parent)
            return False
        
        # If’s a dir with > 0 video files and self + video files years match
        if self.is_dir() and iterlen(self.video_files) > 0 and all_match(
                get_years(iterunshift(self, to=self.video_files))):
            for c in self.descendents: c.filmroot = Path(self)
            for c in self.descendents: c.is_filmroot = False
            return True
        
        # If none of the above criteria were met, it's not likely a filmroot.
        return False
        

    @lazy
    def is_origin(self) -> bool:
        return Path(self) == self.origin

    @lazy
    def is_terminus(self) -> bool:

        # if it's a file or empty, it's a terminus.
        if self.is_file():
            return True
            
        if self.is_dir() and (not self.dirs or all(d.is_empty for d in self.dirs)):
            return True
        
        return False

    @lazy
    def is_video_file(self) -> bool:
        return Info.is_video_file(self)
        
    @lazy
    def maybe_film(self) -> bool:
        
        # If it's not absolute, we can only check for year and video ext.
        if not self.is_absolute() and (self.is_video_file or self.xyear):
            return True
        
        # If it doesn't exist, all we can do is check it or its parent 
        # for a year.
        if not self.exists() and (self.is_video_file 
                                  or self.xyear 
                                  or self.parent.xyear):
            return True
            
        
        # It's a video file and its parent is a branch
        if self.is_video_file and self.parent.is_branch:
            return True
        
        # It's a filmroot, or it has one.
        if self.is_filmroot or self.filmroot:
            return True
        
        # Otherwise it's not likely a film
        return False

    @property
    def origin(self) -> Path:
        return self._origin

    @origin.setter
    def origin(self, value: Union[str, Path, 'FilmPath']):
        self._origin = Path(value)

    @lazy
    def siblings(self) -> Iterable['FilmPath']:
        if not self.is_absolute():
            raise ValueError(
                f"'siblings' failed '{self}', path must be absolute.")
        yield from [x for x in self.parent.iterdir() if x != self and not is_sys_file(x)]

    @property
    def size(self) -> int:
        if self._size is None:
            self._size = Size(self)
            self._size.value
        return self._size

    @property
    def video_files(self) -> Iterable['FilmPath']:
        if not self.exists():
            raise FileNotFoundError(
                f"'video_files' failed, '{self}' does not exist.")
        if not self.is_dir():
            raise NotADirectoryError(
                f"'video_files' failed, '{self}' is not a dir.")
        return filter(lambda f: Info.is_video_file(f), self.resolve().rglob("*"))

    @lazy
    def xyear(self) -> int:
        
        # If it's not an absolute path, we can check the whole path.
        return Parser(self.name if self.is_absolute() else str(self)).year
    
    @staticmethod
    def sync(fp: 'FilmPath', attrs):
        """Syncronize lazy-loaded attributes to the provided FilmPath object.

        Args:
            fp (FilmPath): FilmPath to sync slow properties

        Returns:
            FilmPath: The passed FilmPath object with lazy loaded properties.
        """
        default = [
            'is_origin',
            'is_terminus',
            'is_branch',
            'is_filmroot',
            'maybe_film'
        ]
        for a in (attrs or default):
            fp.__dict__[a] = getattr(fp, a)
        return fp
            
class Find:
    """A collection of methods to search for files and dirs."""
    
    _NEW = None # Cached list from Find.new()
    _EXISTING = None # Cached list from Find.existing()

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
                f"Cannot use Find.deep on '{self}', it is not a dir.")
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
                f"Cannot use Find.shallow on '{self}', it is not a dir.")
        else:
            found = origin.iterdir()
            if sort_key:
                found = sorted(found, key=sort_key)
            for p in found:
                if hide_sys_files and is_sys_file(p):
                    continue
                yield FilmPath(p, origin=origin)
    
    @classmethod
    def existing(cls, 
                 *paths,
                 sort_key=None) -> ['FilmPath']:
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
        if cls._EXISTING:
            return cls._EXISTING
        
        # If paths is none or empty, there's nothing to search for.
        
        Console.debug('Searching for existing films...')
        
        # Coerce str path objects to Path set
        _paths = list(map(Path, set(paths) if paths else set(
            config.destination_dirs.values())))
        
        # Shallow scan the target dirs
        found_iter = itertools.chain.from_iterable(
            Find.shallow(p, sort_key=sort_key) for p in _paths)
            
        # Set the class var
        cls._EXISTING = list(found_iter)
        
        return cls._EXISTING
    
    @classmethod
    def new(cls, 
            *paths,
            sort_key=lambda p: p.name.lower()) -> ['FilmPath']:
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
        if cls._NEW:
            return cls._NEW
        
        Console.debug('Loading new films...')
        
        # Coerce list path objects to Path set
        if paths and type(paths[0]) == list:
            paths = tuple(paths[0])
        
        # Coerce str path objects to Path set
        paths = set(list(map(Path, paths if paths else config.source_dirs)))

        # Shallow scan the target dirs, then sync the maybe_film attr.
        found_iter = itertools.chain.from_iterable(
            Find.deep_sorted(p, sort_key=sort_key) for p in paths)
        
        # Set the class var
        cls._NEW = list(found_iter)

        return cls._NEW
    
    # @staticmethod
    # # FIXME: Probably not going to keep this
    # def invalid_files_deep(path: Union[str, Path, 'FilmPath']) -> Iterable['FilmPath']:
    #     """Scan deeply to find invalid files inside the specified dir.
    #     Note that system files are ignored here, and will not be returned
    #     even if they exist.
        
    #     Args:
    #         path (str, Path, or FilmPath) path to create.
            
    #     Returns:
    #         A generator of invalid files.
    #     """

    #     # Call dir.find_deep to search for files within the specified dir.
    #     # Filter the results using a lambda function.
    #     yield from filter(lambda x: x.is_file() and not x.is_valid, Find.deep(path))
    
    @staticmethod
    def sync_parallel(paths: Iterable['FilmPath'], attrs: [] = None) -> ['FilmPath']:
        with mp.Pool() as pool:
            yield from pool.starmap(FilmPath.sync, zip(paths, repeat(attrs)))
            
class Info:
    """Utilities and helper functions for FilmPath"""
    
    @staticmethod
    def is_acceptable_size(path: 'FilmPath') -> bool:
        """Determine if a path is an acceptable size.

        Args:
            path (FilmPath): Path to file.
            
        Returns:
            True, if the path is an acceptable size, else False.
        """
        return int(path.size.value) >= Info.min_filesize(path)
    
    @staticmethod
    def is_video_file(path: Union[str, Path, 'FilmPath']) -> bool:
        """Determines if the specified path is a video file from
        config.video_exts.

        Args:
            path (str, Path, or FilmPath): Path to check

        Returns:
            bool: True if it's a video file, otherwise False
        """
        
        # Coerce to a standard Path object
        p = Path(path)
        return p.suffix and p.suffix.lower() in config.video_exts
    
    @staticmethod
    def has_valid_ext(path: Union[str, Path, 'FilmPath']) -> bool:
        """Determines if the specified path is a video file from
        config.video_exts.

        Args:
            path (str, Path, or FilmPath): Path to check

        Returns:
            bool: True if it's a video file, otherwise False
        """
        # Coerce to a standard Path object
        p = Path(path)
        return p.is_file() and p.suffix and (
            p.suffix.lower() in config.video_exts + config.extra_exts)
    
    @staticmethod
    def has_ignored_string(path: Union[str, Path, 'FilmPath']) -> bool:
        """Returns true if the specified path has an invalid string from
        config.ignore_strings.

        Args:
            path (str, Path, or FilmPath): Path to check

        Returns:
            bool: True if it contains an ignored string, otherwise False
        """
       
        # Coerce to a str
        return any(word.lower() in str(path).lower() for word in config.ignore_strings)
    
    @staticmethod
    def min_filesize(path: 'FilmPath') -> int:
        """Determine the minimum filesize for the resolution for path.

        Args:
            path (FilmPath): Path to file.

        Returns:
            int: The minimum file size in bytes, or default in bytes
                    if resolution could not be determined.
        """

        # If the file is valid but not a video, we can't expect
        # it to be too large (e.g., .srt)
        if not path.is_video_file:
            return 0

        # If the config is simple, just an int, return that in MB
        min = config.min_filesize
        if isinstance(min, int):
            return min

        # If the min filesize is not an int, we assume
        # that it is an Addict of resolutions.
        size = min.default

        try:
            res = path.resolution
        except:
            res = Parser(path).resolution

        if res is None:
            size = min.default
        elif res.value > 3:  # 3 and higher are SD res
            size = min.SD
        else:
            size = min[res.display_name]

        # If we're running tests, files are in MB instead of GB
        t = 1 if 'pytest' in sys.argv[0] else 1024
        return size * 1024 * t
            
    @staticmethod
    def paths_exist(paths: [Union[str, Path, 'FilmPath']], quiet: bool = False) -> bool:
        """Verified that a list of paths exist on the filesystem.

        Args:
            paths [(str, Path, or FilmPath)]: List of paths to check
            quiet (bool): Do not print an error to the console (default is False)

        Returns:
            bool: True if all paths exist, otherwise false
        """
        failed = [x for x in [Path(p) for p in paths] if not x.exists()]
        for p in failed:
            Console.error(f"'{p}' does not exist.")
                
        return not failed
    
    @staticmethod
    def is_same_partition(path1: Union[str, Path, 'FilmPath'], 
                          path2: Union[str, Path, 'FilmPath']):
        """Determine if path1 and path2 are on the same partition.

        Args:
            path1 (str or Pathlike): First path to check
            path2 (str or Pathlike): Second path to check
            
        Returns:
        # TODO: Separate the business logic (force_move) from this function
            True, if path1 and path2 are on the same parition, otherwise False
        """
        
        p1 = Path(path1)
        p2 = Path(path2)
        
        err = lambda x: f"Tried to get the mount point for a path that does not exist '{x}'."
        
        while not p1.exists():
            p1 = p1.parent
            
        while not p2.exists():
            p2 = p2.parent
        
        return p1.stat().st_dev == p2.stat().st_dev
    
    @staticmethod
    def exists_case_sensitive(path: Union[str, Path, 'FilmPath']) -> bool:
        """Check if file exists, case sensitive.

        Args:
            path (str, Path, or FilmPath): List of paths to check
            
        Returns:
            True if the path exists, else False.
        """
        p = Path(path)
        if not p.exists():
            return False
        return p in p.parent.iterdir()
    
class Move:
    """Move and copy filesystem utils"""
    
    @staticmethod
    def safe(src: Union[str, Path, 'FilmPath'], 
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
        
        src = src if type(src) is FilmPath else Path(src)
        dst = src if type(dst) is FilmPath else Path(dst)

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
                Console().red().indent(
                    f"Unable to move, '{dst.name}' already exists in '{dst.parent}'.").print()
                return False

            # File overwriting is enabled and not marked to upgrade, so warn but continue
            Console().yellow().indent(
                f"Replacing existing file in '{dst.parent}'.").print()

        # Only perform destructive changes if running in live mode, so we can short-circuit
        # the rest by returning True here and presuming it was successful.
        if config.test is True:
            time.sleep(0.05)
            return True

        # Store the size of the source file to verify the copy was successful.
        expected_size = Size(path).calc()

        # Do we need to copy, or move?
        copy = config.always_copy is True or not Info.is_same_partition(
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
                Move.copy_with_progress(src, dst_tmp)
            
            # Just move
            else:
                # Otherwise, move the file instead.
                shutil.move(src, dst_tmp)
                
            # Make sure the new file exists on the filesystem.
            if not dst_tmp.exists():
                console().red().indent(
                    f"Failed to move '{src}'.")
                return False

            # Check the size of the destination file.
            dst_size = Size.calc(dst_tmp)
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
                console().red().indent(
                    f"Size mismatch when moving '{src}', off by {Size.pretty(diff)}.")
                return False           

        except (IOError, OSError) as e:

            # Catch exception and soft warn in the console (don't raise Exception).
            Console().red().indent(f"Failed to move '{src}'.")
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
            console().red().indent(
                f"Unable to copy, a file named '{dst.name}' already exists in '{dst.parent}'.").print()
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
                    Move._copyfileobj(fsrc, fdst, callback=Console(
                    ).print_copy_progress_bar, total=size)

        # Perform a low-level copy.
        shutil.copymode(src, dst)
        
        # Show the cursor.
        Cursor.show()

        # Clear the progress bar from the console.
        Console.clearline()
        
    @staticmethod
    def _copyfileobj(fsrc: str, fdst: str, callback, total, length=16*1024):
        """Internal method for low-level copying.

        Executes low-level file system copy and calls back progress
        to progress bar function.

        Args:
            fsrc: (str, utf-8) path to source file.
            fdst: (str, utf-8) path to destination file.
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
        if type(new_name) is str:
            new_name = new_name.replace(r'/', '-')
        
        # Whether or not new name is a path or a file, extract the name 
        # and apply it to source's parent dir.
        dst = src.parent / (Path(new_name).name)

        # Silently abort if the src and dst are the same.
        if src == dst:
            return
        
        # Check if a file already exists and abort.
        if dst.exists():
            Console().red().indent(
                f"Unable to rename, '{dst.name}' already exists in '{dst.parent}'.").print()
            return

        Console.debug(f"\n  Renaming: '{src}'")
        Console.debug(  f"        To: '{dst}'\n")

        # Only perform destructive changes if we're in live mode.
        if not config.test:

            # Rename
            src.rename(dst)
   
class Size:
    """Calculates and stores the size of the specified path on the filesystem."""
    
    def __init__(self, path: Union[str, Path, 'FilmPath']):
        if not Path(path).exists():
            raise FileNotFoundError(
                f"Cannot calculate size, '{path}' does not exist")
        self.path = Path(path)
        self._size = path._size if type(path) == FilmPath else None
        
    def __repr__(self): 
        return self.pretty()
    
    # def __float__(self): return float(self.size or 0)
    # def __int__(self): return int(self.size or 0)
    # def __add__(self, other): return int.__add__(self.size, num(other))
    # def __sub__(self, other): return int.__sub__(self.size, num(other))
    # def __mul__(self, other): return int.__mul__(self.size, num(other))
    # def __matmul__(self, other): return int.__matmul__(self.size, num(other))
    # def __truediv__(self, other): return int.__truediv__(self.size, num(other))
    # def __floordiv__(self, other): return int.__floordiv__(self.size, num(other))
    # def __mod__(self, other): return int.__mod__(self.size, num(other))
    # def __divmod__(self, other): return int.__divmod__(self.size, num(other))
    # def __pow__(self, other, modulo=None): 
    #     return int.__pow__(self.size, num(other), int(modulo) if modulo else None)
    # def __lshift__(self, other): return int.__lshift__(self.size, num(other))
    # def __rshift__(self, other): return int.__rshift__(self.size, num(other))
    # def __and__(self, other): return int.__and__(self.size, num(other))
    # def __xor__(self, other): return int.__xor__(self.size, num(other))
    # def __or__(self, other): return int.__or__(self.size, num(other))
    # def __lt__(self, other): return int.__lt__(self.size, num(other))
    # def __le__(self, other): return int.__le__(self.size, num(other))
    # def __eq__(self, other): return int.__eq__(self.size, num(other))
    # def __ne__(self, other): return int.__ne__(self.size, num(other))
    # def __ge__(self, other): return int.__ge__(self.size, num(other))
    # def __gt__(self, other): return int.__gt__(self.size, num(other))
    
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
                    f"Cannot calculate size, '{self.path}' does not exist.")
                self._size = 0
            else:
                self._size = self._calc()
        return self._size
    
    def _calc(self) -> int:
        """Determine the size of a file or dir.
            
        Returns:
            Size of file or folder, in bytes (B), or 0.
        """
        
        if not type(self) == Size:
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
