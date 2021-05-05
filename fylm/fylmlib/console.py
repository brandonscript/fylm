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

"""Console output and log proxy handler for Fylm.

This module handles all the console output for the app, and proxies some
output to the log module.

    Console: the main class exported by this module.
"""

import os
import re
import sys
import itertools
import shutil
import math
import time
from pathlib import Path
from datetime import datetime

from colors import color

import fylmlib.config as config
from fylmlib.pyfancy import *
from fylmlib.ansi import ansi
from fylmlib.enums import *
from fylmlib.constants import *
from fylmlib import patterns, Log, Format as ƒ, Progress

class Console(object):
    """Main class for console output methods.

    All public methods should chain together to form a builder pattern, e.g.:

    Console()
        .white('white')
        .blue(' blue')
        .red(' red')
        .bold().red(' bold red')
        .dark_gray()
        .dim(' dim').print()

    """
    def __init__(self, s=''):

        # Coerce to string
        s = f"{s}"

        # Formatted string
        self._fmtxt = pyfancy(s)

        # Plaintext string
        self._pltxt = pyfancy(s)

        # Color
        self._color = None

        # Style
        self._style = []

        # Inject ANSI helper functions
        for c in vars(ansi):
            self._colorizer(c)
            
    def __repr__(self):
        return str(self._pltxt)

    def _colorizer(self, c):
        def add(s=''):
            if c is not None:
                self._color = c
            self.add(s)
            return self
        self.__setattr__(c, add)

    def add(self, s=''):
        s = f"{s}"
        style = '+'.join(list(set(self._style))) if self._style else None
        self._fmtxt.add(color(s, fg=getattr(ansi, self._color or 'white'), style=style))
        self._pltxt.add(s)
        return self

    def get(self):
        return self._fmtxt.get()

    def bold(self, s=''):
        self._style.append('bold')
        self.add(s)
        return self

    def dim(self, s=''):
        self._style.append('faint')
        self.add(s)
        return self

    def reset(self, s=''):
        self._color = None
        self._style = []
        self.add(s)
        return self

    def indent(self, s=''):
        self.add(f'    → {s}')
        return self

    def print(self, should_log=True, override_no_console=False, end=None):
        if config.no_console and not override_no_console:
            return
        if should_log:
            Log.info(self._pltxt.get())
        if config.plaintext:
            print(patterns.ANSI_ESCAPE.sub('', self._pltxt.get()), end=end)
        else:
            self._fmtxt.output(end=end)

    """Helper methods for Console class.
    """

    def print_welcome(self):
        """Print and log the initial welcome header.
        """
        
        tsize = shutil.get_terminal_size((80, 20))

        # Start log section header
        date = f' {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} '
        dashes = "-"*40
        Log.info(f'{dashes}{date}{dashes}')
        
        dirs = f'\n{" "*17}'.join((str(d) for d in config.source_dirs))
        c = Console().pink(f"\nFylm is scanning {dirs}")

        if config.test or config.force_lookup or config.duplicates.force_overwrite:
            c.bold().add('\n')
        if config.test:
            c.purple('\n★ Test mode (no changes will be made)')
        if config.force_lookup:
            c.yellow('\n★ Force lookup mode (smart folder checking is disabled, assuming all folders are films)')
        if config.duplicates.force_overwrite:
            c.yellow('\n★ Force overwrite mode enabled (all identically named existing files will be silently overwritten, regardless of size)')
        
        c.print(override_no_console=True)

    def print_exit(self, count):
        """Print and log the closing summary prior to exit.

        Args:
            count: (int) Count of successful moves/renames, from counter module.
        """

        s = f"Successfully {'renamed' if config.rename_only else 'moved'}" \
                f" {count} {ƒ.pluralize('film', count)}" if count > 0 else "No films moved"
        
        c = Console()
        if config.test is True:
            c.purple(f'\n(Test) {s}')
        else:
            c.pink(f"\n{s}")
        c.print(override_no_console=True)

    def print_exit_early(self):
        """Print the early exit message.
        """
        Console().pink('\n\nThat\'s it, I quit.').print()

    @staticmethod
    def print_film_header(film):
        """Print the film header.

        Args:
            film (Film) for which to print details.
        """

        c = Console('\n')
        
        # Interactive mode
        if config.interactive:
            Console().gray(f'\n{INDENT}{film.name}').white(S.size(film)).print()
            Console().dark_gray(f'{INDENT}{film.src.parent}').print(end="")
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
            c.reset().white(S.size(film))
        
        if film.tmdb.id:
            c.gray(S.tmdb_id(film))
            c.dark_gray(S.percent(film))
        c.print()
    
    @staticmethod
    def print_interactive_success(film):
        c = Console().green(f' {ARROW} {S.name(film)}')
        if film.tmdb.id:
            c.gray(S.tmdb_id(film))
            c.dark_gray(S.percent(film))
        c.print()
        
    @staticmethod
    def print_interactive_uncertain(film):
        Console().light_blue(f' {UNCERTAIN} {film.title} ({film.year})').print()
        
    @staticmethod
    def print_src_dst(film):
        """Print the src and dst.

        Args:
            film (Film) for which to print details.
        """
        
        if config.interactive:
            return
        
        Console().dark_gray(f'{INDENT}{film.src}').print()
        if not film.should_ignore:
            Console().gray(f'{INDENT}{film.dst}').print()
   
    @staticmethod
    def print_skip(film):
        """Print and log reason for skipping a film. Prints file in red, reason in dark gray.

        Args:
            film: (Film) Film that was skipped.
        """
        if film.should_ignore:
            if config.interactive and film.ignore_reason == IgnoreReason.SKIP:
                Console().dark_gray('      Skipped').print()
            else:
                Console().red().dim(
                    f'{INDENT}Ignoring because {film.ignore_reason.display_name}').print()

    @staticmethod
    def print_duplicates(film: 'Film'):
        """Print any duplicates found to the Console.

        Args:
            film: (Film) Inbound film for which one or more duplicates has been detected.
        """

        # Import duplicates' should_replace function here to prevent circular imports.
        if not config.duplicates.enabled:
        # FIXME:
            duplicate_count = len(film.verified_duplicate_files)

            if duplicate_count > 0:
                
                c = Console().blue().indent().add(f"{duplicate_count} {ƒ.pluralize('duplicate', duplicate_count)} found")

                if config.interactive is True:
                    c.add(' for ').light_blue(f'{film.all_valid_files[0].new_filename_and_ext}')
                    c.blue(':').print()
                else:
                    c.add(':').print()

                if config.interactive is False:
                    Console.print_interactive_duplicates(film)

    def print_interactive_duplicates(self, film):
        """Print a duplicate line.

        Args:
            film: (Film.File) The film object for which to print duplicates
        """

        # In case there are multiple video files in the original film, 
        # we need to process each separately.
        for v in film.video_files:

            # Veriified duplicates exist on the filesystem
            for d in film.verified_duplicate_files:

                # Print a line of detail for each duplicate
                size_diff = ƒ.pretty_size_diff(v.source_path, d.source_path)
                pretty_size = ƒ.pretty_size(d.size)
                should = d.duplicate

                c = Console()
                r = "" 
                p = "  "
                if config.interactive:
                    c.yellow()
                    r = "Recommend "
                    p = ""
                if should == Should.UPGRADE:
                    c.blue() if not config.interactive else c.yellow()
                    c.indent(p).add(f"{r}upgrading ".capitalize())
                elif should == Should.KEEP_BOTH:
                    c.purple() if not config.interactive else c.yellow()
                    c.indent(p).add(f"{r}keeping both this and ".capitalize())
                elif should == Should.IGNORE:
                    if config.duplicates.force_overwrite is True and config.interactive is False:
                        c.yellow()
                        c.indent(p).add(f"(Force) replacing ")
                    else:
                        c.red()
                        c.indent(p).add(f"{r}ignoring, not an upgrade for ".capitalize())
                else:
                    c.gray(p).indent()

                c.add(f"'{os.path.basename(d.source_path)}' ({pretty_size})")
                c.dark_gray(' [')
                if d.duplicate_reason != '':
                    c.add(f'{d.duplicate_reason}, ')
                c.add(f'{size_diff}]')
                c.print()

                # If in non-interactive mode, if a duplicate of equal or greater quality is detected,
                # we know this film won't be moved, so we can just display this duplicate.
                if not config.interactive and should == Should.IGNORE:
                    break

    def print_ask(self, s):
        """Print an interactive question.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Console().yellow().indent().add(s).print()

    def print_interactive_error(self, s):
        """Print an interactive error.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Console().red(f'      {s}').print()

    def print_interactive_skipped(self):
        """Print an interactive skip message.
        """
        Console().dark_gray('      Skipped').print()

    def print_choice(self, idx, choice):
        """Print a question choice.

        Args:
            idx: (int or str) Index of choice (first letter or number)
            choice: (str, utf-8) Choice to print/log.
        """

        c = Console().gray(f'      {idx})')
        if choice.startswith('['):
            c.dark_gray(f' {choice}')
        else:
            match = re.search(patterns.TMDB_ID, choice)
            tmdb_id = match.group('tmdb_id') if match else ''
            c.gray(f" {re.sub(patterns.TMDB_ID, '', choice)}")
            c.dark_gray(tmdb_id)
        c.print()

    def print_move_or_copy(self, src, dst_path, dst):

        # Do not print if source and destination root path are the same.
        if src == dst_path:
            return

        from fylmlib.operations import dirops
        Console().gray().indent(
            f"{'Copying' if (config.safe_copy or not dirops.is_same_partition(src, dst)) else 'Moving'}" \
            f" '{os.path.basename(dst)}' to {os.path.dirname(dst)}"
        ).print()

    def print_copy_progress_bar(self, copied, total):
        """Print progress bar to terminal.
        """
        if not config.plaintext:
            print('      ' + Progress.bar(100 * copied / total), end='\r')
            # Catch stdout if None
            if sys.stdout:
                sys.stdout.flush()

    @classmethod
    def get_input(cls, prompt):
        """Prompt the user for input

        Args:
            prompt: (str, utf-8) Query to prompt.
        """
        return input(color('    » ', fg=ansi.white) + color(prompt, fg=ansi.yellow))

    @classmethod
    def clearline(cls):
        """Clears the current printed line."""

        # Clear line, if stdout is not None
        if sys.stdout:
            sys.stdout.write(CURSOR_UP_ONE)
            sys.stdout.write(ERASE_LINE)
            sys.stdout.flush()
        return cls
            
    @classmethod
    def up(cls):
        """Clears the previous printed line."""

        # Clear line, if stdout is not None
        if sys.stdout:
            sys.stdout.write(CURSOR_UP_ONE)
            sys.stdout.flush()
        return cls
            
    @classmethod
    def wait(cls, s: int=0):
        if not config.no_console and not config.plaintext:
            time.sleep(s)
        
    @classmethod
    def slow(cls, s: str='', seconds=0):
        
        if config.debug is True:
            cls().yellow().bold(f'{ WARN }').reset().yellow(
                f" {s} - {round(seconds)} seconds").print()
    
    @classmethod
    def debug(cls, s: str='', end=None):
        """Print debugging details, if config.debug is enabled.

        Args:
            s: (str, utf-8) String to print
        """
        if config.debug is True:
            # TODO: Debug shouldn't also be printing info
            Log.debug(s)
            cls().add('🐞 ').debug(s).print(end=end)

    @classmethod
    def error(cls, s: str='', x: Exception=None):
        """Print error details.

        Args:
            s (str): String to print.
            x (Exception, optional): Exception to raise.
        """
        Log.error(s)
        cls().bold().error(s).print()
        if x:
            raise type(x)(s)

    class strings:
        
        @staticmethod
        def size(film): return f' ({film.size.pretty()})'
        
        @staticmethod
        def tmdb_id(film): return f' [{film.tmdb.id}] '
        
        @staticmethod
        def percent(film): return f'{ƒ.percent(film.tmdb.title_similarity)}% match'
        
        @staticmethod
        def name(film): return (Path(film.main_file.new_name).stem 
                        if not film.should_ignore else film.name)

S = Console.strings
