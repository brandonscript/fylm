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
import sys
from time import time

import pytest

import fylmlib.config as config
import fylmlib.operations as ops
import conftest
import fylm
import make
from pathlib import Path

t = 100 if os.environ.get('TRAVIS') else 1

class TestFilmPath(object):

    def test_init(self):

        conftest.make_empty_dirs()
        
        path = conftest.full_path('files/#new')

        made = conftest.make_all_mock_files(
            'files.json', path)
        
        paths = ops.Find.existing_films('/volumes/Films/HD')
        paths = ops.Find.sync_attrs(paths, ['maybe_film'])
        # paths = ops.Find.existing_films('/Users/brandonscript/Dev/fylm/fylm/tests/files/#new/#4K')
        # print()
        # for p in paths:
        #     print(p.origin, p)
        
        # for d in paths[3].descendents:
        #     print(d)
        # if False:    
        for p in paths:
            
            # print(p, p.container.name, len(p.dirs))
            # t1 = time()
            # if p.is_file():
            print(
                # p.filmrel if p.maybe_film else p.branch.name
                #   p.relpath 
                p.relative_to(p.origin)
                # , 'DID_SYNC' if p._did_sync else 'X'                
                # , 'BRANCH' if p.is_branch else ''
                # , 'CONTAINER' if p.is_container else ''
                # , 'TERMINUS' if p.is_terminus else ''
                # , 'FILM' if p.maybe_film else ''
                # , 'EMPTY' if p.is_empty else ''
            )
                    # if not p.year:
                    #     p
                # t2 = time()
                # print(f'Elapsed time is {t2 - t1} seconds.')
                # if not p.is_origin and p.maybe_film:
                #     print(p)

        
        # FilmPath

