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

"""Console output and log proxy handler for Fylm.

This module handles all the console output for the app, and proxies some
output to the log module.

    console: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import datetime
import os
import sys

from colors import color

from fylmlib.pyfancy import *
import fylmlib.config as config
from fylmlib.log import log
from fylmlib.ansi import ansi
import fylmlib.formatter as formatter
import fylmlib.progress as progress

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
        self.add('    → %s' % s)
        return self

    def print(self, should_log=True):
        if should_log:
            log.info(self._pltxt.get())
        self._fmtxt.output()

class console(console):

    def print_welcome(self):
        """Print and log the initial welcome header.
        """

        # Start log section header
        log.info('%s %s %s' % (('-'*40), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ('-'*40)))
        
        c = console().pink("\nFylm is scanning %s\n" % ', '.join(config.source_dirs))

        if config.test:
            c.bold().purple('\n★ Test mode (no changes will be made)')
        if config.force_lookup:
            c.bold().yellow('\n★ Force lookup mode (smart folder checking is disabled, assuming all folders are films)')
        if config.overwrite_existing:
            c.bold().yellow('\n★ Overwrite mode enabled (identically named existing files will be silently overwritten)')
        if config.test or config.force_lookup or config.overwrite_existing:
            c.add('\n').print()

    def print_exit(self, count):
        """Print and log the closing summary prior to exit.

        Args:
            count: (int) Count of successful moves/renames, from counter module.
        """
        s = "%sSuccessfully %s %s film%s" % (
            '(Test) ' if config.test else '', 
            'renamed' if config.rename_only else 'moved', 
            count, 
            '' if count == 1 else 's')
        
        c = console()
        if config.test is True:
            c.purple(s)
        else:
            c.pink(s)
        c.print()

    def print_exit_early(self):
        """Print the early exit message.
        """
        console().pink('\n\nBye, Fylicia.').print()

    def print_film_header(self, film):
        """When a film is loaded, print a title header.

        Args:
            film: (Film) film to pass to debug calls.
            ignore: (bool) True if the film should be ignored, else False
        """

        # Print original filename and size.
        c = console().bold(' ')
        if film.should_ignore and (config.interactive is False or not (film.ignore_reason or '').startswith('Unknown')):
            c.red()
        c.add(film.original_filename).add(film.ext or '')
        c.reset().dark_gray(' (%s)' % formatter.pretty_size(film.size_of_largest_video))
        c.print()

    def print_search_result(self, film):
        """Print and log film search result details.

        Args:
            film: (Film) Film to print/log.
        """
        
        # Only print lookup results if TMDb searching is enabled.
        if config.tmdb.enabled is True:
            if film.tmdb_id is not None:
                c = console().indent()
                c.green('✓ %s (%s)' % (film.title, film.year))
                c.dark_gray(' [%s] %s match' % (film.tmdb_id, formatter.percent(film.title_similarity)))
                c.print()
            else:
                console().red().indent('× %s (%s)' % (film.title, film.year)).print()
   
    def print_skip(self, film):
        """Print and log reason for skipping a film. Prints file in red, reason in dark gray.

        Args:
            film: (Film) Film that was skipped.
        """
        console().red().dim().indent().red().dim(film.ignore_reason).print()

    def print_duplicates(self, film):
        """Print any duplicates found to the console.

        Args:
            film: (Film) Inbound film that has been marked as duplicate.
            size: ([Film]) Array of duplicate Film objects.
        """

        # Import duplicates' should_replace function here to prevent circular imports.
        from fylmlib.duplicates import duplicates

        if len(film.duplicates) > 0:
            
            console().blue().indent().add('%s duplicate%s found:' % (
                len(film.duplicates), 
                '' if len(film.duplicates) == 1 else 's')).print()

            if config.interactive is False:

                for d in film.duplicates:
    
                    size_diff = formatter.pretty_size_diff(film.source_path, d.source_path)
                    pretty_size = formatter.pretty_size(d.size)
                    should_replace = duplicates.should_replace(film, d)
                    should_keep_both = duplicates.should_keep_both(film, d)

                    c = console().blue().indent()

                    if should_replace or should_keep_both:
                        c.add('  %s' % 'Replacing ' if should_replace else 'Keeping ')
                        c.add("'%s'" % os.path.basename(d.source_path))
                        c.add(' (%s)' % pretty_size)
                        c.dark_gray(' [%s]' % size_diff)
                    else:   
                        c.red('  Ignoring because ')
                        c.add("'%s'" % os.path.basename(d.source_path))
                        c.red("'%s' (%s) is %s" % (
                            os.path.basename(d.source_path), 
                            pretty_size,
                            size_diff))

                    c.print()

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
        console().red('      %s' % s).print()

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

        c = console().gray('      %s)' % idx)
        if choice.startswith('['):
            c.dark_gray(' %s' % choice)
        else:
            c.gray(' %s' % choice)
        c.print()

    def print_move_or_copy(self, src, dst_path, dst):

        # Do not print if source and destination root path are the same.
        if src == dst_path:
            return

        from fylmlib.operations import dirops
        console().gray().indent("%s %s to %s" % (
            "Copying" if (config.safe_copy or not dirops.is_same_partition(src, dst)) else 'Moving', 
            os.path.basename(src),
            os.path.dirname(dst))).print()

    def print_copy_progress_bar(self, copied, total):
        """Print progress bar to terminal.
        """
        print('      ' + progress.progress_bar(100 * copied / total), end='\r')
        sys.stdout.flush()

    @classmethod
    def get_input(cls, prompt):
        """Prompt the user for input

        Args:
            prompt: (str, utf-8) Query to prompt.
        """
        return input(color('    » ', fg=ansi.white) + color(prompt, fg=ansi.pink))

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
            print(color(s, fg=ansi.debug, style='bold'))

    @classmethod
    def error(cls, s, x=Exception):
        """Print error details.

        Args:
            s: (str, utf-8) String to print
        """
        log.error(s)
        print(color(s, fg=ansi.error, style='bold'))
        if x:
            x(s)