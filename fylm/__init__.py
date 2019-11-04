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

import fylmlib.config as config
from fylmlib.console import console
from fylmlib.processor import processor
import fylmlib.operations as ops
import fylmlib.notify as notify
import fylmlib.counter as counter

__version__ = '0.2.7-beta'

def main():
    """Main program."""

    try:
        # Initialize the success counter.
        counter.count = 0

        # Print the welcome message to the console.
        console().print_welcome()

        # Attempt to create the destination dirs if they does not exist.
        for _, dr in config.destination_dirs.items():
            ops.dirops.create_deep(dr)

        # Verify that destination paths exist.
        ops.dirops.verify_root_paths_exist(list(config.destination_dirs.values()))

        # Load duplicates before film processing begins.
        ops.dirops.get_existing_films(config.destination_dirs)

        # TODO: add recursive searching inside poorly named folders

        # Verify that source path(s) exist.
        ops.dirops.verify_root_paths_exist(config.source_dirs)

        # Retrieve a list of films from the current source dir(s) and process each film.
        processor.iterate(ops.dirops.get_new_films(config.source_dirs))

        # When all films have been processed, notify Plex (if enabled).
        notify.plex()

        # Print the summary.
        console().print_exit(counter.count)
    
    except (KeyboardInterrupt, SystemExit):
        console().print_exit_early()
    except (IOError, OSError) as e:
        console().error(f'{type(e).__name__}: {e}')
        if config.debug or config.errors:
            import traceback
            traceback.print_exc()
    except Exception as e:
        console().error(f'{(type(e).__name__, e)}: {type(e)}')
        if config.debug or config.errors:
            import traceback
            traceback.print_exc()
    finally:
        # Don't leave the cursor hidden
        from fylmlib.cursor import cursor
        cursor.show()

if __name__ == "__main__":
    main()