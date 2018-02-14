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

"""Fylm is a simple command line app for renaming and filing films.

Fylm searches a given directory list for valid movie files, looks them up
on TMDb (themoviedb.org), and renames them according to the TMDb title.

Because it runs solely in the command line (and autonomously), you can
easily wire it up as a post script for services like SABnzbd.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
import sys

from fylmlib.config import config
from fylmlib.console import console
from fylmlib.processor import process
from fylmlib.duplicates import duplicates
import fylmlib.operations as ops
import fylmlib.notify as notify
import fylmlib.counter as counter

__version__ = '0.2.3-alpha'

def main():
    """Main program."""

    try:
        # Initialize the success counter.
        counter.count = 0

        # Print the welcome message to the console.
        console.start()

        # Attempt to create the destination dirs if they does not exist.
        for _, dr in config.destination_dirs.items():
            ops.dirops.create_deep(dr)

        # Verify that destination paths exist.
        ops.dirops.verify_paths_exist(list(config.destination_dirs.values()))

        # TODO: add interactive option to skip, confirm, and correct matches
        # TODO: add recursive searching inside poorly named folders

        # Iterate each path in the config.source_dirs array. 
        for source_dir in config.source_dirs:

            # Verify that source path exists.
            ops.dirops.verify_paths_exist([source_dir])

            # Retrieve a list of films from the current source dir.
            films = ops.dirops.get_new_films(source_dir)

            # Iterate each film.
            for film in films:

                # If the film should be ignored, print the reason why, and skip.
                if film.should_ignore is True:
                    console.skip(film)
                    continue

                # Print the film details to the console.
                console.film_loaded(film)

                # Search TMDb for film details (if enabled).
                film.search_tmdb()

                # If the search failed, or TMDb is disabled, print why, and skip.
                if film.tmdb_id is None and config.tmdb.enabled is True:
                    console.skip(film, film.ignore_reason)
                    continue

                # If the lookup was successful, print the results to the console.
                console.lookup_result(film)

                # If duplicate checking is enabled and the film is a duplicate, abort,
                # *unless* overwriting is enabled. `is_duplicate` will always return
                # false if duplicate checking is disabled.
                if film.is_duplicate:
                    console.duplicates(film)

                    if not duplicates.should_keep(film):
                        continue
                    
                    duplicates.delete_unwanted(film)

                # Attempt to Create the destination folder (fails silently if it
                # already exists).
                ops.dirops.create_deep(film.destination_dir)

                # If it is a file and as a valid extension, process it as a file
                if film.is_file and film.has_valid_ext:
                    process.file(film)

                # Otherwise if it's a folder, process it as a folder containing
                # potentially multiple related files.
                elif film.is_dir:
                    process.dir(film)

        # When all films have been processed, notify Plex (if enabled).
        notify.plex()

        # Print the summary.
        console.end(counter.count)
    
    except (KeyboardInterrupt, SystemExit):
        console.exit_early()
    except IOError as e:
        console.red('IOError: %s' % e)
        import traceback
        traceback.print_exc()
    finally:
        # Don't leave the cursor hidden
        from fylmlib.cursor import cursor
        cursor.show()

if __name__ == "__main__":
    main()