# @pytest.mark.skip()
class TestDirOperations(object):

    def test_verify_root_paths_exist(self):

        if sys.platform == "win32":
            ops.dirops.verify_root_paths_exist(['C:\\'])
        else:
            ops.dirops.verify_root_paths_exist(['/bin'])

    @pytest.mark.xfail(raises=(OSError, IOError))
    def test_verify_root_paths_exist_err(self):

        if sys.platform == "win32":
            ops.dirops.verify_root_paths_exist(['C:\\__THERE_IS_NO_SPOON__'])
        else:
            ops.dirops.verify_root_paths_exist(['/__THERE_IS_NO_SPOON__'])

    @pytest.mark.skip(reason='Cannot reliably test multiple partitions/mount points')
    def test_is_same_partition(self):
        pass

    def test_get_existing_films(self):

        fylm.config.duplicates.enabled = True
        assert(fylm.config.duplicates.enabled is True)

        files = {
            '2160p': 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.DTS.mp4',
            '1080p': 'Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group.mkv',
            '720p': 'Rogue.One.A.Star.Wars.Story.2016.720p.DTS.x264-group.mkv',
            'SD': 'Rogue.One.A.Star.Wars.Story.2016.avi'
        }

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_dst_paths['2160p'], files['2160p']), 52234 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], files['1080p']), 11234 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], files['720p']), 6590 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], files['SD']), 723 * make.mb * t)

        # Reset existing films
        ops.dirops._existing_films = None

        assert(ops.dirops._existing_films is None)
        assert(len(ops.dirops.get_existing_films(conftest.films_dst_paths)) == 4)
        assert(ops.dirops._existing_films is not None and len(ops.dirops._existing_films) == 4)

    def test_find_new_films(self):

        conftest._setup()

        all_films = ops.dirops.find_new_films([conftest.films_src_path])
        valid_films = list(filter(lambda film: not film.should_ignore, all_films))

        # Assert that we're getting the expected number of films.
        assert(len(all_films) == len(conftest.made.all))

        # Assert that we're getting the expected number of valid films.
        assert(len(valid_films) == len(conftest.made.good))

    def test_find_new_films_multiple_dirs(self):

        conftest._setup()

        fylm.config.source_dirs.append(conftest.films_src_path2)

        # Make files in alternate path

        make.make_mock_file(os.path.join(
            conftest.films_src_path2, 'Alita.Battle.Angel.2019.BluRay.1080p.x264-NMaRE/Alita.Battle.Angel.2019.BluRay.1080p.x264-NMaRE.mkv'),
            8132 * make.mb * t)

        make.make_mock_file(os.path.join(
            conftest.films_src_path2, 'All.the.Money.in.the.World.2017.BluRay.1080p.x264-NMaRE/All.the.Money.in.the.World.2017.BluRay.1080p.x264-NMaRE.mkv'), 
            7354 * make.mb * t)

        all_films = ops.dirops.find_new_films(fylm.config.source_dirs)
        valid_films = list(filter(lambda film: not film.should_ignore, all_films))

        # Assert that we're getting the expected number of films. (+2 for the 2 we added)
        assert(len(all_films) == len(conftest.made.all) + 2)

        # Assert that we're getting the expected number of valid films. (+2 for the 2 we added)
        assert(len(valid_films) == len(conftest.made.good) + 2)

        # Assert that the list is sorted alphabetically (case insensitive is fine)
        assert(all(valid_films[i].title.lower() <= valid_films[i+1].title.lower()
                   for i in range(len(valid_films)-1)))

    def test_get_valid_files(self):

        conftest._setup()

        fylm.config.min_filesize = 50 # min filesize in MB
        assert(fylm.config.min_filesize == 50)

        files = [
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.sample.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/GROUP.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/RO-ad-scene-WATCHME.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/subs-english.srt',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.nfo',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.sfv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Cover.jpg'
        ]

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_src_path, files[0]), 2354 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[1]),  134 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[2]),   23 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[3]),  219 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),   14 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[5]),    5 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[6]),    6 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[7]),    7 * make.mb * t)
        
        # Assert that there is only one test film identified at the source
        assert(len(ops.dirops.find_new_films([conftest.films_src_path])) == 1)

        valid_files = ops.dirops.get_valid_files(
            os.path.join(conftest.films_src_path, 'Rogue.One.2016.1080p.BluRay.DTS.x264-group')
        )

        # Assert that of the 8 files presented, only two are valid
        #   Main video file and .srt
        assert(len(valid_files) == 2)

        assert(os.path.join(conftest.films_src_path, files[0]) in valid_files) # Main video file
        assert(os.path.join(conftest.films_src_path, files[4]) in valid_files) # .srt

    def get_invaild_files(self):

        conftest._setup()

        fylm.config.min_filesize = 50 # min filesize in MB
        assert(fylm.config.min_filesize == 50)

        files = [
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.sample.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/GROUP.mkv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/subs-english.srt',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.nfo',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Rogue.One.2016.1080p.BluRay.DTS.x264-group.sfv',
            'Rogue.One.2016.1080p.BluRay.DTS.x264-group/Cover.jpg'
        ]

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_src_path, files[0]), 2354 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[1]),  134 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[2]),   23 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[3]),  219 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),   14 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[5]),    5 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[6]),    6 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[7]),    7 * make.mb * t)
        
        # Assert that there is only one test film identified at the source
        assert(len(ops.dirops.find_new_films(conftest.films_src_path)) == 1)

        invalid_files = ops.dirops.get_invalid_files(
            os.path.join(conftest.films_src_path, 'Rogue.One.2016.1080p.BluRay.DTS.x264-group')
        )

        # Assert that of the 8 files presented, 6 are invalid
        assert(len(invalid_files) == 6)

        assert(os.path.join(conftest.films_src_path, files[0]) not in invalid_files) # Main video file
        assert(os.path.join(conftest.films_src_path, files[4]) not in invalid_files) # .srt

    def test_sanitize_dir_list(self):

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            '.DS_Store',
            'Thumbs.db',
            'sub/folder/.DS_Store',
            'sub/folder/Thumbs.db',
            'Amélie.avi',
            'Nausicaä of the Valley of the Wind.avi',
            'Hot Fuzz.avi'
        ]

        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), (700 if f.endswith('.avi') else 1) * make.mb * t)

        loaded_files = ops.dirops.get_valid_files(conftest.films_src_path)

        assert(len(loaded_files) == 3)
        assert('.DS_Store' not in loaded_files)
        assert('Thumbs.db' not in loaded_files)

    def test_create_deep(self):

        conftest._setup()
        fylm.config.test = False
        assert(fylm.config.test is False)
        conftest.cleanup_all()

        create_path = os.path.join(conftest.films_src_path, 'Yates/Gilbert/Holtzmann/Tolan')

        assert(not os.path.exists(conftest.films_src_path))
        assert(not os.path.exists(create_path))

        ops.dirops.create_deep(create_path)

        assert(os.path.exists(conftest.films_src_path))
        assert(os.path.exists(create_path))

        conftest._setup()
        fylm.config.test = True
        assert(fylm.config.test is True)
        conftest.cleanup_all()

        ops.dirops.create_deep(create_path)

        assert(not os.path.exists(conftest.films_src_path))
        assert(not os.path.exists(create_path))

    @pytest.mark.xfail(raises=OSError)
    def test_create_deep_err(self):

        fylm.config.test = False
        assert(fylm.config.test is False)

        if sys.platform == "win32":
            ops.dirops.create_deep('C:\\Windows\\System32\\ShouldNotBeWritable')
        else:
            ops.dirops.create_deep('/bin/ShouldNotBeWritable')

    def test_find_deep(self):

        conftest.cleanup_all()

        create_path1 = os.path.join(conftest.films_src_path, 'Yates/Gilbert/Holtzmann/Tolan')
        create_path2 = os.path.join(conftest.films_src_path, 'Roman/Hamilton/Ride/Jemison')

        ops.dirops.create_deep(create_path1)
        ops.dirops.create_deep(create_path2)

        files = [
            'Yates/Abby.txt',
            'Yates/Gilbert/Erin.txt',
            'Yates/Gilbert/Holtzmann/Jillian.txt',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.txt',
            'Yates/Thumbs.db',
            'Roman/Nancy_Grace.txt',
            'Roman/Hamilton/Margaret.txt',
            'Roman/Hamilton/Ride/Sally.txt',
            'Roman/Hamilton/Ride/Jemison/Mae.txt',
            'Roman/.DS_Store'
        ]

        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 10 * make.kb * t)

        find = ops.dirops.find_deep(conftest.films_src_path)

        assert(len(find) == 8)
        assert(not os.path.join(conftest.films_src_path, files[4]) in find)
        assert(not os.path.join(conftest.films_src_path, files[9]) in find)

    def test_delete_dir_and_contents(self):

        fylm.config.test = False
        assert(fylm.config.test is False)

        create_path = os.path.join(conftest.films_src_path, 'Yates/Gilbert/Holtzmann/Tolan')

        ops.dirops.create_deep(create_path)

        files = [
            'Yates/Abby.txt',
            'Yates/Gilbert/Erin.txt',
            'Yates/Gilbert/Holtzmann/Jillian.txt',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.txt'
        ]

        # Create files. Ensure that for this to pass, the total filesize of the test dir
        # does not exceed this method's max_size default (50KB).
        conftest.cleanup_all()
        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 4 * make.kb * t)

        before_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(before_contents) == 4)

        ops.dirops.delete_dir_and_contents(conftest.films_src_path)

        after_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents) == 0)
        assert(not os.path.exists(conftest.films_src_path))

        # Test that if file size exceeds the default max_size, we do not delete
        conftest.cleanup_all()
        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 40 * make.mb * t)

        before_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(before_contents) == 4)

        ops.dirops.delete_dir_and_contents(conftest.films_src_path)

        after_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents) == 4)
        assert(os.path.exists(conftest.films_src_path))

        # Test overwriting default max_size with -1, unlimited
        conftest.cleanup_all()
        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 400 * make.mb * t)

        before_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(before_contents) == 4)

        ops.dirops.delete_dir_and_contents(conftest.films_src_path, max_size=-1)

        after_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents) == 0)
        assert(not os.path.exists(conftest.films_src_path))

        # Test do not delete when test mode is enabled.
        fylm.config.test = True
        assert(fylm.config.test is True)

        conftest.cleanup_all()

        for f in files:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 4 * make.kb * t)

        before_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(before_contents) == 4)

        ops.dirops.delete_dir_and_contents(conftest.films_src_path)

        after_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents) == 4)
        assert(os.path.exists(conftest.films_src_path))

    def test_delete_unwanted_files(self):

        conftest.cleanup_all()

        create_path = os.path.join(conftest.films_src_path, 'Yates/Gilbert/Holtzmann/Tolan')

        ops.dirops.create_deep(create_path)

        files_nfo = [
            'Yates/Abby.nfo',
            'Yates/Gilbert/Erin.nfo',
            'Yates/Gilbert/Holtzmann/Jillian.nfo',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.nfo'
        ]

        files_mkv = [
            'Yates/Abby.mkv',
            'Yates/Gilbert/Erin.mkv',
            'Yates/Gilbert/Holtzmann/Jillian.mkv',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.mkv'
        ]

        bad_files_mkv = [
            'Yates/Oh.mkv',
            'Yates/Gilbert/Danny.mkv',
            'Yates/Gilbert/Holtzmann/Boy.mkv',
            'Yates/Gilbert/Holtzmann/Tolan/The.mkv'
        ]

        config.min_filesize = 5
        assert(config.min_filesize == 5)

        # Create files. Ensure that for this to pass, the total filesize of the test dir
        # does not exceed this method's max_size default (50KB).
        for f in files_nfo:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 4 * make.kb * t)
        for f in files_mkv:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 7418 * make.mb * t)
        for f in bad_files_mkv:
             make.make_mock_file(os.path.join(conftest.films_src_path, f), 7 * make.kb * t)

        before_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(before_contents) == 12)

        config.test = True
        assert(config.test is True)

        ops.dirops.delete_unwanted_files(conftest.films_src_path)

        after_contents_t = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents_t) == 12)

        config.test = False
        assert(config.test is False)

        ops.dirops.delete_unwanted_files(conftest.films_src_path)

        after_contents = ops.dirops.find_deep(conftest.films_src_path)
        assert(len(after_contents) == 4)

        config.min_filesize = 0
        assert(config.min_filesize == 0)

