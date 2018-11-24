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
from builtins import *

import os
import sys
import shutil
import itertools
from datetime import timedelta

import pytest
import requests_cache
requests_cache.install_cache(f'.cache.fylm_test_py{sys.version_info[0]}', expire_after=timedelta(hours=120))
requests_cache.core.remove_expired_responses()

# Add the cwd to the path so we can load fylmlib modules and fylm app.
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


import fylm
import fylmlib.config as config
from fylmlib.parser import parser
import fylmlib.operations as ops
from make import make_mock_files

# Set the filename that contains test files
test_files = 'files.json'
if os.environ.get('TRAVIS') is not None:
    test_files = 'files_no_unicode.json'

def full_path(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path).strip()

# Configure source and destination paths for test files.
films_src_path = full_path('files/#new')

# Film destination map
films_dst_paths = {
    '2160p': full_path('files/4K'),
    '1080p': full_path('files/HD'),
    '720p': full_path('files/HD'),
    'SD': full_path('files/SD'),
    'default': full_path('files/SD')
}

all_test_films = []
expected = []
expected_no_lookup = []
ignored = []

films = []
valid_films = []

@pytest.fixture(scope="session", autouse=True)
def setup():
    global all_test_films
    global expected
    global ignored
    global films
    global valid_films
    global films_src_path
    global films_dst_paths

    config.reload()

    cleanup_all()

    make_empty_dirs()

    make_result = make_mock_files(test_files, films_src_path)

    all_test_films = make_result.all_test_films
    expected = make_result.expected
    expected_no_lookup = make_result.expected_no_lookup
    ignored = make_result.ignored

    # Set dirs
    config.source_dirs = [films_src_path]
    config.destination_dirs = films_dst_paths

    # Load films and filter them into valid films.
    films = ops.dirops.get_new_films([films_src_path])
    valid_films = list(filter(lambda film: not film.should_ignore, films))

    if os.environ.get('DEBUG') is not None: 
        config.debug = True if os.environ.get('DEBUG') == 'True' else False

    # Set quiet
    config.quiet = True

def make_empty_dirs():
    global films_src_path
    global films_dst_paths

    try:
        os.makedirs(films_src_path)
    except Exception:
        pass

    for _, dr in films_dst_paths.items():
        try:
            os.makedirs(dr)
        except Exception:
            pass

def cleanup_src_files():
    global films_src_path

    for o in os.listdir(films_src_path):
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
    global films_dst_paths

    try:
        shutil.rmtree(films_src_path)
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

def expected_path(expected, folder=True):
    quality = parser.get_quality(expected)
    return os.path.join(config.destination_dirs[quality or 'SD'], os.path.splitext(expected)[0] if folder is True else '', expected)

# Skip cleanup to manually inspect test results
def pytest_sessionfinish(session, exitstatus):
    cleanup_all()