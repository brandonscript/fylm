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
import time
from multiprocessing import Process, Pipe

import pytest

import fylmlib.config as config
import fylmlib.operations as ops
import conftest
import make

src = os.path.join(
    conftest.films_src_path,
    'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

dst = os.path.join(
    conftest.films_dst_paths['1080p'], 
    'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) Bluray-1080p Proper.mkv')

expected_size = 7354 * make.mb_t

def async_safe_copy(conn, *args):
    copy = ops.fileops.safe_move(*args)
    conn.send(copy)
    conn.close()

# @pytest.mark.skip()
class TestMove(object):

    def test_basic_move(self):
        
        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_dst_exists_no_replace(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        make.make_mock_file(dst, expected_size - 220)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        move = ops.fileops.safe_move(src, dst)

        assert(move is False)
        assert(os.path.exists(src))
        assert(os.path.exists(dst))

    def test_dst_exists_no_overwrite_no_replace(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        make.make_mock_file(dst, expected_size - 220)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)
        config.overwrite_existing = False
        assert(config.overwrite_existing is False)

        move = ops.fileops.safe_move(src, dst)

        assert(move is False)
        assert(os.path.exists(src))
        assert(os.path.exists(dst))

    def test_dst_exists_overwrite(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        make.make_mock_file(dst, expected_size - 220)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)
        config.overwrite_existing = True
        assert(config.overwrite_existing is True)

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(not os.path.exists(src))
        assert(os.path.exists(dst))

    def test_dst_exists_replace(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        make.make_mock_file(dst, expected_size - 220)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)
        config.overwrite_existing = False
        assert(config.overwrite_existing is False)

        move = ops.fileops.safe_move(src, dst)

        assert(move is False)
        assert(os.path.exists(src))
        assert(os.path.exists(dst))

    def test_test_enabled(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        assert(os.path.exists(src))
        assert(not os.path.exists(dst))

        config.safe_copy = False
        assert(config.safe_copy is False)

        config.test = True
        assert(config.test is True)

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(src))
        assert(not os.path.exists(dst))

    def test_src_eq_dst(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        move = ops.fileops.safe_move(src, src)

        assert(move is False)
        assert(os.path.exists(src))

    def test_safe_copy(self):

        expected_size = 75 * make.mb
        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)
        
        config.test = False
        assert(config.test is False)
        config.safe_copy = True
        assert(config.safe_copy is True)

        parent_conn, child_conn = Pipe()
        p = Process(target=async_safe_copy, args=(child_conn, src, dst,))
        p.start()
        # This is a bit of a hack, but this test requires the file to sufficiently large enough
        # to check that the partial exists before the thread finishes, but it also can't start
        # too soon, so we sleep for 0.1s.
        time.sleep(0.1)
        assert(os.path.exists(f'{dst}.partial~'))
        copy = parent_conn.recv()
        p.join()

        assert(copy is True)
        assert(not os.path.exists(src))
        assert(os.path.exists(dst))

        # Disable safe copy
        config.safe_copy = False
        assert(config.safe_copy is False)

    @pytest.mark.xfail(raises=OSError)
    def test_not_path_exists(self):
        conftest.cleanup_all()
        conftest.make_empty_dirs()

        src = '_DOES_NOT_EXIST_'
        dst = '_DOES_NOT_MATTER_'

        move = ops.fileops.safe_move(src, dst)

        assert(move is False)