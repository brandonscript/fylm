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

import pytest
import os
import itertools

import fylm
import fylmlib.config as config
from fylmlib.film import Film
from fylmlib import Info
import conftest
from make import Make, MB

# Overwrite the app's pre-loaded config.
fylm.config = config

SRC = conftest.src_path
DST = conftest.dst_paths
TTOP = '2001 - A Space Odyssey (1968)'

# @pytest.mark.skip()
class TestApp(object):
    """Integration tests for application functionality"""

    def test_app(self):
        
        # Disable duplicate checking so all test files are
        # guaranteed to move
        
        made = Make.all_mock_files()
        # Make.mock_files(*[
        #     (DST['1080p'] / TTOP / f'{TTOP} Bluray-1080p.mkv', 4 * MB),
        #     # DST['1080p'] / TTOP / f'{TTOP} WEBDL-1080p.m4v',
        #     # DST['720p'] / TTOP / f'{TTOP} Bluray-720p.mkv'
        #     # ,(DST['2160p'] / TTOP / f'{TTOP} WEBDL-2160p HDR.mp4', 30 * MB)
        # ])
        
        # config.interactive = True
        # config.always_copy = True
        # config.rename_only = True
        
        # (existing, expected) = get('expect_no_lookup')
        # for f in [f.expect_no_lookup for f in made.good]:
        #     print(f)
        
        config.duplicates.enabled = False

        # Execute
        fylm.App.run()

        # Make sure we have some test films
        assert(len(made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (existing, expected) = made.get()
        for desired_path in expected:
            assert(Info.exists_case_sensitive(desired_path))
        assert(len(existing) == len(expected))

    # @pytest.mark.skip(reason="Slow")
    #FIXME: Add simple test for no-folders
    # def test_app_no_folders(self):
        
    #     made = Make.all_mock_files()
        
    #     config.duplicates.enabled = False
    #     fylm.config.use_folders = False
        
    #     # Executes
    #     fylm.main()

    #     # Make sure we have some test films
    #     assert(len(made.good) > 0)

    #     # Assert that all of the films were moved successfully into the correct destination folders.
    #     (existing, expected) = made.get(folders=False)
    #     for desired_path in expected:
    #         assert(Info.exists_case_sensitive(desired_path))
    #     assert(len(existing) == len(expected))

    #     fylm.config.use_folders = True
    #     assert(fylm.config.use_folders is True)

    def test_app_tmdb_disabled(self):

        made = Make.all_mock_files()

        config.duplicates.enabled = False
        fylm.config.tmdb.enabled = False

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (existing, expected) = made.get(key='expect_no_lookup')
        for desired_path in expected:
            assert(Info.exists_case_sensitive(desired_path))
        assert(len(existing) == len(expected))
