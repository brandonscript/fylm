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

import fylmlib.config as config
import fylmlib.operations as ops
import fylm
import conftest

# Overwrite the app's pre-loaded config.
fylm.config = config

# @pytest.mark.skip()
class TestConfig(object):
    """Tests operation impacting config options"""

    def test_reload(self):

        conftest._setup()

        assert(config.tmdb.enabled is True)
        config.tmdb.enabled = False
        assert(config.tmdb.enabled is False)
        config.reload()
        assert(config.tmdb.enabled is True)

    def test_config_test_mode_enabled(self):

        conftest._setup()
        
        # Set test mode to true
        fylm.config.test = True
        assert(fylm.config.test is True)

        # Disable TMDb lookups for faster test
        fylm.config.tmdb.enabled = False
        assert(fylm.config.tmdb.enabled is False)

        existing_files_before = ops.dirops.get_valid_files(conftest.films_src_path)
        
        # Execute
        fylm.main()

        moved_films = conftest.moved_films()

        existing_files_after = ops.dirops.get_valid_files(conftest.films_src_path)
        
        # Assert that no destructive changes are made in src or dst
        assert(len(moved_films) == 0)
        assert(existing_files_before == existing_files_after)

    def test_config_test_mode_disabled(self):
        
        conftest._setup()

        # Set test mode to true
        fylm.config.test = False
        assert(fylm.config.test is False)

        # Disable TMDb lookups for faster test
        fylm.config.tmdb.enabled = False
        assert(fylm.config.tmdb.enabled is False)

        # existing_files_before = ops.dirops.get_valid_files(conftest.films_src_path)
        
        # Execute
        fylm.main()

        moved_films = conftest.moved_films()

        # existing_films_after = map(Film, sorted(ops.dirops.get_valid_files(conftest.films_src_path)))
        
        # Assert that changes were made successfully
        assert(len(moved_films) > 0)

        # non_duplicate_films = [f.title for f in list(toolz.unique(conftest.films, key=lambda f: f.new_filename))]
        # non_duplicate_valid_films = [f.title for f in list(toolz.unique(conftest.valid_films, key=lambda f: f.new_filename))]
        # non_duplicate_remaining_films = [f.title for f in list(toolz.unique(existing_films_after, key=lambda f: f.new_filename))]

        # print("\n".join(non_duplicate_films), "\n\n", "\n".join(non_duplicate_valid_films), "\n\n", "\n".join(non_duplicate_remaining_films))
        # assert(len(non_duplicate_remaining_films) == len(non_duplicate_films) - len(non_duplicate_valid_films))
