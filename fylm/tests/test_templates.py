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

expected_size = 7354 * make.mb_t

def async_safe_copy(conn, *args):
    copy = ops.fileops.safe_move(*args)
    conn.send(copy)
    conn.close()

# @pytest.mark.skip()
class TestTemplates(object):

    def test_title_year(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016).mkv')

        config.rename_pattern.file = r'{title} {(year)}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_the_year(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Last Starfighter, The (1984)/Last Starfighter, The (1984).mkv')

        config.rename_pattern.file = r'{title-the} {(year)}'
        config.rename_pattern.folder: r'{title-the} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_hyphen_edition(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/Last Starfighter (1984) - 25th Anniversary Edition.mkv')

        config.rename_pattern.file = r'{title} {(year)}{ - edition}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_sqbk_edition(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/Last Starfighter (1984) [25th Anniversary Edition].mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_noedition_quality(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-1080p.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_noedition_quality_full(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_folder_title_year_quality_full(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016) Bluray-1080p Proper/Rogue One A Star Wars Story (2016) Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder: r'{title} {(year)} {[edition]} {quality-full}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_unknown_media(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.DTS.x264-DON.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) 1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))

    def test_title_year_sqbk_edition_quality_full(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.PROPER.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.PROPER.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(src, expected_size)

        config.safe_copy = False
        assert(config.safe_copy is False)
        
        config.test = False
        assert(config.test is False)

        dst = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/Last Starfighter (1984) [25th Anniversary Edition] Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]}'
        config.rename_pattern.folder: r'{title} {(year)}'

        move = ops.fileops.safe_move(src, dst)

        assert(move is True)
        assert(os.path.exists(dst))