#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandoncript

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

try:
    from math import isclose
except ImportError:
    from pytest import approx
    def isclose(a, b, abs_tol=0.0):
        return a == approx(b, abs_tol)

import pytest

import fylmlib.config as config
from fylmlib import Film, Find
from fylmlib.tools import *
import fylm
import conftest
from make import Make, MB, GB

SRC = conftest.src_path
DST = conftest.dst_paths
DIE_HARD = 'Die Hard (1988)'
DIE_HARD_NEW = 'Die.Hard.1988.BluRay.1080p.x264-CYaNID3'
BRIDGET = 'Bridget Jones - The Edge of Reason (2004)'

class TestInteractive:

    def test_lookup_success(self):

        config.interactive = True
        config.mock_input = ['N', f'{BRIDGET}', 1]

        f = SRC / f'{BRIDGET} 1080p/{BRIDGET} Bluray-1080p.mkv'
        xf = DST['1080p'] / f'{BRIDGET}/{BRIDGET} Bluray-1080p.mkv'

        Make.mock_file(f, 7354 * MB)

        assert(f.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())

    def test_handle_duplicates_upgrade_same_quality_folder(self):

        config.interactive = True
        config.use_folders = True
        config.mock_input = ['Y', 'U']

        f = SRC / f'{DIE_HARD_NEW}/{DIE_HARD_NEW}.mkv'
        xf = DST['1080p'] / DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'

        Make.mock_files((f, 8233 * MB), 
                        (xf, 7901 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())
        assert(isclose(Film(xf).size.value, 8233 * MB, abs_tol=10))

    def test_handle_duplicates_upgrade_same_quality_file(self):

        # Set up config
        config.interactive = True
        config.use_folders = False
        config.mock_input = ['Y', 'U']

        f = SRC / f'{DIE_HARD} 1080p BluRay.mkv'
        xf = DST['1080p'] / f'{DIE_HARD} Bluray-1080p.mkv'

        Make.mock_files((f, 9576 * MB),
                        (xf, 6441 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())
        assert(isclose(Film(xf).size.value, 9576 * MB, abs_tol=10))

    def test_handle_duplicates_upgrade_lower_quality(self):

        # Set up config
        config.interactive = True
        config.mock_input = ['Y', 'U']

        f = SRC / DIE_HARD_NEW / f'{DIE_HARD_NEW}.mkv'
        xf = DST['720p'] / DIE_HARD / f'{DIE_HARD} WEBDL-720p.mkv'
        nf = DST['1080p'] / DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'

        Make.mock_files((f, 9114 * MB),
                        (xf, 4690 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(not xf.exists())
        assert(nf.exists())
        assert(isclose(Film(nf).size.value, 9114 * MB, abs_tol=10))        

    def test_handle_duplicates_replace_identical(self):

        # Set up config
        config.interactive = True
        config.mock_input = ['Y', 'R']

        f = SRC / '{DIE_HARD} 1080p BluRay.mkv'
        xf = DST['1080p'] / DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'

        Make.mock_files((f, 8133 * MB),
                        (xf, 8133 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())
        assert(isclose(Film(xf).size.value, 8133 * MB, abs_tol=10))

    def test_handle_duplicates_skip(self):

        config.interactive = True
        config.mock_input = ['Y', 'S']

        f = SRC / '{DIE_HARD} 1080p/{DIE_HARD} 1080p.mkv'
        xf = DST['1080p'] / '{DIE_HARD} 1080p/{DIE_HARD} 1080p.mkv'

        Make.mock_files((f, 8854 * MB), 
                        (xf, 9814 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(f.exists())
        assert(xf.exists())

    def test_handle_duplicates_keep_both(self):

        conftest._setup()

        # Set up config
        config.interactive = True
        # Allow 1080p and 720p to be kept
        config.duplicates.upgrade_table['720p'] = []
        config.mock_input = ['Y', 'K']

        n = DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'
        f = SRC / n
        xf = DST['720p'] / DIE_HARD / f'{DIE_HARD} HDTV-720p.mkv'
        nf = DST['1080p'] / n

        Make.mock_files((f, 10223 * MB),
                        (xf, 4690 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())
        assert(nf.exists())
        assert(isclose(Film(xf).size.value, 4690 * MB, abs_tol=10))        
        assert(isclose(Film(nf).size.value, 10223 * MB, abs_tol=10))   

    def test_handle_duplicates_delete_new(self):

        config.interactive = True
        config.mock_input = ['Y', 'D', 'Y']

        f = SRC / DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'
        xf = DST['1080p'] / DIE_HARD / f'{DIE_HARD} Bluray-1080p.mkv'

        Make.mock_files((f, 7854 * MB),
                        (xf, 9814 * MB))

        # Assert that there is 1 duplicate
        assert(iterlen(Find.existing()) == 1)

        assert(f.exists())
        assert(xf.exists())

        fylm.main()

        assert(not f.exists())
        assert(xf.exists())    
        assert(isclose(Film(xf).size.value, 9814 * MB, abs_tol=10))  
