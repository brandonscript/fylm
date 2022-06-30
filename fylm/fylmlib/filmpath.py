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

"""FilmPath object.

    A stateful subclass of Path which includes
    specific use cases for film file and folder objects.
"""

from pathlib import Path
import sys
from typing import List, Union, Iterable

from lazy import lazy

import fylmlib.config as config
from .tools import *
from .enums import *
from . import Parser, Console

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fylmlib.operations import Size

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

        is_branch (bool):           Returns True if the path is likely to contain more than one film.

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

        _year (int or None):        Year detected in in the name segment.

    Methods:

        sync(fp: FilmPath, attrs):  Calls and sets lazy attributes to the passed FilmPath object.

    """

    _flavour = type(Path())._flavour

    def __init__(self, *args, origin: 'Path' = None, dirs: List = None, files: List = None):
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

        self._dirs: List[FilmPath] = list(map(FilmPath, dirs)) if dirs else None
        self._files: List[FilmPath] = list(map(FilmPath, files)) if files else None
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

        # Short-circuit recursion by checking referenced types three levels deep.
        # If at the third level, any types match self or second level, cast them
        # to Path instead, which does not maintain state.

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
        return joined

    # @overrrides(parent)
    @property
    def parent(self) -> 'FilmPath':
        return FilmPath(super().parent, origin=self.origin)

    # @overrrides(parents)
    @property
    def parents(self) -> List['FilmPath']:
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

        new = cls(super().__new__(
            cls, *kwargs['_parts']), origin=kwargs['_origin'])
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
        from fylmlib import Find
        if self.is_file():
            return []
        for d in Find.deep_sorted(self):
            d.origin = self.origin
            if d != self:
                yield d

    @lazy
    def dirs(self) -> List['FilmPath']:
        from fylmlib import Find
        if self._dirs:
            return self._dirs
        if not self.is_dir() or not self.is_absolute():
            return None
        self._dirs = [FilmPath(d, origin=self.origin) for d in Find.shallow(self) if (
            d.is_dir() and not d == self)]
        return self._dirs

    @lazy
    def files(self) -> List['FilmPath']:
        from fylmlib import Find
        if self._files:
            return self._files
        if not self.is_dir() or not self.is_absolute():
            return None
        self._files = [FilmPath(f, origin=self.origin)
                       for f in Find.shallow(self) if f.is_file()]
        return self._files

    @lazy
    def filmrel(self) -> 'FilmPath':

        # If it doesn't exist, but is a video file or has a year,
        # walk the parents to find the first path without year, then
        # return the relative path between it and self.
        if self.is_video_file or (self._year or self.parent._year):

            if not self.is_absolute():
                return self

            fr = first(self.parents,
                       where=lambda x: x.parent.is_branch,
                       default=None)
            if not fr:
                return
            # If we already have a year but the parent does not,
            # that's good enough
            if self._year and not fr._year:
                return self.relative_to(fr)
            # Otherwise, we check fr or its parent for a year
            # (and make sure it's not a branch)
            elif (fr._year or fr == self.parent) and not fr.is_branch:
                return self.relative_to(fr.parent)
            else:
                return self.relative_to(fr)
        # If there are no other video files in this dir, it
        # should have the same filmrel as its child video file
        elif self.is_dir() and iterlen(self.video_files) == 1:
            return first(self.video_files).relative_to(self.parent)

    @lazy
    def filmroot(self) -> 'Path':

        # The first in the list of self + self.parents where is_filmroot is True
        fr = first(prepend(self, to=self.parents),
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
            and not self._year
            and self.dirs
                and any(not d.is_empty for d in self.dirs)):
            return True

        # Lambda: from all objects in x, create a list of years
        def get_years(x): return [o._year for o in x if o is not None]

        # Lambda: compare a list and see if they all match
        def all_match(x): return all(y == x[0] for y in x if y)

        # If it contains more than one video file with different years, or
        # dirs with multiple years, it must be a branch
        y = get_years(prepend(self, self.dirs, to=self.video_files))
        if len(y) > 1 and not all_match(y):
            return True

        return False

    @lazy
    def is_empty(self) -> bool:
        if not self.exists():
            return True
        if self.is_file():
            raise NotADirectoryError(
                f"'is_empty' failed, '{self}' is not a dir.")
        return not first(self.iterdir(), where=lambda x: not is_sys_file(x))

    @lazy
    def is_filmroot(self) -> bool:

        # For relative paths, the top path part is considered the filmroot.
        if not self.is_absolute():
            if self.parent == Path('.'):
                self.filmroot = Path(self)
                return True

        # From all objects in x, create a list of years if not None
        def get_years(x): return [y for y in [
            o._year for o in x] if y is not None]

        # If it's not a terminus, it cannot be a filmroot.
        # Terminus criteria:
        # - Not origin, and
        #   - A file, or
        #   - A dir with no subdirs, or only empty ones
        if not self.is_terminus:
            return False

        if self.is_dir():

            if self.is_empty:
                return False

            if self.is_branch or (self.is_origin and not self == self.origin):
                return False

            if self._year:
                return True

            if iterlen(self.video_files) > 0 and all_match(
                    get_years(prepend(self, to=self.video_files))):
                return True

        elif self.is_video_file:

            if self.parent.is_branch or self.parent.is_origin:
                return True

            if self.parent._year:
                return False

            if all_match(get_years(
                    prepend(self.parent, to=self.parent.video_files))):
                return False

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
        if not self.is_absolute() and (self.is_video_file or self._year):
            return True

        # If it doesn't exist, all we can do is check it or its parent
        # for a year.
        if not self.exists() and (self.is_video_file
                                  or self._year
                                  or self.parent._year):
            return True

        # It's an empty dir
        if self.is_dir() and self.is_empty:
            return False

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
        if '_origin' not in self.__dict__:
            return Path(self)
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
    def size(self) -> 'Size':
        from fylmlib.operations import Size
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
            return None
        return filter(lambda f: Info.is_video_file(f), self.resolve().rglob("*"))

    @lazy
    def _year(self) -> int:

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

    def setpath(self, new_path: Union[str, Path, 'FilmPath']):
        """Updates the current Path object's path parts
        with that of a new one.

        Args:
            new_path (str or Pathlike): Path to update this one with.
        """

        new_path = Path(new_path)
        self._drv = new_path._drv
        self._root = new_path._root
        self._parts = new_path._parts
        self._pparts = tuple(self._parts)
        self._cached_cparts = self._flavour.casefold_parts(self._parts)
        self._str = new_path.__str__()

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
            return p.suffix.lower() in config.video_exts

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
        def paths_exist(paths: List[Union[str, Path, 'FilmPath']], quiet: bool = False) -> bool:
            """Verified that a list of paths exist on the filesystem.

            Args:
                paths [(str, Path, or FilmPath)]: List of paths to check
                quiet (bool): Do not print an error to the console (default is False)

            Returns:
                bool: True if all paths exist, otherwise false
            """
            failed = [x for x in [Path(p) for p in paths] if not x.exists()]
            for p in failed:
                Console.error(f"{INDENT}'{p}' does not exist.")

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

            while not p1.exists():
                p1 = p1.parent

            while not p2.exists():
                p2 = p2.parent

            return p1.stat().st_dev == p2.stat().st_dev

        @staticmethod
        def will_copy(path: Union[str, Path, 'FilmPath']) -> bool:
            """Returns True if the path will require a copy operation
            when moving.

            Args:
                path (str, Path): Path to check

            Returns:
                bool: True if the path will require copying.
            """
            return (config.always_copy
                    or not Info.is_same_partition(path.src.parent, path.dst))

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

Info = FilmPath.Info
