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

import os
import itertools

try:
    from math import isclose
except ImportError:
    from pytest import approx
    def isclose(a, b, abs_tol=0.0):
        return a == approx(b, abs_tol)

import pytest

from fylmlib.film import Film
import fylmlib.config as config
import fylmlib.operations as ops
import fylm
import conftest
import make

# Enable this to turn on test mode in config
# config.test = True

# Overwrite the app's pre-loaded config
fylm.config = config

# An array of potential duplicate files
raw_files = {
    '2160p': 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.WEB-DL.DTS.mp4',
    '1080p': 'Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group.mkv',
    '720p': 'Rogue.One.A.Star.Wars.Story.2016.720p.BluRay.DTS.x264-group.mkv',
    'SD': 'Rogue.One.A.Star.Wars.Story.2016.avi'
}

clean_files = {
    '2160p': 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) WEBDL-2160p.mp4',
    '1080p': 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) Bluray-1080p.mkv',
    '720p': 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) Bluray-720p.mkv',
    'SD': 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016).avi',
    'non-dup': 'Mission Impossible - Rogue Nation (2015)/Mission Impossible - Rogue Nation (2015) Bluray-1080p.mkv'
}

# @pytest.mark.skip()
class TestDuplicates(object):

    # @pytest.mark.skip()
    def test_remove_duplicates_and_dirs(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        fylm.config.debug = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is False)
        
        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = [] 
        
        # Replace 1080p films with 4K
        fylm.config.duplicate_replacing.replace_quality['1080p'] = ['2160p'] 
        
        # Replace 720p films with 4K or 1080p
        fylm.config.duplicate_replacing.replace_quality['720p'] = ['2160p', '1080p'] 

        # Replace SD with any higher quality.
        fylm.config.duplicate_replacing.replace_quality['SD'] = ['2160p', '1080p', '720p'] 

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 12393 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['non-dup']), 8522 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there are 4 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in ops.dirops.get_existing_films(config.destination_dirs)]))
        assert(len(existing_files) == 4)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(os.path.join(conftest.films_src_path, raw_files['2160p'])).duplicate_files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file replaced all others of lesser quality and was correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))

        # Verify that non-duplicates are not deleted
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['non-dup'])))

    # @pytest.mark.skip()
    def test_replace_all_with_2160p(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        fylm.config.debug = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is False)
        
        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = [] 
        
        # Replace 1080p films with 4K
        fylm.config.duplicate_replacing.replace_quality['1080p'] = ['2160p'] 
        
        # Replace 720p films with 4K or 1080p
        fylm.config.duplicate_replacing.replace_quality['720p'] = ['2160p', '1080p'] 

        # Replace SD with any higher quality.
        fylm.config.duplicate_replacing.replace_quality['SD'] = ['2160p', '1080p', '720p'] 

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 12393 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there are 3 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in ops.dirops.get_existing_films(config.destination_dirs)]))
        assert(len(existing_files) == 3)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(os.path.join(conftest.films_src_path, raw_files['2160p'])).duplicate_files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file replaced all others of lesser quality and was correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))
        
        # Assert that duplicate backup files are removed
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], f'{clean_files["1080p"]}.dup')))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], f'{clean_files["720p"]}.dup')))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], f'{clean_files["SD"]}.dup')))
        
        # Assert that empty duplicate parent dirs are removed
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], os.path.dirname(clean_files['1080p']))))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], os.path.dirname(clean_files['720p']))))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], os.path.dirname(clean_files['SD']))))

    # @pytest.mark.skip()
    def test_keep_all_2160p(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is False)
        
        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['1080p'] = [] 
        
        # Replace 720p films with 1080p
        fylm.config.duplicate_replacing.replace_quality['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        fylm.config.duplicate_replacing.replace_quality['SD'] = ['1080p', '720p'] 

        conftest.cleanup_all()
        conftest.make_empty_dirs()
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 12393 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there are 3 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in ops.dirops.get_existing_films(config.destination_dirs)]))
        assert(len(existing_files) == 3)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(os.path.join(conftest.films_src_path, raw_files['2160p'])).duplicate_files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file didn't replace any others and was correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))

    # @pytest.mark.skip()
    def test_keep_2160p_and_1080p(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is False)
        
        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['1080p'] = [] 
        
        # Replace 720p films with 1080p
        fylm.config.duplicate_replacing.replace_quality['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        fylm.config.duplicate_replacing.replace_quality['SD'] = ['1080p', '720p'] 

        conftest.cleanup_all()
        conftest.make_empty_dirs()
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), 12393 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there are 2 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in ops.dirops.get_existing_films(config.destination_dirs)]))
        assert(len(existing_files) == 2)

        # Assert that for each of the 2 source files, there are 2 duplicate files detected
        assert(len(Film(os.path.join(conftest.films_src_path, raw_files['2160p'])).duplicate_files) == 2)
        assert(len(Film(os.path.join(conftest.films_src_path, raw_files['1080p'])).duplicate_files) == 2)

        # Execute
        fylm.main()
        
        # Assert that the 4K and 1080p files replaced all others of lesser quality and were correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))

    def test_keep_2160p_with_existing_1080p(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is False)
        
        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['1080p'] = [] 
        
        # Replace 720p films with 1080p
        fylm.config.duplicate_replacing.replace_quality['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        fylm.config.duplicate_replacing.replace_quality['SD'] = ['1080p', '720p'] 

        conftest.cleanup_all()
        conftest.make_empty_dirs()
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 14234 * make.mb_t)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 19393 * make.mb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the 4K and 1080p files replaced all others of lesser quality and were correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))

    # @pytest.mark.skip()
    def test_replace_proper(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is True)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        big_size = 12393 * make.mb_t
        sm_size = 11213 * make.mb_t

        proper = 'Rogue.One.A.Star.Wars.Story.2016.1080p.PROPER.BluRay.DTS.x264-group.mkv'
        proper_moved = 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) Bluray-1080p Proper.mkv'
        
        make.make_mock_file(os.path.join(conftest.films_src_path, proper), sm_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), big_size)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the proper 1080p file overwrites the existing one
        assert(not os.path.exists(os.path.join(conftest.films_src_path, proper)))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], proper_moved)))
        assert(    isclose(os.path.getsize(os.path.join(conftest.films_dst_paths['1080p'], proper_moved)), sm_size, abs_tol=10))

    # @pytest.mark.skip()
    def test_replace_smaller(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is True)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        big_size = 14393 * make.mb_t
        sm_size = 8213 * make.mb_t
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), big_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), sm_size)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, larger 1080p file overwrites the existing, smaller one
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    isclose(os.path.getsize(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])), big_size, abs_tol=10))

    # @pytest.mark.skip()
    def test_do_not_replace_larger(self):

        conftest._setup()

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is True)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        big_size = 14393 * make.mb_t
        sm_size = 8213 * make.mb_t
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), sm_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), big_size)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, smaller 1080p did not overwrite the existing, bigger one
        # and that the original was left intact (not renamed)
        assert(    os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    isclose(os.path.getsize(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])), big_size, abs_tol=10))

    def test_multiple_editions(self):

        conftest._setup()

        new = 'You Only Live Twice (1967) 1080p/You Only Live Twice (1967) 1080p-Bluray.mkv'
        new_moved = 'You Only Live Twice (1967)/You Only Live Twice (1967) Bluray-1080p.mkv' 
        existing = 'You Only Live Twice (1967)/You Only Live Twice (1967) [Extended] 1080p-Bluray.mkv'

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is True)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        new_size = 9393 * make.mb_t
        existing_size = 8213 * make.mb_t
        
        make.make_mock_file(os.path.join(conftest.films_src_path, new), new_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], existing), existing_size)

        # Reset existing films
        ops.dirops._existing_films = None

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that both editions exist in the end, with a console warning
        assert(not os.path.exists(os.path.join(conftest.films_src_path, new)))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], new_moved)))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], existing)))

    def test_keep_4k_and_hdr(self):

        conftest._setup()

        new = [('Aquaman.2018.1080p.BluRay.X264-SoNG/Aquaman.2018.1080p.BluRay.X264-SoNG.mkv', 8.48),
               ('Aquaman.2018.2160p.UHD.BluRay.X265-IAMABLE/Aquaman.2018.2160p.UHD.BluRay.X265-IAMABLE.mkv', 32.18),
               ('Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group/Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group.mkv', 14.41),
               ('Rogue.One.A.Star.Wars.Story.2016.4K.2160p.WEB-DL.DTS/Rogue.One.A.Star.Wars.Story.2016.4K.2160p.WEB-DL.DTS.mp4', 21.68),
               ('Star.Trek.Beyond.2016.2160p.BluRay.HDR-10bit.x265-AMiABLE/Star.Trek.Beyond.2016.2160p.BluRay.HDR-10bit.x265-AMiABLE.mkv', 18.54),
               ('Star Trek - Into Darkness (2013) (2160p BluRay x265 HEVC 10bit HDR AAC 7.1 Tigole)/Star Trek Into Darkness (2013) Bluray-2160p.mkv', 15.23),
               ('Star.Trek.Into.Darkness.2013.2160p.UHD.BluRay.x265-TERMiNAL/Star.Trek.Into.Darkness.2013.2160p.UHD.BluRay.x265-TERMiNAL.mkv', 22.81)]

        existing = [('1080p', 'Aquaman (2018)/Aquaman (2018) Bluray-1080p.mkv', 18.53),
                    ('1080p', 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) WEBDL-1080p.mkv', 9.80),
                    # Intentionally in the wrong folder
                    ('1080p', 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) WEBDL-2160p.mp4', 18.55),
                    ('2160p', 'Star Trek Beyond (2016)/Star Trek Beyond (2016) Bluray-2160p.mkv', 20.48),
                    ('1080p', 'Star Trek Into Darkness (2013)/Star Trek Into Darkness (2013) Bluray-1080p.mkv', 12.72),
                    ('2160p', 'Star Trek Into Darkness (2013)/Star Trek Into Darkness (2013) Bluray-2160p.mkv', 24.20)]

        expect = [('1080p', 'Aquaman (2018)/Aquaman (2018) Bluray-1080p.mkv', 18.53),
                  ('2160p', 'Aquaman (2018)/Aquaman (2018) Bluray-2160p.mkv', 32.18),
                  ('1080p', 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) Bluray-1080p.mkv', 14.41),
                  ('2160p', 'Rogue One - A Star Wars Story (2016)/Rogue One - A Star Wars Story (2016) WEBDL-2160p.mp4', 21.68),
                  ('2160p', 'Star Trek Beyond (2016)/Star Trek Beyond (2016) Bluray-2160p.mkv', 20.48),
                  ('2160p', 'Star Trek Beyond (2016)/Star Trek Beyond (2016) Bluray-2160p HDR.mkv', 18.54),
                  ('1080p', 'Star Trek Into Darkness (2013)/Star Trek Into Darkness (2013) Bluray-1080p.mkv', 12.72),
                  ('2160p', 'Star Trek Into Darkness (2013)/Star Trek Into Darkness (2013) Bluray-2160p HDR.mkv', 15.23),
                  ('2160p', 'Star Trek Into Darkness (2013)/Star Trek Into Darkness (2013) Bluray-2160p.mkv', 24.20)]


        do_not_move = [new[0], new[6]]

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True
        assert(fylm.config.test is False)
        assert(fylm.config.duplicate_checking.enabled is True)
        assert(fylm.config.duplicate_replacing.enabled is True)
        assert(fylm.config.duplicate_replacing.replace_smaller is True)

        # Do not replace 2160p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['2160p'] = []
        assert(len(fylm.config.duplicate_replacing.replace_quality['2160p']) == 0)

        # Do not replace 1080p films with any other quality
        fylm.config.duplicate_replacing.replace_quality['1080p'] = []
        assert(len(fylm.config.duplicate_replacing.replace_quality['1080p']) == 0)

        conftest.cleanup_all()
        conftest.make_empty_dirs()
        
        for f in new:
            make.make_mock_file(os.path.join(conftest.films_src_path, f[0]), f[1] * make.gb_t)

        for f in existing:
            make.make_mock_file(os.path.join(conftest.films_dst_paths[f[0]], f[1]), f[2] * make.gb_t)

        # Reset existing films
        ops.dirops._existing_films = None

        existing_films = ops.dirops.get_existing_films(config.destination_dirs)
        # Assert that there are 6 duplicate films
        assert(len(existing_films) == 5)

        # Assert that the total duplicate files is 7
        assert(len(list(itertools.chain(*[f.all_valid_files for f in existing_films]))) == 6)
        
        # Execute
        fylm.main()
        
        # Assert that the correct editions were moved, and those that didn't meet the criteria were left alone
        for f in expect:
            path = os.path.join(conftest.films_dst_paths[f[0]], f[1])
            assert(os.path.exists(path))
            assert(isclose(os.path.getsize(path), f[2] * make.gb_t, abs_tol=10))

        for f in do_not_move:
            path = os.path.join(conftest.films_src_path, f[0])
            assert(os.path.exists(path))
            assert(isclose(os.path.getsize(path), f[1] * make.gb_t))
