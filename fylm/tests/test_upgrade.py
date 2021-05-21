#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

# This program is bound to the Hippocratic License 2.1
# Full text is available here:
# https: // firstdonoharm.dev/version/2/1/license

# Further to adherence to the Hippocratic Licenese, this program is
# free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. Full text is avaialble here:
# http: // www.gnu.org/licenses

# Where a conflict or dispute would arise between these two licenses, HLv2.1
# shall take precedence.

import os
import time
from multiprocessing import Process, Pipe

import pytest

import fylmlib.config as config
from fylmlib import IO
import conftest
from make import Make, MB

NEW_ROGUE = 'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON'
MOVED_ROGUE = 'Rogue One - A Star Wars Story (2016)'
SRC = conftest.src_path / NEW_ROGUE / f'{NEW_ROGUE}.mkv'
DST = conftest.dst_paths['1080p'] / MOVED_ROGUE / \
    f'{MOVED_ROGUE} Bluray-1080p Proper.mkv'

sm_size = 5354 * MB
big_size = 7354 * MB

def async_always_copy(conn, *args):
    copy = IO.move(*args)
    conn.send(copy)
    conn.close()

# @pytest.mark.skip()
class TestUpgrade(object):

    def test_dst_exists_upgrade_smaller(self):

        Make.mock_file(SRC, big_size)
        Make.mock_file(DST, sm_size)

        config.always_copy = False
        config.duplicates.force_overwrite = False

        # Pass ok_to_upgrade here forcibly, because app logic doesn't determine upgrade eligibility
        move = IO.move(SRC, DST, overwrite=True) 

        assert(move is True)
        assert(not SRC.exists())
        assert(    DST.exists())

    def test_dst_exists_dont_replace_bigger_overwrite_off(self):

        Make.mock_file(SRC, sm_size)
        Make.mock_file(DST, big_size)

        config.always_copy = False
        config.duplicates.force_overwrite = False

        move = IO.move(SRC, DST)

        assert(move is False)
        assert(SRC.exists())
        assert(DST.exists())

    def test_dst_exists_replace_bigger_overwrite_on(self):

        Make.mock_file(SRC, sm_size)
        Make.mock_file(DST, big_size)

        config.always_copy = False
        config.duplicates.force_overwrite = True

        move = IO.move(SRC, DST)

        assert(move is True)
        assert(not SRC.exists())
        assert(DST.exists())

    def test_dst_exists_dont_replace_identical_overwrite_off(self):

        Make.mock_file(SRC, big_size)
        Make.mock_file(DST, big_size)

        config.always_copy = False
        config.duplicates.force_overwrite = False

        move = IO.move(SRC, DST)

        assert(move is False)
        assert(SRC.exists())
        assert(DST.exists())

    def test_dst_exists_replace_identical_overwrite_on(self):

        Make.mock_file(SRC, big_size)
        Make.mock_file(DST, big_size)

        config.always_copy = False
        config.duplicates.force_overwrite = True

        move = IO.move(SRC, DST)

        assert(move is True)
        assert(not SRC.exists())
        assert(    DST.exists())