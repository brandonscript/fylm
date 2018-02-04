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

from __future__ import unicode_literals, print_function

import unittest
import os
import re
import sys
import unicodedata
import io
import random
import time
# import threading
from glob import glob
# from Queue import Queue

from fylmlib.config import config
import fylmlib.operations as ops
from tests.make import make

DIVIDER = '======================================================================'

def print_title(title):
    print('\n{}\n{}\n{}'.format(DIVIDER, title, DIVIDER))

print('Init tests...')

files_path = 'tests/files'

# Set config to quiet so that TravisCI doesn't fail attempting to send
# notifications to 127.0.0.1.
config.quiet = True

# Set the minimum filesize to 0 so we can load mock files
config.min_filesize = 0

# TravisCI uses environment variables to keep keys secure. Map the TMDB_KEY
# if it is available.
if os.environ.get('TMDB_KEY') is not None: 
    config['tmdb']['key'] = os.environ.get('TMDB_KEY')

# Make test files.
tests_map = make('tests/files.json', files_path)

# If you change the number of valid films in the json map,
# update valid_films_count to match.
valid_films_count = 106

# Load films and filter them into valid films.
films = ops.dirops.get_new_films(files_path)
valid_films = filter(lambda film: not film.should_ignore, films)

# Async handling for lookups.
# TMDb is rate-limited to 40 requests every 10 seconds. The async functionality
# works, but often exceeds the rate limit.
# Read more: https://developers.themoviedb.org/3/getting-started/request-rate-limiting
# q = Queue(maxsize=2)
# num_threads = 1

# TODO: Async had to be disabled in order to run on TravisCI
#       because of rate limiting.
def lookup_async(film):
    # while True:
    # film = q.get()
    
    try:
        film.search_tmdb()

    # TODO: Figure out which HTTPError is actually being thrown, and 
    # which module it belongs to so we can inspect the X-Rate-Limit
    # header.
    except Exception:
        time.sleep(5.0)
        film.search_tmdb()

    print('█', end='')

    # TODO: Add % calculator and print.
    sys.stdout.flush()
    # q.task_done()

    # TODO: A more graceful way of handling rate limiting in TravisCI.
    if os.environ.get('TMDB_KEY') is not None:
        time.sleep(0.5)

class FylmTestCase(unittest.TestCase):

    def test_valid_films(self):

        print_title('Film.is_valid')

        # Assert that we're getting the expected number of valid films.
        self.assertEqual(len(valid_films), valid_films_count)

    # @unittest.skip("Skip long running test_search_tmdb")
    def test_search_tmdb(self):

        # Look up films by name from TMDb and update title
        print_title('Film.search_tmdb()')

        print('Searching {} titles (this may take several minutes), please wait...'.format(len(valid_films)))

        # TODO: Debug this and figure out if we can improve the thread limiting to match the API's rate limit header
        # for _ in range(num_threads):
        #     t = threading.Thread(target=lookup_async, args=(q,))
        #     t.daemon = True
        #     t.start()

        for film in valid_films:
            # q.put(film)
            lookup_async(film)

        # Retrieve finished threads
        # q.join()
        sys.stdout.write("\033[F") # back to previous line
        sys.stdout.write("\033[K") # clear line

        for film in valid_films:
            matching_tests = filter(lambda x: x.expected_title == film.title, tests_map)
            if len(matching_tests) == 0:
                raise Exception('No matching tests found for "{}" (expected {}); check that there is a matching title property in files.json'.format(film.title, x.expected_title))

            # Get the first matching title in the tests map
            test_film = matching_tests[0]

            if film.title != test_film.expected_title:
                print(' 𝗑 fail  {}\n'.format(film.original_filename))
                print('\n'.join("%s: %s" % item for item in vars(film).items()) + '\n')
            self.assertIsNotNone(film.title)
            self.assertEqual(film.title, test_film.expected_title)

            if film.tmdb_id != test_film.expected_id:
                print(' 𝗑 fail  {}\n'.format(film.original_filename))
                print('\n'.join("%s: %s" % item for item in vars(film).items()) + '\n')
            self.assertIsNotNone(film.tmdb_id)
            self.assertEqual(film.tmdb_id, test_film.expected_id)

            self.assertIsNotNone(film.year)
            print(" ✓ pass   {} {} {} {}".format(film.title.ljust(40)[:40], str(film.year).ljust(6)[:6], str(film.tmdb_id).ljust(10)[:10], film.original_filename))
        for not_a_film in list(set(films) - set(valid_films)):
            print(" ✓ pass   {} {}".format(not_a_film.ignore_reason, not_a_film.original_filename))
            self.assertIsNone(not_a_film.tmdb_id)

    def test_title_the(self):
        # Check that films beginning with 'The' have it moved to the end, ', The'
        print_title('Film.title_the')
        for film in films:
            if not film.should_ignore and ', the' in film.title_the.lower():
                self.assertFalse(film.title_the.lower().startswith('the '))
                self.assertTrue(film.title_the.lower().endswith(', the'))

    def test_year(self):
        # Check that year is detected correctly
        print_title('Film.year')
        for film in films:
            if film.year is not None:
                self.assertGreaterEqual(film.year, 1910)
                self.assertLess(film.year, 2160)
                self.assertNotEqual(film.year, 2160)
                self.assertNotEqual(film.year, 1080)
                self.assertNotEqual(film.year, 720)

    def test_quality(self):
        # Check that quality is detected correctly
        print_title('Film.quality')
        for film in films:
            if film.quality is not None:
                self.assertIn(film.quality, ['720p', '1080p', '2160p'])

    def test_edition(self):
        # Check that editions, when detected, are set correctly and cleaned from original string
        print_title('Film.edition')
        for film in films:
            for key, value in config.edition_map:
                rx = re.compile(r'\b' + key + r'\b', re.I)
                if re.search(rx, film.original_filename):
                    self.assertEqual(film.edition, value)
                    self.assertFalse(re.search(rx, film.title))
                    break

    def test_is_file_dir(self):
        # Check file extensions
        print_title('Film.is_dir, Film.is_file')
        for film in films:
            if film.is_file:
                self.assertTrue(film.ext is not None and [film.ext in config.video_exts + config.extra_exts])
            elif film.is_dir:
                self.assertEqual(film.ext, None)

if __name__ == '__main__':
    unittest.main()
