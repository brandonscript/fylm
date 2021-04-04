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

from __future__ import unicode_literals, print_function, absolute_import
from builtins import *

import os
import sys
import shutil
import itertools
from pathlib import Path
from datetime import timedelta

import pytest
import requests_cache

# Add the cwd to the path so we can load fylmlib modules and fylm app.
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import fylm
import fylmlib.config as config
from fylmlib.parser import parser
import fylmlib.operations as ops
from make import make_all_mock_files, MakeFilmsResult

if config.cache:
    requests_cache.install_cache(f'.cache.fylm_test_py{sys.version_info[0]}', expire_after=timedelta(hours=120))
    requests_cache.core.remove_expired_responses()

# Set the filename that contains test files
test_files = 'files.json'

def full_path(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path).strip()

# Configure source and destination paths for test files.
films_src_path = full_path('files/#new')
films_src_path2 = full_path('files/#two')

# Film destination map
films_dst_paths = {
    '2160p': full_path('files/4K'),
    '1080p': full_path('files/HD'),
    '720p': full_path('files/HD'),
    'SD': full_path('files/SD'),
    'default': full_path('files/SD')
}

made: MakeFilmsResult

all_films = []
valid_films = []

@pytest.fixture(scope="session", autouse=True)
def setup():
    _setup()

def _setup():
    global made
    global all_films
    global valid_films
    # global films_src_path
    # global films_dst_paths

    fylm.config.reload()

    cleanup_all()

    make_empty_dirs()

    made = make_all_mock_files(test_files, films_src_path)
    
    # Debugging
    fylm.config.debug = False

    # Console output
    fylm.config.no_console = True

    # Set dirs
    fylm.config.source_dirs = [films_src_path]
    fylm.config.destination_dirs = films_dst_paths

    # Set default rename mask
    fylm.config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
    fylm.config.rename_pattern.folder = r'{title} {(year)}'

    # Load films and filter them into valid films.
    all_films = ops.dirops.get_new_films([films_src_path])
    valid_films = list(filter(lambda film: not film.should_ignore, all_films))

    if os.environ.get('DEBUG') is not None: 
        fylm.config.debug = True if os.environ.get('DEBUG') == 'True' else False

    # Set quiet to suppress external notifications
    fylm.config.quiet = True

def make_empty_dirs():
    global films_src_path
    global films_src_path2
    global films_dst_paths

    paths = [films_src_path, films_src_path2] + list(set(films_dst_paths.values()))

    [Path(dr).mkdir(parents=True, exist_ok=True) for dr in paths]

def cleanup_src_files():
    global films_src_path
    global films_src_path2

    for o in os.listdir(films_src_path).extend(os.listdir(films_src_path2)):
        path = os.path.join(films_src_path, o)
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path): 
                shutil.rmtree(path)
        except Exception:
            pass

def cleanup_all():
    global films_src_path
    global films_src_path2
    global films_dst_paths

    try:
        shutil.rmtree(films_src_path)
        shutil.rmtree(films_src_path2)
    except Exception:
        pass

    for _, dr in films_dst_paths.items():
        try:
            shutil.rmtree(dr)
        except Exception:
            pass

def moved_films():
    global films_dst_paths

    return sorted(list(set(itertools.chain.from_iterable(
        [ops.dirops.get_valid_files(dr) for _, dr in list(set(films_dst_paths.items()))]
    ))))

def desired_path(path, test_film, folder=True):
    assert(test_film.make is not None and path is not None)
    resolution = parser.get_resolution(test_film.make[0])
    return os.path.join(config.destination_dirs[resolution or 'SD'], path if folder else os.path.basename(path))

# Skip cleanup to manually inspect test results
def pytest_sessionfinish(session, exitstatus):
    return
    cleanup_all()
