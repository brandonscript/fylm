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

import os
import io
import re
import shutil
import json
import random

class _MockFilm:
    def __init__(self, expected_title, expected_id):
        self.expected_title = expected_title
        self.expected_id = expected_id

def make_files(json_path, files_path):

    tests_map = []

    search_dir = os.path.join(os.path.dirname(__file__), files_path)
    json_path = os.path.join(os.path.dirname(__file__), os.path.basename(json_path))

    mb = 1024 * 1024
    gb = mb * 1024

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
        test_films = json.load(json_data)
        for test_film in test_films['files']:
            if 'dir' in test_film:
                os.makedirs(os.path.join(search_dir, test_film['dir']))
            if 'files' in test_film:
                for file in test_film['files']:
                    parent_dir = test_film['dir'] if 'dir' in test_film else ''
                    file = os.path.join(search_dir, parent_dir, file)
                    
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
                    f = open(file, 'wb')
                    f.seek(size)
                    f.write('\0')
                    f.close()
            tmdb_id = test_film['tmdb_id'] if 'tmdb_id' in test_film else None
            title = test_film['title'] if 'title' in test_film else None
            tests_map.append(_MockFilm(title, tmdb_id))

        return (tests_map, test_films['valid_films'])

if __name__ == '__main__':
    make_files('files.json', 'files/#new/')