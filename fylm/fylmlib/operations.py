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
import re
import unicodedata
import itertools
from itertools import islice, chain
from multiprocessing import Pool
from pathlib import Path, PurePath
from typing import Union, Iterable

from lazy import lazy

from fylmlib.console import console
from fylmlib.cursor import cursor
import fylmlib.formatter as formatter
import fylmlib.patterns as patterns
import fylmlib.parser as Parser
from fylmlib.tools import *

class FilmPath(Path):
    """A collection of paths used to construct filenames, parseable strings, and locate 
    files. It tries to follow the os.walk() model as best as possible. FilmPath can 
    represent both a file and a dir, depending on whether it was initialized with a 
    file or dir path.
    
    Attributes:
        
        origin (Path):              Origin path originally passed to find_deep, likely 
                                    provided by config or -s, e.g.
                                    
                                     - /volumes/downloads
                                    
        container (FilmPath):       The nearest parent that contains one more films, e.g.
                                    
                                     - /volumes/downloads
                                     - /volumes/downloads/#done
                                     
                                    A container can also be a film candidate, if it tests
                                    true for `maybe_film`, meaning all its contents belong to
                                    a single a single title.
                                    
        branch (Filmpath):          A container that is not a film, as it contains multiple films.
           
        filmrel (Filmpath):             Relative path between branch and self, e.g.

                                     - Avatar.2009.BluRay.1080p/Avatar.2009.BluRay.1080p.x264-Scene.mkv
                                     - Avatar.2009.BluRay.1080p.x264-Scene/av.bluray.1080p.mkv
                                     - Avatar.2009.BluRay.1080p.x264-Scene.mkv
                                     
        filmroot (FilmPath):        The root path of a file or film container whose contents
                                    belong to a single title.
                                     
        files ([FilmPath]):         List of all files in the dir, or a list of one, if path is a 
                                    file. Does not return deeply nested files.
                                            
        video_files ([FilmPath]):   Subset of files that are valid video files.
        
        dirs ([FilmPath]):          List of subdirectories in this path object.
                                    
        siblings ([FilmPath]):      List of all files or dirs that are adjacent to the current path.
        
        descendents ([FilmPath]):   List of all files or dirs contained within the specified dir.
                                    Default (even for files) is an empty list.
        
        is_origin (bool):           Returns True if the path matches the origin.
                                    
        is_container (bool):        Returns True if the path contains multiple films and should 
                                    be investigated recursively.
                                    
        is_branch (bool):           Returns True if the path is container, but not a film.  
        
        filename (str or None):     Filename, if this path is a file, or None
        
        year (int or None):         Year detected in .name.
              
        has_ignored_string (bool):  Returns True if this Path contains any ignored strings.
        
        is_video_file (bool):       True if the path is a file with a suffix matching video_exts.
        
        is_terminus (bool):         True if the path is the last in a tree, i.e. is a file, or is a 
                                    directory but contains no dirs or files, or if we can safely determine 
                                    that all its files or subdirs belong to a single title.
                                    
        is_empty (bool):            True if the path does not contain any files or dirs. Exludes system files
                                    like 'thumbs.db' and '.DS_Store'.
                                    
        is_filelike (bool):         True if the path is file-like, without calling is_file() and checking 
                                    the filesystem. Checks if a path has a suffix.
                                    
        is_filelike (bool):         True if the path is dir-like, without calling is_dir() and checking 
                                    the filesystem. Checks if a path does not have a suffix.                                    
        
        maybe_film (bool):          Returns True if the path is a valid candidate for a possible 
                                    Film object. A candidate must either be a file immediately after
                                    a root path, or a dir containing at least one video file, and
                                    not nested dirs containing additional video files.
                                    
    """
    
    _flavour = type(Path())._flavour
   
    def __init__(self, *args, origin: 'FilmPath'=None, dirs: []=None, files: []=None):
        """Initialize FilmPath object.

        Args:
            origin (WalkPath):      Origin top level path, inherited from args[0] if possible,
                                    or self.
                                        
            dirs (list):            Dirs provided by os.walk(), defauls to []
                                         
            files (list):           Files provided by os.walk(), defaults to []
        """
        super().__init__()
        
        try:
            self._o = origin or args[0].origin
        except:
            self._o = self
                    
        self._dirs: [FilmPath] = list(map(FilmPath, dirs)) if dirs else None
        self._files: [FilmPath] = list(map(FilmPath, files)) if files else None

    # @overrides(joinpath)
    def joinpath(self, path) -> 'FilmPath':
        joined = FilmPath(super().joinpath(path), origin=self.origin)
        self.__dict__ = joined.__dict__.copy()
        return joined
    
    # @overrides(relative_to)
    def relative_to(self, path) -> 'FilmPath':
        rel = FilmPath(super().relative_to(path), origin=self.origin)
        self.__dict__ = rel.__dict__.copy()
        return rel
    
    # @overrrides(parent)
    @property
    def parent(self) -> 'FilmPath':
        return FilmPath(super().parent, origin=self.origin)
    
    # @overrrides(parents)
    @property
    def parents(self) -> ['FilmPath']:
        return [FilmPath(p, origin=self.origin) for p in super().parents]
    
    @property
    def origin(self) -> 'FilmPath':
        return self._o
    
    @property
    def dirs(self) -> ['FilmPath']:
        self._dirs = (self._dirs or 
                      [FilmPath(d) for d in self.iterdir() if d.is_dir()] 
                      if self.is_absolute() and self.is_dir() else [])
        return self._dirs
    
    @lazy
    def siblings(self) -> ['FilmPath']:
        return [x for x in self.parent.dirs + self.parent.files if x != self]
    
    @property
    def descendents(self) -> Iterable['FilmPath']:
        # Note that this is an expensive call, but intentionally performs a scan
        # each time it is called so that we always have a current list of descendents. 
        if self.is_filelike:
            return []
        for d in Find.deep_sorted(self):
            d._o = self.origin
            if d != self:
                yield d
    
    @property
    def files(self) -> ['FilmPath']:
        self._files = (self._files or 
                       [FilmPath(f) for f in self.iterdir() if f.is_file()] 
                       if self.is_absolute() and self.is_dir() else [])
        return self._files
    
    @lazy
    def container(self) -> 'FilmPath':
        return first(self.parents, where=lambda p: (p.is_origin 
                       or self.origin == p 
                       or p.is_container), 
                     default=self if self.is_origin else self.origin)
            
    @lazy
    def filmrel(self) -> 'FilmPath':
        return self.relative_to(self.branch)
    
    @lazy
    def filmroot(self) -> ('FilmPath', 'FilmPath'):
        
        # If this isn't a film, it can't have a filmroot.
        if not self.maybe_film:
            return
        
        # Walk up the parent list to find the first index doesn't have a year
        i = self.parents.index(
            first(self.parents, where=lambda x: not x.year, default=None)
        )
        
        # If no results were found (or the first parent is not a film),
        # but this film has a year, it's its own filmroot.
        if (not i or i == 0) and self.maybe_film:
            return self
        
        # Otherwise, check the nearest parent to see if the years match
        if i > 0:
            
            fr = self.parents[i - 1]

            # If this doesn't have a year, or it does and it 
            # matches the parent, that's the root.
            if not self.year or self.year == fr.year:
                # Return the delta between the root and self
                return fr
            
        return None
    
    @lazy
    def branch(self) -> 'FilmPath':
        # A branch is almost certainly the first parent above a 
        # filmroot isn't a film.
        if self.filmroot and not self.filmroot.parent.maybe_film:
            return self.filmroot.parent
        else:
            return self.container
                   
    @property
    def video_files(self) -> ['FilmPath']:
        return [self] if self.is_video_file else list(filter(lambda f: 
            Utils.is_video_file, 
            self.resolve().rglob("*")))
    
    @lazy
    def is_video_file(self) -> bool:
        return Utils.is_video_file(self)
    
    @lazy
    def year(self) -> int:
        return Parser(self.name).year
    
    @property
    def has_ignored_string(self) -> bool:
        return Utils.has_ignored_string(self)
    
    @lazy
    def is_empty(self) -> bool:
        return not self.dirs and not self.files
    
    @lazy
    def is_filelike(self) -> bool:
        return self.suffix
    
    @lazy
    def is_dirlike(self) -> bool:
        return not self.suffix
        
    @lazy
    def is_origin(self) -> bool:
        return self == self._o
    
    @lazy
    def is_container(self) -> bool:
        # It's not the origin, it's a file or empty, it cannot be a container.
        if not self.is_origin and (self.is_filelike or self.is_empty):
            return False
        
        # Otherwise it's probably a container
        return True
    
    @lazy
    def is_branch(self) -> bool:
        return all([self.is_container, 
                    not self.maybe_film, 
                    not self.is_terminus])
    
    @lazy 
    def is_terminus(self) -> bool:
        # if it's a file or empty, it's a terminus.
        if self.is_filelike or self.is_empty:
            return True
        
        # Lambda: from all objects in x, create a list of years
        get_years = lambda x: [o.year for o in x if o is not None]

        # Lambda: compare a list and see if they all match
        all_match = lambda x: all(y == x[0] for y in x)
        
        # If it contains more than one video file with different years, or 
        # folders with multiple years, it cannot be a terminus (it's a container)
        y = get_years(self.video_files)
        if len(y) > 0 and not all_match(y):
            return False
        
        # Return True if all of its subdirs are empty
        return self.dirs and all(d.is_empty for d in self.dirs)
        
    @lazy
    def maybe_film(self) -> bool:
        # It's an empty dir 
        if ((self.is_dirlike and self.is_empty) 
            # Or it's a file, but not a video
            or (self.is_filelike and not self.is_video_file)):
            return False
        
        # Origin cannot be a film
        if self.is_origin:
            return False
        
        # If it has a year, it's quite possibly a film, even though it might be
        # empty. We return false positives here so that `branch` is strictly not
        # potential film containers.
        if self.year:
            return True

        # It's a video, and either it or its parent have a year, e.g.
        #  - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene/a-x264.mkv
        #                                                           ----------
        if self.is_video_file and (self.year or self.parent.year):
            return True

        # or it's a video file with a year, and its parent does not e.g.
        #  - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene.mkv
        #                       ---------------------------------------
        #  - /volumes/downloads/#done/Avatar.2009.BluRay.1080p.x264-Scene.mkv
        #                             ---------------------------------------
        if self.is_video_file and self.year and not self.parent.year:
            return True

        # or it's a dir with a year in its name, and contains at least one
        # video file, e.g.
        #  - /volumes/downloads/Avatar.2009.BluRay.1080p.x264-Scene/a-x264.mkv
        #                       -----------------------------------
        if self.is_dirlike and self.year and self.video_files:
            return True

        # If it's a terminus, it's the end of the line, maybe it's a film?
        return self.is_terminus
        
