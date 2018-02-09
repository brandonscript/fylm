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
import re
import sys
import time
import json
import pytest

from fylmlib.config import config
import conftest

class TestFilmClass(object):

    def test_valid_films(self):
        # Assert that we're getting the expected number of valid films.
        assert(len(conftest.valid_films) == conftest.valid_films_count)

    # @pytest.mark.skip(reason="Skip long running test_search_tmdb")
    @pytest.mark.slow
    def test_search_tmdb(self):

        # Look up films by name from TMDb and update title
        for film in conftest.valid_films:
            conftest.lookup_sync(film)

        for film in conftest.valid_films:
            matching_tests = filter(lambda x: x.expected_title == film.title, conftest.tests_map)
            if len(matching_tests) == 0:
                raise Exception('No matching tests found for "{}" (expected {}); check that there is a matching title property in files.json'.format(film.title, x.expected_title))

            # Get the first matching title in the tests map
            test_film = matching_tests[0]

            assert(film.title is not None)
            assert(film.title == test_film.expected_title)
            assert(film.tmdb_id is not None)
            assert(film.tmdb_id == test_film.expected_id)
            assert(film.year is not None)
        for not_a_film in list(set(conftest.films) - set(conftest.valid_films)):
            assert(not_a_film.tmdb_id is None)

    def test_title_the(self):
        # Check that films beginning with 'The' have it moved to the end, ', The'
        for film in conftest.films:
            if not film.should_ignore and ', the' in film.title_the.lower():
                assert(not film.title_the.lower().startswith('the '))
                assert(film.title_the.lower().endswith(', the'))

    def test_year(self):
        # Check that year is detected correctly
        for film in conftest.films:
            if film.year is not None:
                assert(film.year >= 1910)
                assert(film.year < 2160)
                assert(film.year != 2160)
                assert(film.year != 1080)
                assert(film.year != 720)

    def test_quality(self):
        # Check that quality is detected correctly
        for film in conftest.films:
            if film.quality is not None:
                assert(film.quality in ['720p', '1080p', '2160p'])

    def test_edition(self):
        # Check that editions, when detected, are set correctly and cleaned from original string
        for film in conftest.films:
            for key, value in config.edition_map:
                rx = re.compile(r'\b' + key + r'\b', re.I)
                if re.search(rx, film.original_filename):
                    assert(film.edition == value)
                    assert(not re.search(rx, film.title))
                    break

    def test_is_file_dir(self):
        # Check file extensions
        for film in conftest.films:
            if film.is_file:
                assert(film.ext is not None and [film.ext in config.video_exts + config.extra_exts])
            elif film.is_dir:
                assert(film.ext == None)
