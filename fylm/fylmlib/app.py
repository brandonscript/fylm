#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

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

"""Main application logic.

This module scans for and processes films.

    processor: the main class exported by this module.
"""

from timeit import default_timer as timer

import fylmlib.config as config
import fylmlib.counter as counter
from .enums import *
from .tools import *
from .constants import *

from . import Console, Find, Delete
from . import Notify, TMDb
from . import Format as ƒ
from . import Interactive, Duplicates
from . import Film, FilmPath
from .console import Tinta
Info = FilmPath.Info

QUEUE = []
MOVED = []


class App:
    """Main class for scanning for and processing films.

    All methods are class methods, thus this class should never be instantiated.
    """

    @staticmethod
    def run():
        """Main entry point for Fylm."""

        counter.COUNT = 0

        # Print the welcome message to the console.
        Console.welcome()

        filmroots = list(
            filter(lambda f: f.is_filmroot, map(Film, Find.new())))
        NEW = list(Find.sync_parallel(
            filmroots, attrs=['filmrel', 'year', 'size']))
        if len(NEW) == 0:
            return App.end()

        Tinta().pink(
            f"Found {len(NEW)} possible new {ƒ.pluralize('film', len(NEW))}"
        ).print()

        if config.tmdb.enabled:

            # Search TMDb
            start = timer()
            spinner = Console.spinner('Searching TMDb...')
            spinner.start()

            TMDb.Search.parallel(*NEW)
            spinner.stop()

            Tinta().green(f'{CHECK} Done searching TMDb'
                          ).dark_gray(f'({round(timer() - start)} seconds)'
                                      ).print()

            Console.wait(1.5)
            Tinta.clearline()

        NEW = sorted([f for f in NEW if not f.should_hide],
                     key=lambda f: f.title.lower())

        for film in NEW:

            if not film.exists():
                film.ignore_reason = IgnoreReason.DOES_NOT_EXIST

            Console.film_header(film)
            Console.film_src(film)

            Interactive.lookup(film)
            Interactive.handle_duplicates(film)

            if film.should_ignore is True:
                Console.skip(film)
                continue

            Duplicates.handle(film)

            if not film.should_ignore:
                QUEUE.append(film)

            if not Info.will_copy(film) or config.rename_only:
                # Process the queue immediately
                App.process_queue()

        # Process remaining queue items (or all, if copying)
        App.process_queue()

        # Cleanup
        to_clean = [f for f in map(lambda f: Film(f.src), MOVED)
                    if iterlen(f.wanted_files) == 0]
        cleaned = Delete.paths(*to_clean)

        return App.end()

    @staticmethod
    def process_queue():
        """Process the move queue"""

        if len(QUEUE) > 0:
            Tinta().pink(f"\nPreparing to move",
                         len(QUEUE),
                         f"{ƒ.pluralize('film', len(QUEUE))}...").print()

        while len(QUEUE) > 0:
            film = QUEUE.pop(0)
            _, verbed, _ = Console.strings.verb(film)

            if Info.will_copy(film):
                Console.film_header(film)

            if not film.exists():
                Tinta().yellow(
                    f"{INDENT}'No longer exists or cannot be accessed.").print()
                continue

            if film.src == film.dst:
                Tinta(f'{INDENT}Already {verbed}').print()
                continue

            film.rename() if config.rename_only else film.move()

            did_move = [f.did_move for f in film.files]

            if all(did_move):
                Tinta().dark_gray(f'{INDENT}{verbed.capitalize()}',
                                  f'{ARROW} {film.dst}').print()
                counter.add(len(did_move))

                Duplicates.delete_upgraded()
                if (config.remove_source
                    and film.is_dir()
                        and film.src != film.dst):
                    Console.debug(f"Deleting parent folder '{film.src}'")
                    Delete.dir(film.src, force=True)
                MOVED.append(film)

    @staticmethod
    def end():
        # When all films have been processed, notify Plex (if enabled).
        Notify.plex()

        # Print the summary.
        Console.exit(counter.COUNT)

        return MOVED
