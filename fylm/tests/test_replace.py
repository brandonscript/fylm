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
from builtins import *

import os
import pytest

from fylmlib.config import config
import fylmlib.operations as ops
import fylm
import conftest
import make

# Enable this to turn on test mode in config
# config.test = True

# Overwrite the app's pre-loaded config
config.reload()
fylm.config = config

# An array of potential duplicate files
raw_files = {
    '2160p': 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.DTS.mp4',
    '1080p': 'Rogue.One.A.Star.Wars.Story.2016.1080p.DTS.x264-group.mkv',
    '720p': 'Rogue.One.A.Star.Wars.Story.2016.720p.DTS.x264-group.mkv',
    'SD': 'Rogue.One.A.Star.Wars.Story.2016.avi'
}

clean_files = {
    '2160p': 'Rogue One A Star Wars Story (2016) 2160p/Rogue One A Star Wars Story (2016) 2160p.mp4',
    '1080p': 'Rogue One A Star Wars Story (2016) 1080p/Rogue One A Star Wars Story (2016) 1080p.mkv',
    '720p': 'Rogue One A Star Wars Story (2016) 720p/Rogue One A Star Wars Story (2016) 720p.mkv',
    'SD': 'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016).avi'
}

# @pytest.mark.skip()
class TestReplace(object):

    def test_replace_all_with_2160p(self):

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        
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

        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 12393 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb)

        # Assert that there are 3 duplicates
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file replaced all others of lesser quality and was correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))
        # Reset config
        fylm.config.reload()

    def test_keep_all_2160p(self):

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        
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
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), 12393 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb)

        # Assert that there are 3 duplicates
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 3)
        # Execute
        fylm.main()
        
        # Assert that the 4K file didn't replace any others and was correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))
        # Reset config
        fylm.config.reload()

    def test_keep_2160p_and_1080p(self):

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = False
        
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
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['2160p']), 52234 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), 12393 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p']), 7213 * make.mb)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD']), 786 * make.mb)

        # Assert that there are 2 duplicates
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 2)
        # Execute
        fylm.main()
        
        # Assert that the 4K and 1080p files replaced all others of lesser quality and were correctly processed
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['2160p'])))
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['2160p'], clean_files['2160p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['720p'], clean_files['720p'])))
        assert(not os.path.exists(os.path.join(conftest.films_dst_paths['SD'], clean_files['SD'])))
        # Reset config
        fylm.config.reload()

    def test_replace_smaller(self):

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        big_size = 14393 * make.mb
        sm_size = 8213 * make.mb
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), big_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), sm_size)

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, larger 1080p file overwrites the existing, smaller one
        assert(not os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    os.path.getsize(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])) == pytest.approx(big_size, 10))
        # Reset config
        fylm.config.reload()

    def test_do_not_replace_larger(self):

        # Set up config
        fylm.config.test = False
        fylm.config.duplicate_checking.enabled = True
        fylm.config.duplicate_replacing.enabled = True
        fylm.config.duplicate_replacing.replace_smaller = True

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        big_size = 14393 * make.mb
        sm_size = 8213 * make.mb
        
        make.make_mock_file(os.path.join(conftest.films_src_path, raw_files['1080p']), sm_size)
        make.make_mock_file(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p']), big_size)

        # Assert that there is 1 duplicate
        assert(len(ops.dirops.get_existing_films(config.destination_dirs)) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, larger 1080p file overwrites the existing, smaller one
        assert(    os.path.exists(os.path.join(conftest.films_src_path, raw_files['1080p'])))
        assert(    os.path.exists(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])))
        assert(    os.path.getsize(os.path.join(conftest.films_dst_paths['1080p'], clean_files['1080p'])) == pytest.approx(big_size, 10))
        # Reset config
        fylm.config.reload()
