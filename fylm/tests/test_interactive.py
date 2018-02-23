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

import pytest

from fylmlib.config import config
import fylm
import conftest
import make

# @pytest.mark.skip()
class TestInteractive(object):

    def test_happy_path(self):

        fylm.config.interactive = True
        fylm.config.mock_input = ['N', 'Bridget Jones The Edge of Reason', 1]

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