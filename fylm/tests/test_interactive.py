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
import fylmlib.operations as ops
import fylm
import conftest
import make

# @pytest.mark.skip()
class TestInteractive(object):

    def test_lookup_success(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)

        fylm.config.mock_input = ['N', 'Bridget Jones - The Edge of Reason', 1]

        f = os.path.join(conftest.films_src_path, 'Bridget Jones - The Edge of Reason 1080p/Bridget Jones - The Edge of Reason Bluray-1080p.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Bridget Jones - The Edge of Reason (2004)/Bridget Jones - The Edge of Reason (2004) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 7354 * make.mb)

        assert(os.path.exists(f))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))

    def test_handle_duplicates_upgrade_same_quality_folder(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'U']

        f = os.path.join(conftest.films_src_path, 'Die.Hard.1988.BluRay.1080p.x264-CYaNID3/Die.Hard.1988.BluRay.1080p.x264-CYaNID3.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 8233 * make.mb)
        make.make_mock_file(xf, 7901 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))
        assert(isclose(ops.size(xf), 8233 * make.mb, abs_tol=10))

    def test_handle_duplicates_upgrade_same_quality_file(self):

        conftest._setup()

        # Set up config
        fylm.config.use_folders = False
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.use_folders is False)
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'U']

        f = os.path.join(conftest.films_src_path, 'Die Hard (1988) 1080p BluRay.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 9576 * make.mb)
        make.make_mock_file(xf, 6441 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))
        assert(isclose(ops.size(xf), 9576 * make.mb, abs_tol=10))

    def test_handle_duplicates_upgrade_lower_quality(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.use_folders is True)
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'U']

        n = 'Die.Hard.1988.BluRay.1080p.x264-CYaNID3.mkv/Die.Hard.1988.BluRay.1080p.x264-CYaNID3.mkv.mkv'
        f = os.path.join(conftest.films_src_path, n)
        xf = os.path.join(conftest.films_dst_paths['720p'], 'Die Hard (1988)/Die Hard (1988) WEBDL-720p.mkv')
        nf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 9114 * make.mb)
        make.make_mock_file(xf, 4690 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(not os.path.exists(xf))
        assert(os.path.exists(nf))
        assert(isclose(ops.size(nf), 9114 * make.mb, abs_tol=10))        

    def test_handle_duplicates_replace_identical(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.use_folders is True)
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'R']

        f = os.path.join(conftest.films_src_path, 'Die Hard (1988) 1080p BluRay.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 8133 * make.mb)
        make.make_mock_file(xf, 8133 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))
        assert(isclose(ops.size(xf), 8133 * make.mb, abs_tol=10))

    def test_handle_duplicates_skip(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'S']

        f = os.path.join(conftest.films_src_path, 'Die Hard (1988) 1080p/Die Hard (1988) 1080p.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988) 1080p/Die Hard (1988) 1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 8854 * make.mb)
        make.make_mock_file(xf, 9814 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

    def test_handle_duplicates_keep_both(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        # Allow 1080p and 720p to be kept
        fylm.config.duplicates.upgrade_table['720p'] = [] 
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)
        assert(len(fylm.config.duplicates.upgrade_table['720p']) == 0)

        fylm.config.mock_input = ['Y', 'K']

        n = 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv'
        f = os.path.join(conftest.films_src_path, n)
        xf = os.path.join(conftest.films_dst_paths['720p'], 'Die Hard (1988)/Die Hard (1988) HDTV-720p.mkv')
        nf = os.path.join(conftest.films_dst_paths['1080p'], n)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 10223 * make.mb)
        make.make_mock_file(xf, 4690 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))
        assert(os.path.exists(nf))
        assert(isclose(ops.size(xf), 4690 * make.mb, abs_tol=10))        
        assert(isclose(ops.size(nf), 10223 * make.mb, abs_tol=10))   

    def test_handle_duplicates_delete_new(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.interactive = True
        fylm.config.duplicates.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.interactive is True)
        assert(fylm.config.duplicates.enabled is True)

        fylm.config.mock_input = ['Y', 'D', 'Y']

        f = os.path.join(conftest.films_src_path, 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv')
        xf = os.path.join(conftest.films_dst_paths['1080p'], 'Die Hard (1988)/Die Hard (1988) Bluray-1080p.mkv')

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(f, 7854 * make.mb)
        make.make_mock_file(xf, 9814 * make.mb)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)

        assert(os.path.exists(f))
        assert(os.path.exists(xf))

        fylm.main()

        assert(not os.path.exists(f))
        assert(os.path.exists(xf))    
        assert(isclose(ops.size(xf), 9814 * make.mb, abs_tol=10))  

        fylm.config.interactive = False
        assert(fylm.config.interactive is False)

