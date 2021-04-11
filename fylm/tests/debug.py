#!/usr/bin/env python
import os
import pathlib
from pathlib import Path
from typing import Union

class WalkPath(Path):
    
    _flavour = type(Path())._flavour
    
    def __init__(self, *args, dirs: []=None, files: []=None):
        """Initialize WalkPath object.

        Args:
            dirs (list):    Dirs provided by os.walk(), defauls to []
            files (list):   Files provided by os.walk(), defaults to []
        """
        
        super().__init__()
        
        self._dirs: [WalkPath] = list(map(WalkPath, dirs)) if dirs else None
        self._files: [WalkPath] = list(map(WalkPath, files)) if files else None
    
    # @overrides(joinpath)
    def joinpath(self, path) -> 'WalkPath':
        joined = WalkPath(super().joinpath(path))
        self.__dict__ = joined.__dict__.copy()
        return joined
    
    # @overrides(relative_to)
    def relative_to(self, path) -> 'WalkPath':
        rel = WalkPath(super().relative_to(path))
        self.__dict__ = rel.__dict__.copy()
        return rel
        
    # @overrrides(parent)
    @property
    def parent(self) -> 'WalkPath':
        return WalkPath(super().parent)
    
    # @overrrides(parents)
    @property
    def parents(self) -> ['WalkPath']:
        return [WalkPath(p) for p in super().parents]
    
    @property
    def dirs(self) -> ['Walkpath']:
        self._dirs = (self._dirs or 
                      [WalkPath(d) for d in self.iterdir() if d.is_dir()] 
                      if self.is_absolute() and self.is_dir() else [])
        return self._dirs
    
    @property
    def files(self) -> ['Walkpath']:
        self._files = (self._files or 
                       [WalkPath(f) for f in self.iterdir() if f.is_file()] 
                       if self.is_absolute() and self.is_dir() else [])
        return self._files
    
    @property
    def is_terminus(self) -> bool:
        return self.is_file() or not self.dirs
        
class Find:

    @staticmethod
    def deep(path: Union[str, Path, 'WalkPath'], 
             hide_sys_files=True) -> ['WalkPath']:
        """Deeply search the specified path and return all files and dirs 
        (using os.walk), mapped to WalkPath objects that maintain a 
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
        
        if Path(path).is_file(): 
            return [WalkPath(path)]
        
        for root,dirs,files in os.walk(WalkPath(path)):
            
            if hide_sys_files:
                files = filter(lambda f: 
                    not f.startswith('.')
                    and not f.lower() == 'thumbs.db', files)
            
            this = WalkPath(root)
            
            this._dirs = [this.joinpath(d) for d in dirs]
            this._files = [this.joinpath(f) for f in files]
                        
            dirs = this.dirs
            files = this.files
                        
            yield this
            yield from files
            
    @staticmethod
    def deep_sorted(path: Union[str, Path, 'WalkPath'], 
                    sort_key=lambda p: str(p).lower(),
                    hide_sys_files=True) -> ['WalkPath']:
        yield from sorted(Find.deep(root, 
                                    hide_sys_files=hide_sys_files), 
                          key=sort_key)

root = WalkPath('fylm/tests/files/#new').resolve()
for p in Find.deep_sorted(root):
    print(p, 
          p.exists(), 
          len(p.dirs) if len(p.dirs) > 10 else p.dirs, 
          len(p.files),
          p.parent.name, 
          len(p.parent.dirs))
    