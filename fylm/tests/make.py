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

import os
import io
import re
import shutil
import json
import random
from pathlib import Path
import conftest
from typing import Union

# For tests on Travis, miniaturize filesizes.
# To force this in local tests, do:
#   export TRAVIS=true
#   export TMDB_KEY={key}
# To unset these:
#   unset TRAVIS

KB = 1 if os.environ.get('TRAVIS') is not None else 1024
MB = KB * 1024
GB = MB * 1024

class MockFilm:
    def __init__(self, test_film):
        
        self.tmdb_id = test_film["tmdb_id"] if 'tmdb_id' in test_film else None
        self.make = test_film["make"]
        self.expect = []
        self.expect_no_lookup = []
        self.sizes = []

        if 'expect' in test_film and test_film['expect'] is not None:
            self.expect = test_film['expect']
            self.expect_no_lookup = test_film['expect']
        if 'expect_no_lookup' in test_film and test_film['expect_no_lookup'] is not None:
            self.expect_no_lookup = test_film['expect_no_lookup']

        for f in test_film["make"]:
            self.sizes.append(Make.size(f))

    @property
    def acceptable_names(self):
        if self.expect_no_lookup is not None:
            return self.expect + self.expect_no_lookup
        elif self.expect is not None:
            return self.expect
        else:
            return []
            

class MakeFilmsResult:
    def __init__(self, good: ['MockFilm'], bad: ['MockFilm']):
        self.all: ['MockFilm'] = good + bad
        self.good: ['MockFilm'] = good
        self.bad: ['MockFilm'] = bad
        
    @property
    def all_files(self) -> ['MockFilm']:
        return sorted([x for m in self.all for x in m.make if x],
                       key=lambda x: Path(x).name.lower())
        
    def get(self, lst='good', key='expect', folders=True) -> ([], []):
        expected = []
        existing = []
        
        for tf in getattr(self, lst):
            ex = getattr(tf, key)
            valid_paths = [p for p in ex if p is not None]
            for path in valid_paths:
                desired_path = conftest.desired_path(path, tf, folders=folders)
                if desired_path:
                    expected.append(desired_path)

        for t in conftest.dst_paths.values():
            for r, _, files in os.walk(t):
                for f in list(filter(lambda x: not x.startswith('.'), files)):
                    existing.append(os.path.join(r, f))

        # Need to remove identical duplicates, as only one will exist on the filesystem
        return (list(set(existing)), list(set(expected)))

class Make:

    @staticmethod
    def size(path: Union[str, Path]) -> int:

        global KB
        global MB
        global GB

        path = Path(path)
        
        if path.suffix.lower() in ['.mkv', '.mp4', '.m4v', '.avi']:

            # junk file
            if 'sample' in str(path).lower() or 'junk' in str(path).lower():
                return random.randrange(10 * MB, 50 * MB)
            
            # 720p mkv
            elif re.search(r'\b720p?\b', str(path), re.I):
                return random.randrange(int(3 * GB), int(7 * GB))
            
            # 1080p mkv
            elif re.search(r'\b1080p?\b', str(path), re.I):
                return random.randrange(int(7 * GB), int(15 * GB))
            
            # 4K mkv
            elif re.search(r'\b(2160p?|4k)\b', str(path), re.I):
                return random.randrange(int(18 * GB), int(26 * GB))
            
            # .avi or SD mkv
            else:
                return random.randrange(int(750 * MB), int(1300 * MB))
        
        # Something else
        else:
            return random.randrange(int(5 * KB), int(150 * KB))
    
    @staticmethod
    def empty_dirs():
        paths = [conftest.src_path, conftest.src_path2] + list(set(conftest.dst_paths.values()))
        [Path(dr).mkdir(parents=True, exist_ok=True) for dr in paths]

    @staticmethod
    def mock_file(path, size=0):
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        # Force size to be an integer
        size = int(round(size)) if size and size > 0 else Make.size(path)

        f = open(path, 'wb')
        f.seek(size-1)
        f.write(b'\0')
        f.close()
        
    @staticmethod
    def mock_files(*paths: Union[str, list]):
        global MB
        
        for f in paths:
            (path, size) = f if type(f) is tuple else (f, 0)
            assert(path.is_absolute())
            Make.mock_file(path, size * MB)

    @staticmethod
    def mock_src_files(*files: Union[str, list], src_path: str = None):
        global MB
        
        src_path = src_path or conftest.src_path
        for p in [Path(f) for f in files]:
            assert(not p.is_absolute())
            (name, size) = p if type(p) is tuple else (p, 0)
            Make.mock_file(src_path / name, size * MB)
    
    @staticmethod
    def mock_dst_files(files: dict):
        global MB
        
        for k, v in files.items():
            (name, size) = v if type(v) is tuple else (v, 0)
            Make.mock_file(conftest.dst_paths[k] / name, size * MB)

    @staticmethod
    def all_mock_files() -> MakeFilmsResult:
        good: ['MockFilm'] = []
        bad: ['MockFilm'] = []

        # Clean up first
        try:
            shutil.rmtree(conftest.src_path)
        except Exception:
            pass

        with io.open(conftest.files_root / 'files.json', mode="r", encoding="utf-8") as json_data:
            test_films = sorted(json.load(json_data)['test_films'], 
                                key=lambda k: re.sub(r'^the\W*', '', k['make'][0].lower(), flags=re.I))

            for tf in [MockFilm(f) for f in test_films if 'skip' not in f]:

                for i, file in enumerate(tf.make):
                    Make.mock_file(Path(conftest.src_path) / file, tf.sizes[i])

                if len(tf.expect) > 0 and tf.tmdb_id is not None:
                    good.append(tf)
                else:
                    bad.append(tf)
                                
            return MakeFilmsResult(good, bad)

# if __name__ == '__main__':
#     make_all_mock_files('files.json', 'files/#new/')
