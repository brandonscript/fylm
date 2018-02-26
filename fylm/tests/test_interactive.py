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

try:
    from math import isclose
except ImportError:
    from pytest import approx
    def isclose(a, b, abs_tol=0.0):
        return a == approx(b, abs_tol)

import pytest

import fylmlib.config as config
import fylmlib.operations as ops
import fylm
import conftest
import make

# @pytest.mark.skip()
class TestInteractive(object):

    def test_lookup_success(self):

        conftest.setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.mock_input = ['N', 'Bridget Jones The Edge of Reason', 1]
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)

        f = os.path.join(conftest.films_src_path, 'Bridget Jones The Edge of Reason 1080p/Bridget Jones The Edge of Reason 1080p.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Bridget Jones The Edge of Reason (2004) 1080p/Bridget Jones The Edge of Reason (2004) 1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 7354 * make.mb_t)

        assert(os.path.exists(f))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))

        config.interactive = False
        fylm.config.mock_input = None

    def test_duplicates(self):

        conftest.setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicate_checking.enabled = True
        fylm.config.mock_input = ['Y', 'R']
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicate_checking.enabled is True)

        f = os.path.join(conftest.films_src_path, 'Die Hard (1988) 1080p/Die Hard (1988) 1080p.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988) 1080p/Die Hard (1988) 1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 7354 * make.mb_t)
        make.make_mock_file(xf, 9114 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there are 3 duplicates
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))
        assert(isclose(ops.size(xf), 7354 * make.mb_t, abs_tol=10))

        config.interactive = False
        fylm.config.mock_input = None    