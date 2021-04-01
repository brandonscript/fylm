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

"""Console output and log proxy handler for Fylm.

This module handles all the console output for the app, and proxies some
output to the log module.

    console: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import datetime
import os
import re
import sys
import itertools

from colors import color

from fylmlib.pyfancy import *
import fylmlib.config as config
from fylmlib.log import log
from fylmlib.ansi import ansi
import fylmlib.patterns as patterns
import fylmlib.formatter as formatter
import fylmlib.progress as progress
from fylmlib.enums import Should

class console(object):
    """Main class for console output methods.

    All public methods should chain together to form a builder pattern, e.g.:

    console()
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

    def print(self, should_log=True, override_no_console=False):
        if should_log:
            log.info(self._pltxt.get())
        if config.no_console and not override_no_console:
            return
        if config.plaintext:
            print(patterns.ansi_escape.sub('', self._pltxt.get()))
        else:
            self._fmtxt.output()

    """Helper methods for console class.
    """

    def print_welcome(self):
        """Print and log the initial welcome header.
        """

        # Start log section header
        log.info(f'{("-"*40)} {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {("-"*40)}')
        
        dirs = '\n                 '.join(config.source_dirs)
        c = console().pink(f"\nFylm is scanning {dirs}")

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
                f" {count} {formatter.pluralize('film', count)}" if count > 0 else "No films moved"
        
        c = console()
        if config.test is True:
            c.purple(f'\n(Test) {s}')
        else:
            c.pink(f"\n{s}")
        c.print(override_no_console=True)

    def print_exit_early(self):
        """Print the early exit message.
        """
        console().pink('\n\nThat\'s it, I quit.').print()

    def print_film_header(self, film):
        """When a film is loaded, print a title header.

        Args:
            film: (Film) film to pass to debug calls.
            ignore: (bool) True if the film should be ignored, else False
        """
        
        # Print blank line to separate from previous film
        console().print()
        # Print original filename and size.
        c = console().bold(' ')
        if film.should_ignore and (config.interactive is False or not (film.ignore_reason or '').startswith('Unknown')):
            c.red()
        c.add(film.original_basename)
        c.reset().dark_gray(f' ({formatter.pretty_size(film.size)})')
        c.print()
        console().dark_gray().indent(f'in {film.original_path}').print()


    def print_search_result(self, film):
        """Print and log film search result details.

        Args:
            film: (Film) Film to print/log.
        """
        
        # Only print lookup results if TMDb searching is enabled.
        if config.tmdb.enabled is True:
            if film.tmdb_id is not None:
                c = console().indent()
                c.green(f'✓ {film.title} ({film.year})')
                c.dark_gray(f' [{film.tmdb_id}] {formatter.percent(film.title_similarity)}% match')
                c.print()
            else:
                console().red().indent(f'× {film.title} ({film.year})').print()
   
    def print_skip(self, film):
        """Print and log reason for skipping a film. Prints file in red, reason in dark gray.

        Args:
            film: (Film) Film that was skipped.
        """

        console().red().dim().indent().red().dim(film.ignore_reason).print()

    def print_duplicates(self, film: 'Film'):
        """Print any duplicates found to the console.

        Args:
            film: (Film) Inbound film for which one or more duplicates has been detected.
        """

        # Import duplicates' should_replace function here to prevent circular imports.
        from fylmlib.duplicates import duplicates

        duplicate_count = len(film.verified_duplicate_files)

        if duplicate_count > 0:
            
            c = console().blue().indent().add(f"{duplicate_count} {formatter.pluralize('duplicate', duplicate_count)} found")

            if config.interactive is True:
                c.add(' for ').light_blue(f'{film.all_valid_files[0].new_filename_and_ext}')
                c.blue(':').print()
            else:
                c.add(':').print()

            if config.interactive is False:
                self.print_duplicate_lines(film)

    def print_duplicate_lines(self, film):
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
                size_diff = formatter.pretty_size_diff(v.source_path, d.source_path)
                pretty_size = formatter.pretty_size(d.size)
                should = d.duplicate

                c = console()
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
                        c.indent(p).add(f"{r}ignoring; not an upgrade for ".capitalize())
                else:
                    c.gray(p).indent()

                c.add(f"'{os.path.basename(d.source_path)}' ({pretty_size})")
                c.dark_gray(' [')
                if d.upgrade_reason != '':
                    c.add(f'{d.upgrade_reason}, ')
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
        console().yellow().indent().add(s).print()

    def print_interactive_error(self, s):
        """Print an interactive error.

        Args:
            s: (str, utf-8) String to print/log.
        """
        console().red(f'      {s}').print()

    def print_interactive_skipped(self):
        """Print an interactive skip message.
        """
        console().dark_gray('      Skipped').print()

    def print_choice(self, idx, choice):
        """Print a question choice.

        Args:
            idx: (int or str) Index of choice (first letter or number)
            choice: (str, utf-8) Choice to print/log.
        """

        c = console().gray(f'      {idx})')
        if choice.startswith('['):
            c.dark_gray(f' {choice}')
        else:
            match = re.search(patterns.tmdb_id, choice)
            tmdb_id = match.group('tmdb_id') if match else ''
            c.gray(f" {re.sub(patterns.tmdb_id, '', choice)}")
            c.dark_gray(tmdb_id)
        c.print()

    def print_move_or_copy(self, src, dst_path, dst):

        # Do not print if source and destination root path are the same.
        if src == dst_path:
            return

        from fylmlib.operations import dirops
        console().gray().indent(
            f"{'Copying' if (config.safe_copy or not dirops.is_same_partition(src, dst)) else 'Moving'}" \
            f" '{os.path.basename(dst)}' to {os.path.dirname(dst)}"
        ).print()

    def print_copy_progress_bar(self, copied, total):
        """Print progress bar to terminal.
        """
        if not config.plaintext:
            print('      ' + progress.progress_bar(100 * copied / total), end='\r')
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
        """Clears the current printed line.
        """

        # Clear line.
        sys.stdout.write("\033[K")

    @classmethod
    def debug(cls, s):
        """Print debugging details, if config.debug is enabled.

        Args:
            s: (str, utf-8) String to print
        """
        if config.debug is True:
            log.debug(s)
            console().bold().debug(s).print()

    @classmethod
    def error(cls, s, x=Exception):
        """Print error details.

        Args:
            s: (str, utf-8) String to print
            x: (Exception)
        """
        log.error(s)
        console().bold().error(s).print()
        if x:
            x(s)
