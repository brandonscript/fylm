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

# import pytest

from multiprocessing import Pool
import multiprocessing
from pathlib import Path
import fylm
import fylmlib.config as config
from fylmlib.film import Film
from fylmlib.filmpath import Info
import conftest
from make import Make

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
        
        config.duplicates.enabled = False

        
        # Execute
        fylm.pool = Pool(multiprocessing.cpu_count())
        fylm.App.run()
        fylm.pool.close()

        # Make sure we have some test films
        assert(len(made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (existing, expected) = made.get()
        for desired_path in expected:
            assert(Info.exists_case_sensitive(desired_path))
        if (len(existing) != len(expected)):
            print([Path(ex) for ex in existing])
            print(expected)
        assert(len(existing) == len(expected))

    def test_app_tmdb_disabled(self):

        made = Make.all_mock_files()

        config.duplicates.enabled = False
        config.tmdb.enabled = False

        # Execute
        fylm.pool = Pool(multiprocessing.cpu_count())
        fylm.App.run()
        fylm.pool.close()

        # Make sure we have some test films
        assert(len(made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (existing, expected) = made.get(key='expect_no_lookup')
        for desired_path in expected:
            assert(Info.exists_case_sensitive(desired_path))
        assert(len(existing) == len(expected))