class Find:

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
            sort_key (lambda, optional): Sort function, defaults 
                                            to alpha case-insensitive.
            hide_sys_files (bool): Hide system files. Default is True.
            
        Returns:
            A filtered list of files or an empty list.
        """
        
        origin = FilmPath(path)
        if origin.is_file(): 
            return [origin]
        
        for root,dirs,files in os.walk(origin):
            
            if hide_sys_files:
                files = filter(lambda f: not is_sys_file(f), files)
            
            this = FilmPath(root, origin=origin)
            
            this._dirs = [this.joinpath(d) for d in dirs]
            this._files = [this.joinpath(f) for f in files]
            
            dirs = this.dirs
            files = this.files
                        
            yield this
            yield from files
            
    @staticmethod
    def deep_sorted(path: Union[str, Path, 'FilmPath'], 
                    sort_key=lambda p: str(p).lower(),
                    hide_sys_files=True) -> Iterable['FilmPath']:
        yield from sorted(Find.deep(FilmPath(path), 
                                    hide_sys_files=hide_sys_files), 
                                    key=sort_key)
        
    @staticmethod
    def shallow(path: Union[str, Path, 'FilmPath'],
                sort_key=lambda p: str(p).lower(),
                hide_sys_files=True) -> Iterable['FilmPath']:
        """Return a list of all files and dirs contained in a path,
        one-level deep, mapped to FilmPath objects. Note: the original
        path root will always be included in this list. If sorting 
        alphabetically, use [1:] to remove the first element (root).
        If path provided is a single file, return a list with it.

        Args:
            path (str or Path): Root path to search for files.
            sort_key (lambda, optional): Sort function, defaults 
                                            to alpha case-insensitive.
            hide_sys_files (bool): Hide system files. Default is True.
            
        Returns:
            A filtered list of files or an empty list.
        """
        origin = FilmPath(path)
        if origin.is_file(): 
            return [origin]
        
        for p in sorted(origin.iterdir(), key=sort_key):
            if hide_sys_files and is_sys_file(p):
                continue
            yield FilmPath(p, origin=origin)

    _existing_films = None
    @classmethod
    def existing_films(cls, 
                       paths: Union[str, Path, 'FilmPath']=None) -> ['FilmPath']:
        """Get a list of existing films.

        Scan one level deep of the target paths to get a list of existing films.
        # TODO: Took dupe checking ignoring calling this out of this method

        Returns:
            A list of existing films mapped to FilmPath objects.
        """

        # If existing films has already been loaded and the list has
        # more than one film:
        if not cls._existing_films:
            return cls._existing_films
        
        # If paths is none or empty, there's nothing to search for.
        if not paths:
            return
        
        import fylmlib.config as config

        debug('Scanning for existing films...')

        cls._existing_films = []
        
        # Coerce str path objects to FilmPath
        _paths = paths or config.destination_dirs.values()
        if any(type(p) is str for p in _paths):
            _paths = list(map(FilmPath, _paths))
            
        found = itertools.chain([p for p in _paths])
        
        with Pool(processes=50) as pool:
            cls._existing_films += pool.map(lambda x: x.maybe_film, found)
            
        debug(
            f'Loaded {len(cls._existing_films)} existing Film objects from destination dirs.')

        # Sort the existing films alphabetically, case-insensitive, and return.
        return sorted(cls._existing_films, key=lambda s: s.title.lower())
        
class Utils:
    """Utilities and helper functions for FilmPath"""
    
    @staticmethod
    def is_video_file(path: Union[str, Path, 'FilmPath']) -> bool:
        """Returns true if the specified path is a video file from
        config.video_exts.

        Args:
            path (str, Path, or FilmPath): Path to check

        Returns:
            bool: True if it's a video file, otherwise False
        """
        import fylmlib.config as config
        
        # Coerce to a standard path object
        p = Path(path)
        return p.is_file() and p.suffix and p.suffix.lower() in config.video_exts
    
    @staticmethod
    def has_ignored_string(path: Union[str, Path, 'FilmPath']) -> bool:
        """Returns true if the specified path has an invalid string from
        config.ignore_strings.

        Args:
            path (str, Path, or FilmPath): Path to check

        Returns:
            bool: True if it contains an ignored string, otherwise False
        """
        import fylmlib.config as config
        
        # Coerce to a str
        any(word.lower() in str(path).lower() for word in config.ignore_strings)
            
    @staticmethod
    def paths_exist(paths: [], quiet: bool = False) -> bool:
        """Verified that a list of paths exist on the filesystem.

        Args:
            paths [(str, Path, or FilmPath)]: List of paths to check
            quiet (bool): Do not print an error to the console (default is False)

        Returns:
            bool: True if all paths exist, otherwise false
        """
        checked = [Path(p) for p in paths if not p.exists()]
        for p in checked:
            console.error(f"'{d}' does not exist.")
                
        return all(checked) 
    
    @staticmethod
    def same_partition(path1, path2):
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
        
        if not p1.exists(): raise OSError(err(path1))
        if not p2.exists(): raise OSError(err(path2))
        
        return p1.stat().st_dev == p2.stat().st_dev
        

class dirops:
    """Directory-related class method operations.
    """

    # @classmethod
    # def verify_root_paths_exist(cls, paths):
    #     """Verifies that the specified paths (array) exist.

    #     Loops through an array of paths to check that each one exists. If any do not,
    #     raise an Exception. Primarily used at app initiation time to verify that source
    #     and destination paths are in working order.

    #     Args:
    #         paths: (list) paths to verify existence.
    #     """
    #     for d in (d for d in paths if not os.path.exists(d)):
    #         console.error(f"'{d}' does not exist; check source path in config.yaml")

    # @classmethod
    # def is_same_partition(cls, path1, path2):
    #     """Determine if path1 and path2 are on the same partition.

    #     Args:
    #         f1: (str, utf-8) path of source file/folder
    #         f2: (str, utf-8) path of destination file/folder
    #     Returns:
    #     # TODO: Separate the business logic (force_move) from this function
    #         True, if f1 and f2 are on the same parition, or force_move is True, else False.
    #     """

    #     if config.force_move is True:
    #         return True

    #     while not os.path.exists(f1):
    #         f1 = os.path.dirname(f1)

    #     while not os.path.exists(f2):
    #         f2 = os.path.dirname(f2)

    #     return os.stat(os.path.dirname(f1)).st_dev == os.stat(os.path.dirname(f2)).st_dev


    # TODO: REFACTOR
    # @classmethod
    # def find_existing_films(cls, paths):
    #     """Get a list of existing films.

    #     Scan one level deep of the target paths to get a list of existing films. Since
    #     this is used exclusively for duplicate checking, this method is skipped when
    #     duplicate checking is disabled.

    #     Args:
    #         paths: (dict) a set of unicode paths to search for existing films.
    #                Must be passed in the form of: { "<quality>": "<path>" }
    #     Returns:
    #         A list of existing Film objects.
    #     """

    #     # If existing films has already been loaded and the list has
    #     # more than one film:
    #     if cls._existing_films is not None:
    #         return cls._existing_films

    #     # Import Film here to avoid circular import conflicts.
    #     from fylmlib.film import Film

    #     # If check_for_duplicates is disabled, we don't care about duplicates, and
    #     # don't need to spend cycles processing duplicates. Return an empty array.
    #     if config.duplicates.enabled is False:
    #         return []

    #     # Fix paths being a str
    #     if isinstance(paths, str):
    #         paths = { 'default': paths }

    #     # Enumerate the destination directory and check for duplicates.
    #     debug('Loading existing films from disk...')

    #     cls._existing_films = []

    #     # Map a list of valid and sanitized files to Film objects by iterating
    #     # over paths for 720p, 1080p, 4K, and SD qualities.
    #     for path in list(set(os.path.normpath(path) for _, path in paths.items())):
    #         if os.path.normpath(path) not in config.source_dirs:
    #             xfs = [os.path.normpath(os.path.join(path, file)) for file in cls.sanitize_dir_list(os.listdir(path))]
    #             with Pool(processes=50) as pool:                    
    #                 cls._existing_films += pool.map(Film, xfs)

    #     # Strip bad duplicates
    #     cls._existing_films = list(filter(lambda x: x.should_ignore is False, cls._existing_films))

    #     files_count = list(itertools.chain(*[f.video_files for f in cls._existing_films]))
    #     debug(f'Loaded {len(cls._existing_films)} existing unique Film objects containing {len(files_count)} video files')

    #     # Uncomment for verbose debugging. This can get quite long.
    #     # for f in sorted(cls._existing_films, key=lambda s: s.title.lower()):
    #     #     debug(f' - {f.source_path} {f.all_valid_films}')
        
    #     # Sort the existing films alphabetically, case-insensitive, and return.
    #     return sorted(cls._existing_films, key=lambda s: s.title.lower())

    @classmethod
    def find_new_films(cls, paths):
        """Get a list of new potenial films we want to tidy up.

        Scan one level deep of the target path to get a list of potential new files/folders.

        Args:
            paths: (List[str, utf-8]) paths to search for new films.
        Returns:
            An array of potential films.
        """

        # Import Film here to avoid circular import conflicts.
        from fylmlib.film import Film
        import fylmlib.config as config

        films = []

        # Convert to a list if paths is not already (safety check)
        if isinstance(paths, str):
            paths = [paths]

        for path in paths:

            # Check if the source path is a single file (usually because of the -s switch)
            if len(paths) == 1 and os.path.exists(path) and os.path.isfile(path):
                films.append([Film(path)])
                break

            # Enumerate the search path(s) for files/subfolders, then sanitize them.
            # If using the `limit` option, create a sliced list to limit the number of
            # files to be processed.
            raw_films = islice(cls.sanitize_dir_list(os.listdir(
                path)), config.limit if config.limit > 0 else None)

            # Map the list to Film objects and extend the films list
            films.extend(
                list(map(Film, [os.path.join(path, file) for file in raw_films])))

        # Sort the resulting list of files alphabetically, case-insensitive.
        films.sort(key=lambda x: x.title.lower())
        return list(films)
        
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
                    debug(f'Creating destination {path}')
                    os.makedirs(path)
                # If the dir creation fails, raise an Exception.
                except OSError as e:
                    console.error(f'Unable to create {path}', OSError)

    # @staticmethod
    # def find_deep(path: Union[str, Path, 'FilmPath'], 
    #               origin: Union[str, Path, 'FilmPath'] = None) -> ['FilmPath']:
    #     """Deeply search the specified dir and return all files and subdirs.
    #     If path passed is a file, return a list with that single file.

    #     Args:
    #         path (str or Path): Root path to search for files.
            
    #     Returns:
    #         A filtered list of files or an empty list.
    #     """

    #     _path = Utils.coerce_type(path)
    #     _origin = Utils.coerce_type(origin) if origin else _path
    #     if _path.is_file():
    #         return [FilmPath(_path, origin=_origin)]

    #     # Use os.walk() to recursively search the dir and return full path of each file.
    #     # paths = [os.path.join(root, f) for root, dirs, files in os.walk(path) for f in files]
    #     for root, dirs, files in os.walk(path):
    #         fp = FilmPath(root, origin=_origin, container=root, dirs=dirs, files=files)
    #         for d in fp.dirs_abs:
    #             # print(d)
    #             yield FilmPath(d, origin=_origin, container=root)
    #             dirops.find_deep(d, origin=_origin)
    #             # [paths.append(f) for f in dirops.find_deep(d, origin=_origin)]
    #         for f in fp.files_abs:
    #             yield FilmPath(f, origin=_origin, container=root)
                
    #     # return sorted(paths, key=lambda p: str(p).lower())
    #     # Sanitize the list to remove system fils and normalize unicode chars
    #     # return list(filter(lambda f: not f.endswith('.DS_Store') and not f.endswith('Thumbs.db'),
    #     #                    [unicodedata.normalize('NFC', path) for path in paths]))
        
    # TODO: DEPRECATED
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
                           not any(
                               [f.lower() in map(lambda x: x.lower(), config.ignore_strings)])
                           and not f.endswith('.DS_Store') and not f.endswith('Thumbs.db'),
                           [unicodedata.normalize('NFC', file) for file in files]))

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

            debug(f'Recursively deleting {path}')

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
                for f in [f for f in cls.find_invalid_files(path) if os.path.isfile(f)]:
                    # Increment deleted_files if deletion was successful.
                    # `fileops.delete` has test check built in, so
                    # no need to check here.
                    deleted_files += fileops.delete(f)
        return deleted_files

