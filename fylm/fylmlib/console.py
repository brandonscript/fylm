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
import sys

from colors import color

from fylmlib.pyfancy import *
from fylmlib.config import config
from fylmlib.log import log
from fylmlib.ansi import ansi
import fylmlib.formatter as formatter
import fylmlib.progress as progress

# TODO: Overhaul console to support a set of common patterns, 
# colors, and a more flexible API.

# Define some pretty console output constants
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
DIVIDER = '======================================'
MAIN_PREFIX = ' '
INDENT_PREFIX = '    → '

class console:
    """Main class for console output methods.

    All methods are class methods, thus this class should never be instantiated.
    """
    @classmethod
    def start(cls):
        """Print and log the initial welcome header.
        """
        log.info('{}{}{}'.format(('-'*40), NOW, ('-'*40)))
        log.info('Scanning {}'.format(', '.join(config.source_dirs)))
        print("Fylm is scanning " + ', '.join(config.source_dirs))
        print("Please wait...\n")
        console._notify_test()
        console._notify_force_lookup()
        console._notify_overwrite_existing()

    @classmethod
    def film_loaded(cls, film):
        """When a film is loaded, print and log the file (or dir) name and size.

        Args:
            film: (Film) film to pass to debug calls.
        """
        # Print original filename and size.
        p = pyfancy().bold('{}{}{}'.format(MAIN_PREFIX, film.original_filename, film.ext or ''))
        p.raw().dim(color(' ({})'.format(formatter.pretty_size(film.size_of_largest_video)), fg=ansi.gray))
        p.output()

        log.info('{} ({})'.format(film.source_path, formatter.pretty_size(film.size_of_largest_video)))
        if film.title is not None:
            console.debug('----------------------------')
            console.debug('Init film object:\n')
            console.debug('title\t{}'.format(film.title))
            console.debug('year\t{}'.format(film.year))
            console.debug('edition\t{}'.format(film.edition))
            console.debug('media\t{}'.format(film.media))
            console.debug('quality\t{}'.format(film.quality))
            console.debug('size\t{}'.format(formatter.pretty_size(film.size_of_largest_video)))


    @classmethod
    def skip(cls, film):
        """Print and log reason for skipping a film. Prints file in red, reason in dark gray.

        Args:
            film: (Film) Film that was skipped.
        """
        p = pyfancy().bold().red('{}{}{}'.format(MAIN_PREFIX, film.original_filename, film.ext or ''))
        p.raw().dim(color(' ({})'.format(formatter.pretty_size(film.size_of_largest_video)), fg=ansi.gray))
        p.output()
        pyfancy().red().dim('{}{}'.format(INDENT_PREFIX, film.ignore_reason)).output()
        log.detail("Skipping (%s)" % film.ignore_reason)

    @classmethod
    def lookup_result(cls, film):
        """Print and log film details.

        Args:
            film: (Film) Film to print/log.
        """
        
        # Only print lookup results if TMDb searching is enabled.
        if config.tmdb.enabled is True:
            if film.tmdb_id is not None:
                p = pyfancy().white(INDENT_PREFIX).raw(color('✓ {} ({})'.format(film.title, film.year), fg=ansi.green)).dark_gray()
                p.add(' [{}] {} match'.format(film.tmdb_id, formatter.percent(film.title_similarity))).output()
                log.detail('✓ {} ({}) [{}] {} match'.format(film.title, film.year, film.tmdb_id, formatter.percent(film.title_similarity)))
            else:
                pyfancy().white(INDENT_PREFIX).red('× {} ({})'.format(film.title, film.year)).output()
                log.detail('× Not found')

    @classmethod
    def _notify_test(cls):
        """Print and log a warning header to indicate that Fylm is running in test mode.
        """
        if config.test:
            log.info(' *** TEST MODE *** ')
            pyfancy().bold().dim('{}\nTEST MODE\nNo changes will be made\n{}\n'.format(DIVIDER, DIVIDER)).output()

    @classmethod
    def _notify_force_lookup(cls):
        """Print and log a warning header to indicate that Fylm is running in force mode.
        """
        if config.force_lookup:
            log.info(' *** FORCE MODE *** ')
            pyfancy().bold().light_yellow('{}\nFORCE MODE\nSmart folder checking will be disabled\nAssuming all folders are films\n{}\n'.format(DIVIDER, DIVIDER)).output()

    @classmethod
    def _notify_overwrite_existing(cls):
        """Print and log a warning header to indicate that Fylm will overwrite duplicates.
        """
        if config.overwrite_existing:
            log.info(' *** OVERWRITE MODE *** ')
            pyfancy().bold().red('{}\nOVERWRITE EXISTING ENABLED\nExisting files will be overwritten\n{}\n'.format(DIVIDER, DIVIDER)).output()

    @classmethod
    def copy_progress(cls, copied, total):
        """Print progress bar to terminal.
        """
        print('      ' + progress.progress_bar(100 * copied / total), end='\r')
        sys.stdout.flush()

    @classmethod
    def clearline(cls):
        """Clears the current printed line.
        """

        # Clear line.
        sys.stdout.write("\033[K") 

    @classmethod
    def end(cls, count):
        """Print and log the closing summary prior to exit.

        Args:
            count: (int) Count of successful moves/renames, from counter module.
        """
        s = "Successfully {} {} film{}".format('renamed' if config.rename_only else 'moved', count, '' if count == 1 else 's')
        print(s)
        log.info(s)

    @classmethod
    def exit_early(cls):
        print(color('\nBye, Fylicia.', fg=ansi.pink))

    @classmethod
    def debug(cls, s):
        """Print debugging details, if config.debug is enabled.

        Args:
            s: (str, utf-8) String to print/log
        """
        if config.debug is True: 
            print(color(s, fg=ansi.debug))

    @classmethod
    def info(cls, s):
        """Print and log less important text. Prints dark gray.

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().dark_gray('{}{}'.format(INDENT_PREFIX, s)).output()
        log.detail(s)

    @classmethod
    def error(cls, s, x=Exception):
        """Print an error, then call log.error, which raises an Exception. Prints red.

        Args:
            s: (str, utf-8) String to print/log.
        """
        log.error(s)
        raise x(s)

    @classmethod
    def rename(cls, title='', size=''):
        """Print film rename details to the console. Prints white first, then a green highlight.

        Args:
            title: (str, utf-8) String to print green and send to log.
            size: (float) String to print white and send to log.
        """
        pyfancy().white('{}⌥ '.format(INDENT_PREFIX)).raw(color(title, fg=ansi.green)).dark_gray().dim(' ({})'.format(size)).output()
        log.detail('⌥ {} {}'.format(title, size))

    @classmethod
    def duplicates(cls, film):
        """Print any duplicates found to the console.

        Args:
            film: (Film) Inbound film that has been marked as duplicate.
            size: ([Film]) Array of duplicate Film objects.
        """

        # Import duplicates' should_replace function here to prevent circular imports.
        from fylmlib.duplicates import duplicates

        if len(film.duplicates) > 0:
            console.info('{} duplicate{} found:'.format(
                len(film.duplicates),
                '' if len(film.duplicates) == 1 else 's'))
            for d in film.duplicates:

                pretty_size_diff = formatter.pretty_size_diff(film.source_path, d.source_path)
                pretty_size = formatter.pretty_size(d.size)

                # If the film will be replaced, print info:
                if duplicates.should_replace(film, d):
                    console.replacing(
                        "  Replacing '{}'".format(d.new_filename__ext()),
                        " ({})".format(pretty_size),
                        " [{}]".format(pretty_size_diff))
                elif duplicates.should_keep_both(film, d):
                    console.info("  Keeping '{}' ({}) [{}]".format(
                        d.new_filename__ext(), 
                        pretty_size,
                        pretty_size_diff))
                else:
                    console.warn("  Ignoring because '{}' ({}) is {}".format(
                        d.new_filename__ext(), 
                        pretty_size,
                        pretty_size_diff))

    @classmethod
    def replacing(cls, s1, s2, s3):
        """Print and log replacement text, note, and dim.

        Args:
            s1: (str, utf-8) String 1 to print/log.
            s2: (str, utf-8) String 2 to print/log.
            s3: (str, utf-8) String 3 to print/log.
        """
        pyfancy().raw(
            color('%s%s' % (INDENT_PREFIX, s1), fg=ansi.blue)).raw(
            color(s2, fg=ansi.blue)).dark_gray().dim(s3).output()
        log.detail('{}{}{}'.format(s1, s2, s3))

    @classmethod
    def interesting(cls, s):
        """Print and log interesting text. Prints green.

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().raw(color('{}{}'.format(INDENT_PREFIX, s)), fg=ansi.green).output()
        log.detail(s)

    @classmethod
    def caution(cls, s):
        """Print and log caution text. Prints yellow.

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().yellow('{}{}'.format(INDENT_PREFIX, s)).output()
        log.detail(s)

    @classmethod
    def warn(cls, s):
        """Print and log a warning. Prints red.

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().raw(color('{}{}'.format(INDENT_PREFIX, s), fg=ansi.red)).output()
        log.detail(s)

    @classmethod
    def red(cls, s):
        """Print and log text in red. Prints red.

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().red('{}'.format(s)).output()
        log.detail(s)

    @classmethod
    def dim(cls, s):
        """Print and log unimportant text. Prints dim (darker).

        Args:
            s: (str, utf-8) String to print/log.
        """
        pyfancy().dark_gray().dim('{}{}'.format(INDENT_PREFIX, s)).output()
        log.detail(s)