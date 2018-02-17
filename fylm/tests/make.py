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

from __future__ import unicode_literals, print_function
from builtins import *

import os
import io
import re
import shutil
import json
import random

kb = 1024
mb = kb * 1024
gb = mb * 1024

# Special Travis calculations that reduce file sizes by / 1024
kb_t = kb
mb_t = mb
gb_t = gb

# For tests on Travis, miniaturize filesizes.
if os.environ.get('TRAVIS') is not None:
    kb_t = 1
    mb_t = kb_t * 1024
    gb_t = mb_t * 1024

class MockFilm:
    def __init__(self, expected_title, expected_id, acceptable_names):
        self.expected_title = expected_title
        self.expected_id = expected_id
        self.acceptable_names = acceptable_names

class MakeFilmsResult:
    def __init__(self, all_test_films, expected, expected_no_lookup, ignored):
        self.all_test_films = all_test_films
        self.expected = expected
        self.expected_no_lookup = expected_no_lookup
        self.ignored = ignored

def make_mock_file(path, size):
    # Create an empty file that appears to the system to be the size of `size`.
    try:
        os.makedirs(os.path.dirname(path))
    except Exception:
        pass

    f = open(path, 'wb')
    f.seek(size)
    f.write(b'\0')
    f.close()

def make_mock_files(json_path, files_path):
    global gb
    global mb

    all_test_films = []
    expected = []
    expected_no_lookup = []
    ignored = []

    search_dir = os.path.join(os.path.dirname(__file__), files_path)
    json_path = os.path.join(os.path.dirname(__file__), os.path.basename(json_path))

    # Clean up first
    try:
        shutil.rmtree(search_dir)
    except Exception:
        pass

    try:
        os.makedirs(search_dir)
    except Exception:
        pass

    with io.open(json_path, mode="r", encoding="utf-8") as json_data:
        test_films = json.load(json_data)['test_films']
        for test_film in test_films:
            if 'dir' in test_film:
                os.makedirs(os.path.join(search_dir, test_film['dir']))
            
            acceptable_names = []

            for tf in test_film['files']:
                parent_dir = test_film['dir'] if 'dir' in test_film else ''
                file = os.path.join(search_dir, parent_dir, tf['filename'])
                if 'expect_no_lookup' in tf:
                    # Add the expected filename to expected_no_lookup[]:
                    expected_no_lookup.append(tf['expect_no_lookup'])
                    acceptable_names.append(tf['expect_no_lookup'])
                if 'expect' in tf and tf['expect'] is not None:
                    # Add the expected filename to expected[] and ..no_lookup[]:
                    expected.append(tf['expect'])
                    expected_no_lookup.append(tf['expect'])
                    acceptable_names.append(tf['expect'])
                else:
                    ignored.append(tf['filename'])
                
                size_2160p = random.randrange(int(35 * gb), int(55 * gb))
                size_1080p = random.randrange(int(7 * gb), int(15 * gb))
                size_720p = random.randrange(int(4 * gb), int(8 * gb))
                size_sd = random.randrange(int(750 * mb), int(1300 * mb))
                size_sample = random.randrange(10 * mb, 50 * mb)

                if (re.search(re.compile(r'\bsample', re.I), file) 
                    or os.path.basename(file) == 'ETRG.mp4'):
                    size = size_sample
                elif re.search(re.compile(r'720p?', re.I), file):
                    size = size_720p
                elif re.search(re.compile(r'1080p?', re.I), file):
                    size = size_1080p
                elif re.search(re.compile(r'(2160p?|\b4K)', re.I), file):
                    size = size_2160p
                elif os.path.splitext(file)[1] in ['.avi', '.mp4']:
                    size = size_sd
                else:
                    size = size_1080p
                # Create an empty file that appears to the system to be 
                # a random size akin to the qulity of the film.
                make_mock_file(file, size)
            tmdb_id = test_film['tmdb_id'] if 'tmdb_id' in test_film else None
            title = test_film['title'] if 'title' in test_film else None
            all_test_films.append(MockFilm(title, tmdb_id, acceptable_names))

        return MakeFilmsResult(all_test_films, expected, expected_no_lookup, ignored)

if __name__ == '__main__':
    make_mock_files('files.json', 'files/#new/')