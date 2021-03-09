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

import re
import os

import pytest

import fylmlib.config as config
import fylmlib.patterns as patterns
import fylm
import conftest

# @pytest.mark.skip()
class TestFilm(object):

    # @pytest.mark.skip(reason="Slow")
    def test_search_tmdb(self):

        conftest._setup()

        fylm.config.tmdb.enabled = True
        assert(fylm.config.tmdb.enabled is True)

        # Look up films by name from TMDb and update title
        for film in conftest.valid_films:
            film.search_tmdb()

            # Use this for debugging test matches
            # for f in conftest.all_test_films:
            #     if f.expected_title == film.title:
            #         print(f.acceptable_names, f.expected_title)

            matching_tests = list(filter(lambda t: (t.expected_title == film.title and len(t.acceptable_names) > 0), conftest.all_test_films))

            # Debugging helper
            # print(f"Looking up '{film.title}' ({film.year}) for '{film.original_basename}'")

            # Ensure that at least one matching test is found for the film
            assert(len(matching_tests) > 0)
            
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

        conftest._setup()

        # Check that films beginning with 'The' have it moved to the end, ', The'
        for film in conftest.films:
            if not film.should_ignore and ', the' in film.title_the.lower():
                assert(not film.title_the.lower().startswith('the '))
                assert(film.title_the.lower().endswith(', the'))

    def test_year(self):

        conftest._setup()

        # Check that year is detected correctly
        for film in conftest.films:
            if film.year is not None:
                assert(film.year >= 1910)
                assert(film.year < 2160)
                assert(film.year != 2160)
                assert(film.year != 1080)
                assert(film.year != 720)

    def test_resolution(self):

        conftest._setup()

        # Check that resolution is detected correctly
        for film in conftest.films:
            for file in film.video_files:
                if file.resolution is not None:
                    assert(file.resolution in ['720p', '1080p', '2160p'])

    def test_media(self):

        conftest._setup()

        # Check that media is detected correctly
        for film in conftest.films:
            for file in film.video_files:
                if file.media is not None:
                    assert(file.media in ['Bluray', 'WEBDL', 'HDTV', 'SDTV'])

    def test_hdr(self):

        conftest._setup()

        # Check that media is detected correctly
        for film in conftest.films:
            for file in film.video_files:
                assert(file.is_hdr is True or file.is_hdr is False)


    def test_proper(self):

        conftest._setup()

        # Check that proper is detected correctly
        for film in conftest.films:
            for file in film.video_files:
                assert(file.is_proper is True or file.is_proper is False)

    def test_edition(self):

        conftest._setup()

        # Check that editions, when detected, are set correctly and cleaned from original string
        for film in conftest.films:
            for file in film.video_files:
                for key, value in config.edition_map:
                    rx = re.compile(r'\b' + key + r'\b', re.I)
                    result = re.search(rx, file.original_basename)
                    if result:
                        assert(file.edition == rx.sub(value, result.group()))
                        assert(not re.search(rx, file.title))
                        break

    def test_is_file_or_dir(self):

        conftest._setup()

        # Check file extensions to verify whether source is a file or a dir
        for film in conftest.films:
            if film.is_file:
                print([x.ext for x in film.all_valid_files])
                assert(len(film.video_files) == 1)
                assert(len(film.all_valid_files) == 1)
                assert(film.all_valid_files[0].ext is not None and [film.all_valid_files[0].ext in config.video_exts + config.extra_exts])
                assert(film.is_folder == False)
            elif film.is_folder:
                assert(film.is_file == False)

    def test_should_ignore(self):

        conftest._setup()
        
        # Check that ignored films will be ignored
        for ignored in conftest.ignored:
            assert(ignored not in [os.path.basename(f.source_path) for f in conftest.valid_films])