# @pytest.mark.skip()
class TestFileOperations(object):

    def test_has_valid_ext(self):

        conftest._setup()
        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            'Test.File.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo',
            'Test.File.jpg',
        ]

        make.make_mock_file(os.path.join(conftest.films_src_path, files[0]), 2354 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[1]),   10 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[2]),    4 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[3]),  454 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),    4 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),    6 * make.mb * t)

        assert(    ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[0])))
        assert(    ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[1])))
        assert(    ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[2])))
        assert(    ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[3])))
        assert(not ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[4])))
        assert(not ops.fileops.has_valid_ext(os.path.join(conftest.films_src_path, files[5])))

    def test_is_acceptable_size(self):

        conftest._setup()

        config.min_filesize = 5 # min filesize in MB
        assert(config.min_filesize == 5)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            'Test.File.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo'
        ]

        make.make_mock_file(os.path.join(conftest.films_src_path, files[0]),  300 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[1]),    1 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[2]),    4 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[3]),   54 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),    4 * make.kb * t)

        assert(    ops.fileops.is_acceptable_size(os.path.join(conftest.films_src_path, files[0])))
        assert(not ops.fileops.is_acceptable_size(os.path.join(conftest.films_src_path, files[1])))
        assert(    ops.fileops.is_acceptable_size(os.path.join(conftest.films_src_path, files[2])))
        assert(    ops.fileops.is_acceptable_size(os.path.join(conftest.films_src_path, files[3])))
        assert(not ops.fileops.is_acceptable_size(os.path.join(conftest.films_src_path, files[4])))

        config.min_filesize = 0 # min filesize back to 0
        assert(config.min_filesize == 0)

    def test_contains_ignored_strings(self):

        assert(ops.fileops.contains_ignored_strings('This.Is.A.sample.mkv'))
        assert(not ops.fileops.contains_ignored_strings('This.Is.Not.mkv'))

    def test_delete(self):

        conftest._setup()

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        file = os.path.join(conftest.films_src_path, 'Test.File.mkv')

        make.make_mock_file(file, 2354 * make.mb * t)

        fylm.config.test = True
        assert(fylm.config.test is True)

        ops.fileops.delete(file)
        assert(os.path.exists(file))

        fylm.config.test = False
        assert(fylm.config.test is False)

        ops.fileops.delete(file)
        assert(not os.path.exists(file))


