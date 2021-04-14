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

"""Fylm is a simple command line app for renaming and filing films.

Fylm searches a given directory list for valid movie files, looks them up
on TMDb (themoviedb.org), and renames them according to the TMDb title.

Because it runs solely in the command line (and autonomously), you can
easily wire it up as a post script for services like SABnzbd.
"""

import os
import sys
import asyncio
from contextlib import suppress

import fylmlib.config as config
from fylmlib import Console
from fylmlib import Processor
# from fylmlib import
from fylmlib import Notify
import fylmlib.counter as counter
from fylmlib import Cursor

__version__ = '0.4.0-beta'

def main():
    """Main program."""
    
    # Load config the first time
    config.load()

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

        # Verify that source path(s) exist.
        ops.dirops.verify_root_paths_exist(config.source_dirs)

        # Retrieve a list of films from the current source dir(s) and process each film.
        processor.iterate(ops.dirops.get_new_films(config.source_dirs))

        # When all films have been processed, notify Plex (if enabled).
        notify.plex()

        # Print the summary.
        console().print_exit(counter.count)
    
    except (KeyboardInterrupt, SystemExit):
        loop = asyncio.get_event_loop()
        with suppress(asyncio.CancelledError):
            pending = asyncio.Task.all_tasks()
            loop.run_until_complete(asyncio.gather(*pending))
            loop.close()
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
        cursor.show()

if __name__ == "__main__":
    main()
