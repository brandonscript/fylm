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
        
        made = Make.all_mock_files()
        Make.mock_files(*[
            (DST['1080p'] / TTOP / f'{TTOP} Bluray-1080p.mkv', 4 * MB),
            DST['1080p'] / TTOP / f'{TTOP} WEBDL-1080p.m4v',
            DST['720p'] / TTOP / f'{TTOP} Bluray-720p.mkv'
            # ,(DST['2160p'] / TTOP / f'{TTOP} WEBDL-2160p HDR.mp4', 30 * MB)
        ])
        
        config.interactive = True
        
        # (moved, expected) = get('expect_no_lookup')
        # for f in [f.expect_no_lookup for f in made.good]:
        #     print(f)

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (moved, expected) = get('expect')
        for desired_path in expected:
            assert(ops.fileops.exists_case_sensitive(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

    # @pytest.mark.skip(reason="Slow")
    def test_app_no_folders(self):

        conftest._setup()

        fylm.config.test = False
        fylm.config.use_folders = False
        fylm.config.tmdb.enabled = True
        assert(fylm.config.test is False)
        assert(fylm.config.use_folders is False)
        assert(fylm.config.tmdb.enabled is True)

        # Executes
        fylm.main()

        # Make sure we have some test films
        assert(len(conftest.made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders.
        (moved, expected) = get('expect', folders=False)
        for desired_path in expected:
            assert(ops.fileops.exists_case_sensitive(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

        fylm.config.use_folders = True
        assert(fylm.config.use_folders is True)

    def test_app_tmdb_disabled(self):

        conftest._setup()

        fylm.config.test = False
        fylm.config.use_folders = True
        fylm.config.tmdb.enabled = False
        assert(fylm.config.test is False)
        assert(fylm.config.use_folders is True)
        assert(fylm.config.tmdb.enabled is False)

        # Execute
        fylm.main()

        # Make sure we have some test films
        assert(len(conftest.made.good) > 0)

        # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
        (moved, expected) = get('expect_no_lookup')
        for desired_path in expected:
            assert(ops.fileops.exists_case_sensitive(desired_path))
        assert(len(list(set(moved))) == len(list(set(expected))))

def get(key, folders=True) -> ([], []):
    expected = []
    moved = []
    # Assert that all of the films were moved successfully into the correct destination folders/subfolders.
    for tfilm in conftest.made.good:
        ex = tfilm.expect if key == 'expect' else tfilm.expect_no_lookup
        valid_paths = [p for p in ex if p is not None]
        for path in valid_paths:
            desired_path = conftest.desired_path(path, tfilm, folder=folders)
            if desired_path:
                expected.append(desired_path)

    for t in conftest.films_dst_paths.values():
        for r, _, files in os.walk(t):
            for f in list(filter(lambda x: not x.startswith('.'), files)):
                moved.append(os.path.join(r, f))

    # Need to remove identical duplicates, as only one will exist on the filesystem
    return (list(set(moved)), list(set(expected)))