class fileops:
    """File-related class method operations.
    """

    @classmethod
    def exists_case_sensitive(cls, path):
        """Check if file exists, case sensitive.

        Args:
            path: (str, utf-8) path of file to check.
        Returns:
            True if the file exists, else False.
        """
        if not os.path.isfile(path):
            return False
        directory, filename = os.path.split(path)
        return filename in os.listdir(directory)

    @classmethod
    def safe_move(cls, src: str, dst: str, ok_to_upgrade = False):
        """Performs a 'safe' move operation.

        Performs some additional checks before moving files. Optionally supports
        config.safe_copy, which forcibly copies files from one folder to the next
        instead of moving them, even if the files exist on the same partition.
        
        Args:
            src: (str, utf-8) path of file to move.
            dst: (str, utf-8) destination for file to move to.
            ok_to_upgrade: (Bool) True if this file is OK to replace an existing one
                                  as determined by checking for identical duplicates
                                  that meet upgrade criteria.

        Returns:
            True if the file move was successful, else False.
        """

        # Abort if src does not exist in live mode. We can't raise this error in 
        # test mode, because the file would never have been renamed.
        if not os.path.exists(src) and config.test is False:
            raise OSError(f'Path does not exist: {src}')

        # Silently abort if the src and dst are the same.
        if src == dst:
            debug('Source and destination are the same, nothing to move')
            return False

        # Try to create destination folders if they do not exist.
        dirops.create_deep(os.path.dirname(dst))

        debug(f"\n  Moving: '{src}'")
        debug(f"      To: '{dst}'\n")

        # Check if a file already exists with the same name as the one we're moving.
        # By default, abort here (otherwise shutil.move would silently overwrite it)
        # and print a warning to the console. If force_overwrite is enabled, 
        # proceed anyway, otherwise forcibly prevent accidentally overwriting files.
        # If the function was called with a Should property, we can skip this if it's
        # marked for upgrade.
        if os.path.exists(dst) and not ok_to_upgrade:
            # If force_overwrite is turned off, we can't overwrite this file.
            # If interactive is on, the user has some more flexibility and can choose to
            # overwrite, so we can skip this.
            if config.duplicates.force_overwrite is False and config.interactive is False:
                # If we're not overwriting, return false
                console().red().indent(f"Unable to move; a file with the same name already exists in '{os.path.dirname(dst)}'").print()
                return False
                
            # File overwriting is enabled and not marked to upgrade, so warn but continue
            console().yellow().indent(f"Replacing existing file in '{os.path.dirname(dst)}'").print()

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
                    console().red().indent(f"Size mismatch; file is {dst_size:,} bytes, expected {expected_size:,} bytes")
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
            debug(e)
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

        debug(f'Renaming: {src}')
        debug(f'      To: {dst}')

        # Only perform destructive changes if we're in live mode.
        if not config.test:

            # Rename the file using shutil.move (instead of os.rename). (os.rename won't work if the
            # src/dst are on different partitions, so we use shutil.move instead). There is also
            # some funky (untested) Windows-related stuff that makes .move the obvious choice.
            os.rename(src, dst)

    @classmethod
    def delete(cls, file) -> int:
        """Attempts to delete the specified file, and returns a number that can be used to
        increment a counter if the deletion was successful.

        Args:
            file (str): Full path (including filename) of file to check for ignored strings.
        
        Returns:
             1 if the delete was successful, 0 otherwise.
        """
        debug(f"Deleting file {file}")

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

def size(path: str or Path) -> int:
    """Determine the size of a file or dir.

    Args:
        path (str): File or folder to determine size.
    Returns:
        Size of file or folder, in bytes (B), or 0.
    """
    p = Path(path)
    if not p.exists():
        raise Exception(f'Cannot calculate size for a path that does not exist ({path})')

    # If it's a directory, we need to call the _size_dir func to recursively get
    # the size of each file inside.
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob('*'))
    else:
        return p.stat().st_size
