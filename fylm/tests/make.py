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

from __future__ import unicode_literals

import os
import io
import shutil
import json

class _MockFilm:
    def __init__(self, expected_title, expected_id):
        self.expected_title = expected_title
        self.expected_id = expected_id

def make(json_path, files_path):

    tests_map = []

    root_dir = files_path

    # Clean up first
    try:
        shutil.rmtree(root_dir)
    except:
        pass

    try:
        os.makedirs(root_dir)
    except:
        pass

    with io.open(json_path, mode="r", encoding="utf-8") as json_data:
        test_films = json.load(json_data)
        for test_film in test_films['files']:
            if 'dir' in test_film:
                os.makedirs(os.path.join(root_dir, test_film['dir']))
            if 'files' in test_film:
                for file in test_film['files']:
                    parent_dir = test_film['dir'] if 'dir' in test_film else ''
                    open(os.path.join(root_dir, parent_dir, file), 'a').close()
            tmdb_id = test_film['tmdb_id'] if 'tmdb_id' in test_film else None
            title = test_film['title'] if 'title' in test_film else None
            tests_map.append(_MockFilm(title, tmdb_id))

        return tests_map