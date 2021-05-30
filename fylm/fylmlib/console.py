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

"""Console output and log proxy handler for Fylm.

This module handles all the console output for the app, and proxies some
output to the log module.

    Console: the main class exported by this module.
"""

import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from colors import color
from tinta import Tinta
Tinta.load_colors(Path(__file__).parent.parent / 'colors.ini')

from halo import Halo

import fylmlib.config as config
from .enums import *
from .tools import *
from .constants import *
from . import patterns, Log, Format as ƒ
from . import Progress

class Console():

    @staticmethod
    def welcome():
        """Print and log the initial welcome header.
        """

        # tsize = shutil.get_terminal_size((80, 20))

        # Start log section header
        date = f' {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} '
        dashes = "-"*40
        Log.info(f'{dashes}{date}{dashes}')

        dirs = f'\n{" "*17}'.join((str(d) for d in config.source_dirs))
        c = Tinta().pink(f"\nFylm is scanning {dirs}")

        if config.test or config.force_lookup or config.duplicates.force_overwrite:
            c.bold().add('\n')
        if config.test:
            c.purple('\n★ Test mode (no changes will be made)')
        if config.force_lookup:
            c.yellow('\n★ Force lookup mode (smart folder checking is disabled, assuming all folders are films)')
        if config.duplicates.force_overwrite:
            c.yellow('\n★ Force overwrite mode enabled (all identically named existing files will be silently overwritten, regardless of size)')

        c.print(force=True)

    @staticmethod
    def exit(count):
        """Print and log the closing summary prior to exit.

        Args:
            count: (int) Count of successful moves/renames, from counter module.
        """

        s = f"Successfully {'renamed' if config.rename_only else 'moved'}" \
                f" {count} {ƒ.pluralize('film', count)}" if count > 0 else "No films moved"

        c = Tinta()
        if config.test is True:
            c.purple(f'\n(Test) {s}')
        else:
            c.pink(f"\n{s}")
        c.print(force=True)
        Tinta().pink("Thanks for using Fylm. Be kind, and please rewind.").print()

    @staticmethod
    def exit_early():
        """Print the early exit message.
        """
        Tinta().pink('\n\nThat\'s it, I quit.').print()

    @staticmethod
    def film_header(film: 'Film'):
        c = Tinta('\n')

        header = film.name if film._year else film.main_file.name
        Tinta().gray(f'\n{INDENT}{header}').white(S.size(film)).print(end="")

        # Interactive mode
        if config.interactive:
            if film.should_ignore and not film.ignore_reason in [
                    IgnoreReason.UNKNOWN_YEAR,
                    IgnoreReason.TOO_SMALL,
                    IgnoreReason.NO_TMDB_RESULTS]:
                c.red(f' {FAIL} {S.name(film)}')
            elif film.tmdb.id and film.tmdb.is_instant_match:
                c.green(f' {CHECK} {S.name(film)}')
            else:
                c.light_blue(f' {UNCERTAIN} {S.name(film)}')

        # Automatic mode
        else:
            if film.should_ignore:
                c.red(f' {FAIL} {S.name(film)}')
            else:
                c.green(f' {CHECK} {S.name(film)}')

        if film.tmdb.id:
            c.gray(S.tmdb_id(film))
            c.dark_gray(S.percent(film))
        c.print()

    @staticmethod
    def film_src(film):
        parent = film.src.parent if film._year else film.src
        Tinta().dark_gray(f'{INDENT}{parent}').print()

    @staticmethod
    def interactive_success(film: 'Film'):
        c = Tinta().green(f' {ARROW} {S.name(film)}')
        if film.tmdb.id:
            c.gray(S.tmdb_id(film))
            c.dark_gray(S.percent(film))
        c.print()

    @staticmethod
    def interactive_uncertain(film: 'Film'):
        Tinta().light_blue(f' {UNCERTAIN} {film.title} ({film.year})').print()

    @staticmethod
    def src_dst(film: 'Film'):
        if config.interactive:
            return

        Tinta().dark_gray(f'{INDENT}{film.src}').print()
        if not film.should_ignore:
            Tinta().gray(f'{INDENT}{film.dst}').print()

    @staticmethod
    def skip(film: 'Film'):
        if film.should_ignore:
            if config.interactive and film.ignore_reason == IgnoreReason.SKIP:
                Console.interactive_skipped()
            else:
                Tinta().red().dim(
                    f'{INDENT}Ignoring because {film.ignore_reason.display_name}').print()

    @staticmethod
    def rename_only(film: 'Film'):
        Tinta().red().dim(
            f'{INDENT}Ignoring because {film.ignore_reason.display_name}').print()

    @staticmethod
    def duplicates(new: 'Film.File', duplicates: 'List[Duplicates.Map]'):
        # If any duplicates determine that the current file should be ignored,
        # we only show the skip recommendation.

        if not duplicates:
            return

        c = Tinta().blue(f"{INDENT}Found {ƒ.num_to_words(len(duplicates))} ")
        c.add(f"{ƒ.pluralize('duplicate', len(duplicates))} for '{new.name}'")
        c.dim(f" ({new.size.pretty()})").print()

        keeps = list(filter(lambda mp: mp.action == Should.KEEP_EXISTING, duplicates))
        duplicates = keeps[:1] if keeps else duplicates

        def fixcase(s): return s.capitalize() if not config.interactive else s

        for mp in duplicates:

            c = Tinta(INDENT)
            ar = f" {ARROW} " if not config.interactive else ''
            if config.interactive:
                c.red() if mp.action == Should.KEEP_EXISTING else c.yellow()
                c.add(ar).add("Suggest ")
            if mp.action == Should.UPGRADE:
                c.blue() if not config.interactive else c.yellow()
                c.add(ar).add(fixcase("upgrading "))
            elif mp.action == Should.KEEP_BOTH:
                c.purple() if not config.interactive else c.yellow()
                c.add(ar).add(fixcase("keeping both this and "))
            elif mp.action == Should.KEEP_EXISTING:
                if (config.duplicates.force_overwrite is True
                    and config.interactive is False):
                    c.yellow(ar).add(f"(Force) replacing ")
                else:
                    c.red(ar).add(fixcase(
                        f"skipping, not an upgrade for existing file of "\
                        f"the same quality\n{INDENT*2}"))
            else:
                c.gray(ar)

            c.add(f"'{mp.duplicate.name}' ({mp.duplicate.size.pretty()})")
            c.dark_gray(' ')
            if mp.reason == ComparisonReason.IDENTICAL:
                c.add('Identical')

            # They're different, but we can't determine if one is better than the other
            elif mp.result == ComparisonResult.DIFFERENT:
                reason = f'Different {mp.reason.display_name.lower()}'
                if mp.reason == ComparisonReason.HDR:
                    reason = 'HDR' if mp.duplicate.is_hdr else ''
                c.add(reason)

            # For human readable output, we need to reverse the descriptor
            # because if "new" is better than "duplicate", we describe the inverse
            # for the duplicate.
            elif mp.reason == ComparisonReason.SIZE:
                c.add(ƒ.pretty_size_diff(mp.new.size.value, mp.duplicate.size.value))
            else:
                c.add(f'{"Higher" if mp.result == ComparisonResult.LOWER else "Lower"}')
                c.add(f' {mp.reason.display_name.lower()}')
            c.print()

            # If in non-interactive mode, if a duplicate of equal or greater quality is detected,
            # we know this film won't be moved, so we can just display this duplicate.
            if not config.interactive and mp.action == Should.KEEP_EXISTING:
                break

    @staticmethod
    def ask(s):
        """Print an interactive question.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Tinta().yellow(INDENT, s, sep='').print()

    @staticmethod
    def io_reject(verb, dst):
        if config.rename_only:
            verb = 'rename'
        Tinta().red(INDENT, f"Unable to {verb}, a file with the same name ",
                      f"already exists in\n{INDENT}'{dst.parent}'.", sep='').print()


    @staticmethod
    def interactive_error(s):
        """Print an interactive error.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Tinta().red(f'      {s}').print()

    @staticmethod
    def interactive_skipped():
        """Print an interactive skip message.
        """
        Tinta().dark_gray(f'{INDENT}Skipped').print()

    @staticmethod
    def choice(idx, choice):
        """Print a question choice.

        Args:
            idx: (int or str) Index of choice (first letter or number)
            choice: (str, utf-8) Choice to print/log.
        """

        c = Tinta().white(INDENT_WIDE, f'{idx})')
        if choice.startswith('['):
            c.dark_gray(f' {choice}')
        else:
            match = re.search(patterns.TMDB_ID, choice)
            tmdb_id = match.group('tmdb_id') if match else ''
            c.light_gray(f" {re.sub(patterns.TMDB_ID, '', choice)}")
            c.dark_gray(tmdb_id)
        c.print()

    @staticmethod
    def copy_progress_bar(copied, total):
        """Print progress bar to terminal.
        """
        if not config.plaintext:
            print(INDENT + Progress.bar(100 * copied / total), end='\r')
            # Catch stdout if None
            if sys.stdout:
                sys.stdout.flush()

    @staticmethod
    def get_input(cls, p):
        """Prompt the user for input

        Args:
            p (str): Query to print.
        """
        return input(color(PROMPT, fg=Tinta.colors.white) + color(p, fg=Tinta.colors.yellow))

    @staticmethod
    def wait(s: int=0):
        if not config.no_console and not config.plaintext:
            time.sleep(s)

    @staticmethod
    def slow(s: str='', seconds=0):
        if config.debug is True:
            Tinta().yellow().bold(f'{ WARN }').reset().yellow(
                f" {s} - {round(seconds)} seconds").print()

    @staticmethod
    def debug(s: str='', end=None):
        """Print debugging details, if config.debug is enabled.

        Args:
            s: (str, utf-8) String to print
        """
        if config.debug is True:
            # TODO: Debug shouldn't also be printing info
            Log.debug(s)
            Tinta().add('🐞 ').debug(s).print(end=end)

    @staticmethod
    def error(s: str='', x: Exception=None):
        """Print error details.

        Args:
            s (str): String to print.
            x (Exception, optional): Exception to raise.
        """
        Log.error(s)
        Tinta().bold().error(s).print()
        if x:
            raise type(x)(s)

    @staticmethod
    def spinner(s: str = '') -> Halo:
        halo = Halo()
        if (not config.no_console
            and not config.plaintext
            and not config.debug):
            halo = Halo(text=s,
                spinner='dots',
                color='yellow',
                text_color='yellow')
        else:
            halo.start = lambda: Tinta(s).print()
            halo.stop = lambda: None
        return halo

    class strings:

        @staticmethod
        def size(film: 'Film'): return f' ({film.size.pretty()})'

        @staticmethod
        def tmdb_id(film: 'Film'): return f' [{film.tmdb.id}] '

        @staticmethod
        def percent(film: 'Film'): return f'{ƒ.percent(film.tmdb.title_similarity)}% match'

        @staticmethod
        def name(film: 'Film'): return (Path(film.main_file.new_name).stem
                        if not film.should_ignore else film.name)

        @staticmethod
        def verb(film: 'Film') -> Tuple[str, str]:
            from fylmlib.filmpath import Info
            if Info.will_copy(film):
                return ('copy', 'copied', 'copying')
            elif config.rename_only:
                return ('rename', 'renamed', 'renaming')
            else:
                return ('move', 'moved', 'moving')

S = Console.strings
