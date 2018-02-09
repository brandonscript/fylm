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

from __future__ import unicode_literals, print_function, absolute_import

import os
import re
import sys
import io
import random
import time
import json
import shutil
import pytest

# Add the cwd to the path so we can load fylmlib modules and fylm app.
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from fylmlib.config import config
import fylmlib.operations as ops
from make import make_files

# Set config to quiet so that TravisCI doesn't fail attempting to send
# notifications to 127.0.0.1.
config.quiet = True
# config.no_console = True

# TravisCI uses environment variables to keep keys secure. Map the TMDB_KEY
# if it is available.
if os.environ.get('TMDB_KEY') is not None: 
    config['tmdb']['key'] = os.environ.get('TMDB_KEY')

# Helper functions.
def lookup_sync(film):
    try:
        film.search_tmdb()

    # TODO: Figure out which HTTPError is actually being thrown, and 
    # which module it belongs to so we can inspect the X-Rate-Limit
    # header.
    except Exception:
        time.sleep(5.0)
        film.search_tmdb()

    # TODO: A more graceful way of handling rate limiting in TravisCI.
    if os.environ.get('TMDB_KEY') is not None:
        time.sleep(0.5)

def full_path(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)

# Configure source and destination paths for test files.
films_src_path = full_path('files/#new/')

# Film destination map
films_dst_paths = {
    '2160p': full_path('files/4K'),
    '1080p': full_path('files/HD'),
    '720p': full_path('files/HD'),
    'SD': full_path('files/SD'),
    'default': full_path('files/SD')
}

# Make test files.
make_result = make_files('files_mini.json', films_src_path)

# If you change the number of valid films in the json map,
# update valid_films_count to match.
tests_map = make_result[0]
valid_films_count = make_result[1]

# Load films and filter them into valid films.
films = ops.dirops.get_new_films(films_src_path)
valid_films = filter(lambda film: not film.should_ignore, films)

for _, dr in films_dst_paths.items():
    try:
        shutil.rmtree(dr)
    except Exception:
        pass
    ops.dirops.create_deep(dr)

