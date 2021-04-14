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

import re
import os
import pathlib

import pytest

import fylmlib.config as config
import fylmlib.patterns as patterns
import fylmlib.tmdb as tmdb
import fylm
import conftest
from fylmlib.enums import Media

# @pytest.mark.skip()
class TestFilm(object):

    # @pytest.mark.skip(reason="Slow")
    def test_search_tmdb(self):

        conftest._setup()

        fylm.config.tmdb.enabled = True
        assert(fylm.config.tmdb.enabled is True)

        # Look up films by name from TMDb and update title
        for film in tmdb.dispatch_search_set(conftest.valid_films).run():
            expected_path = os.path.join(
                film.primary_file.new_foldername, film.primary_file.new_filename_and_ext)
            match = next((tf for tf in conftest.made.good for f in tf.expect if f == expected_path), None)

            if match is None:
                raise AssertionError(f'"{expected_path}" was expected but not found on the filesystem')
                
            assert(film.title is not None)
            assert(film.tmdb_id is not None)
            assert(film.tmdb_id == match.tmdb_id)
            assert(film.year is not None)

        for not_a_film in list(set(conftest.all_films) - set(conftest.valid_films)):
            assert(not_a_film.tmdb_id is None)

    def test_title_the(self):

        conftest._setup()

        # Check that films beginning with 'The' have it moved to the end, ', The'
        for film in conftest.all_films:
            if not film.should_ignore and ', the' in film.title_the.lower():
                assert(not film.title_the.lower().startswith('the '))
                assert(film.title_the.lower().endswith(', the'))

    def test_year(self):

        conftest._setup()

        # Check that year is detected correctly
        for film in conftest.all_films:
            if film.year is not None:
                assert(film.year >= 1910)
                assert(film.year < 2160)
                assert(film.year != 2160)
                assert(film.year != 1080)
                assert(film.year != 720)

    def test_resolution(self):

        conftest._setup()

        # Check that resolution is detected correctly
        for film in conftest.all_films:
            for file in film.video_files:
                if file.resolution is not None:
                    assert(file.resolution in ['720p', '1080p', '2160p'])

    def test_mediainfo(self):

        

    def test_media(self):

        conftest._setup()

        # Check that media is detected correctly
        for film in conftest.all_films:
            for file in film.video_files:
                if file.media is not None and file.media is not Media.UNKNOWN:
                    assert(file.media in [Media.BLURAY, Media.WEBDL, Media.HDTV, Media.SDTV])

    def test_hdr(self):

        conftest._setup()

        # Check that media is detected correctly
        for film in conftest.all_films:
            for file in film.video_files:
                assert(file.is_hdr is True or file.is_hdr is False)


    def test_proper(self):

        conftest._setup()

        # Check that proper is detected correctly
        for film in conftest.all_films:
            for file in film.video_files:
                assert(file.is_proper is True or file.is_proper is False)

    def test_edition(self):

        conftest._setup()

        # Check that editions, when detected, are set correctly and cleaned from original string
        for film in conftest.all_films:
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
        for film in conftest.all_films:
            if film.is_file:
                assert(len(film.video_files) == 1)
                assert(len(film.all_valid_files) == 1)
                assert(film.all_valid_files[0].ext is not None and [film.all_valid_files[0].ext in config.video_exts + config.extra_exts])
                assert(film.is_folder == False)
            elif film.is_folder:
                assert(film.is_file == False)

    def test_should_ignore(self):

        conftest._setup()
        
        # Check that bad films will be ignored
        for tf in conftest.made.bad:
            for f in tf.make:
                assert(f not in [os.path.basename(f.source_path) for f in conftest.valid_films])
