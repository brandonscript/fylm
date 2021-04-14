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

# For tests on Travis, miniaturize filesizes.
# To force this in local tests, do:
#   export TRAVIS=true
#   export TMDB_KEY={key}
# To unset these:
#   unset TRAVIS

kb = 1 if os.environ.get('TRAVIS') is not None else 1024
mb = kb * 1024
gb = mb * 1024

class MockFilm:
    def __init__(self, test_film):
        self.tmdb_id = test_film["tmdb_id"] if 'tmdb_id' in test_film else None
        self.make = test_film["make"]
        self.expect = []
        self.expect_no_lookup = []
        self.sizes = []

        size_2160p = random.randrange(int(18 * gb), int(26 * gb))
        size_1080p = random.randrange(int(7 * gb), int(15 * gb))
        size_720p = random.randrange(int(3 * gb), int(7 * gb))
        size_sd = random.randrange(int(750 * mb), int(1300 * mb))
        size_sample = random.randrange(10 * mb, 50 * mb)


        if 'expect' in test_film and test_film['expect'] is not None:
            self.expect = test_film['expect']
            self.expect_no_lookup = test_film['expect']
        if 'expect_no_lookup' in test_film and test_film['expect_no_lookup'] is not None:
            self.expect_no_lookup = test_film['expect_no_lookup']

        for file in test_film["make"]:
            if (re.search(re.compile(r'\bsample', re.I), file)
                or os.path.basename(file) == 'junk.mp4'):
                self.sizes.append(size_sample)
            elif re.search(re.compile(r'\b720p?\b', re.I), file):
                self.sizes.append(size_720p)
            elif re.search(re.compile(r'\b1080p?\b', re.I), file):
                self.sizes.append(size_1080p)
            elif re.search(re.compile(r'\b(2160p?|\b4K)\b', re.I), file):
                self.sizes.append(size_2160p)
            elif os.path.splitext(file)[1] in ['.avi', '.mp4']:
                self.sizes.append(size_sd)
            else:
                self.sizes.append(size_1080p)

    @property
    def acceptable_names(self):
        if self.expect_no_lookup is not None:
            return self.expect + self.expect_no_lookup
        elif self.expect is not None:
            return self.expect
        else:
            return []
            

class MakeFilmsResult:
    def __init__(self, good, bad):
        self.all = good + bad
        self.good = good
        self.bad = bad

def make_mock_file(path, size):
    
    Path(os.path.dirname(path)).mkdir(parents=True, exist_ok=True)
    
    # Force size to be an integer
    size = int(round(size))

    f = open(path, 'wb')
    f.seek(size)
    f.write(b'\0')
    f.close()

def make_all_mock_files(json_path, files_path):
    global gb
    global mb

    good = []
    bad = []

    search_dir = os.path.join(os.path.dirname(__file__), files_path)
    json_path = os.path.join(os.path.dirname(__file__), os.path.basename(json_path))

    # Clean up first
    try:
        shutil.rmtree(search_dir)
    except Exception:
        pass

    with io.open(json_path, mode="r", encoding="utf-8") as json_data:
        test_films = list(sorted(json.load(json_data)[
                          'test_films'], key=lambda k: re.sub(re.compile(r'^the\W*', re.I), '', k['make'][0].lower())))

        for tf in [MockFilm(f) for f in test_films if 'skip' not in f]:

            for i, file in enumerate(tf.make):
                file = os.path.join(search_dir, file)
                make_mock_file(file, tf.sizes[i])

            if len(tf.expect) > 0 and tf.tmdb_id is not None:
                good.append(tf)
            else:
                bad.append(tf)
                            
        return MakeFilmsResult(good, bad)

if __name__ == '__main__':
    make_all_mock_files('files.json', 'files/#new/')