# @pytest.mark.skip()
class TestSizeOperations(object):
    def test_size(self):

        conftest._setup()

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        file = os.path.join(conftest.films_src_path, 'Test.File.mkv')
        file_in_dir = os.path.join(conftest.films_src_path, 'Test.Dir/Test.File.mkv')
        file_in_dir_a1 = os.path.join(conftest.films_src_path, 'Test.Dir2/Test.File.mkv')
        file_in_dir_a2 = os.path.join(conftest.films_src_path, 'Test.Dir2/Test.File.jpg')
        file_in_dir_a3 = os.path.join(conftest.films_src_path, 'Test.Dir2/Test.File.avi')

        size = 2354 * make.mb

        make.make_mock_file(file, size)
        make.make_mock_file(file_in_dir, size)
        make.make_mock_file(file_in_dir_a1, size)
        make.make_mock_file(file_in_dir_a2, 10 * make.mb * t)
        make.make_mock_file(file_in_dir_a3, 700 * make.mb * t)

        # Assert file is the correct size within 1 byte
        assert(abs(ops.size(file) - size) <= 1)

        # Assert dir is at least the size of the file, probably larger
        # because the folder itself takes up some space. Diff of 1 byte.
        assert(abs(ops.size(os.path.dirname(file_in_dir)) - size) <= 1)

        # Test multiple files in dir to diff of 3 bytes
        assert(abs(ops.size(os.path.dirname(file_in_dir_a1)) - (size + (710 * make.mb * t))) <= 3)

    def size_of_largest_video(self):

        conftest._setup()

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            'Test.File/Test.File.mkv',
            'Test.File/Test.File2.mkv',
            'Test.File/Test.File3.mkv',
            'Test.File/Test.File.avi',
            'Test.File/Test.File.srt',
            'Test.File/Test.File.mp4',
            'Test.File/Test.File.nfo'
        ]

        make.make_mock_file(os.path.join(conftest.films_src_path, files[0]), 2354 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[1]), 1612 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[2]),  280 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[3]),   10 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[4]),    4 * make.kb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[5]),  454 * make.mb * t)
        make.make_mock_file(os.path.join(conftest.films_src_path, files[6]),    4 * make.kb * t)

        # Test multiple files to diff of 1 byte
        assert(abs(ops.size(ops.largest_video(os.path.dirname('Test.File'))) - (2354 * make.mb * t)) <= 1)
