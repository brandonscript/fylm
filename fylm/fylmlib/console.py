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

from __future__ import unicode_literals

import sys
import logging
import datetime

from pyfancy import *

from fylmlib.config import config
from fylmlib.log import log
import fylmlib.formatter as formatter

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
        log.info('{}{}{}'.format(('-'*50), NOW, ('-'*50)))
        log.info('Scanning {}'.format(', '.join(config.source_dirs)))
        print("Fylm is scanning " + ', '.join(config.source_dirs))
        print("Please wait...\n")
        console._notify_test()
        console._notify_force_lookup()
        console._notify_overwrite_duplicates()

    @classmethod
    def film_loaded(cls, film):
        """When a film is loaded, print and log the file (or dir) name and size.

        Args:
            film: (Film) film to pass to debug calls.
        """
        log.info('{} ({})'.format(film.source_path, formatter.pretty_size(film.size)))
        if film.title is not None:
            console.debug('----------------------------')
            console.debug('Init film object:\n')
            console.debug('title\t{}'.format(film.title))
            console.debug('year\t{}'.format(film.year))
            console.debug('edition\t{}'.format(film.edition))
            console.debug('media\t{}'.format(film.media))
            console.debug('quality\t{}'.format(film.quality))
            console.debug('size\t{}'.format(formatter.pretty_size(film.size)))

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
            pyfancy().bold().yellow('{}\nFORCE MODE\nSmart folder checking will be disabled\nAssuming all folders are films\n{}\n'.format(DIVIDER, DIVIDER)).output()

    @classmethod
    def _notify_overwrite_duplicates(cls):
        """Print and log a warning header to indicate that Fylm will overwrite duplicates.
        """
        if config.overwrite_duplicates:
            log.info(' *** OVERWRITE DUPLICATES *** ')
            pyfancy().bold().yellow('{}\nOVERWRITE DUPLICATES ENABLED\nDuplicate files will be overwritten\n(File size will be ignored)\n{}\n'.format(DIVIDER, DIVIDER)).output()

    @classmethod
    def end(cls, count):
        """Print and log the closing summary prior to exit.

        Args:
            count: (int) Count of successful moves/renames, from counter module.
        """
        s = "Successfully moved {} films".format(count)
        print(s)
        log.info(s)

    @classmethod
    def debug(cls, str):
        """Print debugging details, if config.debug is enabled.

        Args:
            str: (unicode) String to print/log
        """
        if config.debug is True: print(str)

    @classmethod
    def info(cls, str):
        """Print and log less important text. Prints dark gray.

        Args:
            str: (unicode) String to print/log.
        """
        pyfancy().dark_gray('{}{}'.format(INDENT_PREFIX, str)).output()
        log.detail(str)

    @classmethod
    def error(cls, str):
        """Print an error, then call log.error, which raises an Exception. Prints red.

        Args:
            str: (unicode) String to print/log.
        """
        log.error(str)

    @classmethod
    def interesting(cls, str, highlight):
        """Print important text to the console. Prints white first, then a green highlight.

        Args:
            str: (unicode) String to print white and send to log.
            highlight: (unicode) String to print green and send to log.
        """
        pyfancy().white('{}{} '.format(INDENT_PREFIX, str)).green(highlight).output()
        log.detail('{}{}'.format(str, highlight))

    @classmethod
    def warn(cls, str):
        """Print and log a warning. Prints red.

        Args:
            str: (unicode) String to print/log.
        """
        pyfancy().red('{}{}'.format(INDENT_PREFIX, str)).output()
        log.detail(str)

    @classmethod
    def red(cls, str):
        """Print and log text in red. Prints red.

        Args:
            str: (unicode) String to print/log.
        """
        pyfancy().red('{}'.format(str)).output()
        log.detail(str)

    @classmethod
    def notice(cls, str):
        """Print and log unimportant text. Prints dim (darker gray).

        Args:
            str: (unicode) String to print/log.
        """
        pyfancy().dim('{}{}'.format(INDENT_PREFIX, str)).output()
        log.detail(str)

    @classmethod
    def skip(cls, film, str):
        """Print and log reason for skipping a film. Prints file in red, reason in dark gray.

        Args:
            film: (Film) Film that was skipped.
            str: (unicode) Reason the film was skipped
        """
        pyfancy().red('{}{}'.format(MAIN_PREFIX, film.original_filename)).dark_gray(' {}'.format(str)).output()
        log.detail(str)

    @classmethod
    def film_details(cls, film):
        """Print and log film details.

        Args:
            film: (Film) Film to print/log.
        """

        # Print original filename and size.
        pyfancy().bold('{}{}{} ({})'.format(MAIN_PREFIX, film.original_filename, film.ext or '', formatter.pretty_size(film.size))).output()

        # Only print lookup results if TMDb searching is enabled.
        if config.tmdb.enabled is True:
            if film.id is not None:
                p = pyfancy().white(INDENT_PREFIX).green(u'✓ {} ({})'.format(film.title, film.year)).dark_gray()
                p.add(' [{}] {} match'.format(film.id, formatter.percent(film.title_similarity))).output()
                log.detail(u'✓ {} ({}) [{}] {} match'.format(film.title, film.year, film.id, formatter.percent(film.title_similarity)))
            else:
                pyfancy().white(INDENT_PREFIX).red('𝗑 {} ({})'.format(film.title, film.year)).output()
                log.detail(u'𝗑 Not found')