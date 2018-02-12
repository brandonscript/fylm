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

import pytest

from fylmlib.config import config
import fylm
import conftest

# Overwrite the app's pre-loaded config.
fylm.config = config

# @pytest.mark.skip()
class TestApp(object):
    """Tests E2E application functionality"""

    def test_app_tmdb_disabled(self):

        conftest.setup()

        fylm.config.quiet = True
        fylm.config.test = False
        fylm.config.use_folders = True
        fylm.config.tmdb.enabled = False

        # Execute
        fylm.main()

        moved_films = conftest.moved_films()
        assert(len(moved_films) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        for expected in conftest.expected_no_lookup:
            expected_path = conftest.expected_path(expected, folder=True).lower()
            assert(expected_path in [m.lower() for m in moved_films])

        config.reload()
        fylm.config = config

    # @pytest.mark.skip(reason="Slow")
    @pytest.mark.slow
    def test_app_use_folders_true(self):

        conftest.setup()

        fylm.config.quiet = True
        fylm.config.test = False
        fylm.config.use_folders = True
        fylm.config.tmdb.enabled = True

        # Execute
        fylm.main()

        moved_films = conftest.moved_films()

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        for expected in conftest.expected:
            expected_path = conftest.expected_path(expected, folder=True)
            assert(expected_path in moved_films)

    # @pytest.mark.skip(reason="Slow")
    @pytest.mark.slow
    def test_app_use_folders_false(self):

        conftest.setup()
        
        fylm.config.quiet = True
        fylm.config.test = False
        fylm.config.use_folders = False
        fylm.config.tmdb.enabled = True

        # Execute
        fylm.main()

        moved_films = conftest.moved_films()

        # Assert that all of the films were moved successfully into the correct destination folders.
        for expected in conftest.expected:
            expected_path = conftest.expected_path(expected, folder=False)
            assert(expected_path in moved_films)

        fylm.config.use_folders = True