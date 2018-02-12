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
import sys
import pytest

from fylmlib.config import config
import fylmlib.operations as ops
import conftest
import make

# @pytest.mark.skip()
class TestDirOperations(object):

    @pytest.mark.xfail(raises=IOError)
    def test_verify_paths_exist(self):

        if sys.platform == "win32":
            ops.dirops.verify_paths_exist(['C:\\__THERE_IS_NO_SPOON__'])
        else:
            ops.dirops.verify_paths_exist(['/__THERE_IS_NO_SPOON__'])

    @pytest.mark.skip(reason='Cannot reliably test multiple partitions/mount points')
    def test_is_same_partition(self):
        pass

    def test_get_existing_films(self):


        config.duplicate_checking.enabled = True
        assert(config.duplicate_checking.enabled is True)

        raw_files = {
            '2160p': 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.DTS.mp4',
            '1080p': 'Rogue.One.A.Star.Wars.Story.2016.1080p.DTS.x264-group.mkv',
            '720p': 'Rogue.One.A.Star.Wars.Story.2016.720p.DTS.x264-group.mkv',
            'SD': 'Rogue.One.A.Star.Wars.Story.2016.avi'
        }

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_dst_paths['2160p'], raw_files['2160p']), 52234 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], raw_files['1080p']), 11234 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], raw_files['720p']), 6590 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], raw_files['SD']), 723 * make.mb)

        print(ops.dirops.get_existing_films(conftest.films_dst_paths))
        assert(len(ops.dirops.get_existing_films(conftest.films_dst_paths)) == 4)

    def test_get_new_films(self):

        conftest.setup()

        all_films = ops.dirops.get_new_films(conftest.films_src_path)
        valid_films = filter(lambda film: not film.should_ignore, all_films)

        # Assert that we're getting the expected number of films.
        assert(len(all_films) == len(conftest.all_test_films))

        # Assert that we're getting the expected number of valid films.
        assert(len(valid_films) == len(conftest.expected))