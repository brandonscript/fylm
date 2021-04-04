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

import pytest
import os
import itertools
from timeit import default_timer as timer

import fylm
import fylmlib.config as config
from fylmlib.film import Film
import conftest

# Overwrite the app's pre-loaded config.
fylm.config = config

# @pytest.mark.skip()
class TestApp(object):
    """Integration tests for application functionality"""

    def test_app_tmdb_disabled(self):

        conftest._setup()

        fylm.config.test = False
        fylm.config.use_folders = True
        fylm.config.tmdb.enabled = False
        assert(fylm.config.test is False)
        assert(fylm.config.use_folders is True)
        assert(fylm.config.tmdb.enabled is False)

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(conftest.made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (moved, expected) = get('expect_no_lookup')
        for desired_path in expected:
            assert(os.path.exists(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

        
    # @pytest.mark.skip(reason="Slow")
    def test_app_use_folders_true(self):

        conftest._setup()

        fylm.config.test = False
        fylm.config.use_folders = True
        fylm.config.tmdb.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.use_folders is True)
        assert(fylm.config.tmdb.enabled is True)

        # fylm.config.debug = True

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(conftest.made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (moved, expected) = get('expect')
        for desired_path in expected:
            assert(os.path.exists(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

    # @pytest.mark.skip(reason="Slow")
    def test_app_use_folders_false(self):

        conftest._setup()
        
        fylm.config.test = False
        fylm.config.use_folders = False
        fylm.config.tmdb.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.use_folders is False)
        assert(fylm.config.tmdb.enabled is True)

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(conftest.made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders.
        (moved, expected) = get('expect', folders=False)
        for desired_path in expected:
            assert(os.path.exists(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

        fylm.config.use_folders = True
        assert(fylm.config.use_folders is True)

def get(key, folders=True) -> ([], []):
    expected = []
    moved = []
    # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
    for tfilm in conftest.made.good:
        ex = tfilm.expect if key == 'expect' else tfilm.expect_no_lookup
        valid_paths = [p for p in ex if p is not None]
        for path in valid_paths:
            desired_path = conftest.desired_path(path, tfilm, folder=folders)
            if desired_path:
                expected.append(desired_path)

    for t in conftest.films_dst_paths.values():
        for r, _, files in os.walk(t):
            for f in list(filter(lambda x: not x.startswith('.'), files)):
                moved.append(os.path.join(r, f))

    # Need to remove identical duplicates, as only one will exist on the filesystem
    return (list(set(moved)), list(set(expected)))