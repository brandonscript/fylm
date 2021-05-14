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
import yaml
from halo import Halo

import fylmlib.config as config
from fylmlib.enums import *
from fylmlib.tools import *
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
    def __init__(self, *s, join=' '):

        self.color = 'white'
        self.style = []
        self.parts = []
        self.parts_plaintext = []
            
        # Inject ANSI helper functions
        for c in vars(self.ansi):
            self._colorizer(c)
            
        self.add(*s, join=join)
            
    def __repr__(self):
        return str(self._pltxt)

    def _colorizer(self, c: str):
        def add(*s, join=' '):
            if c is not None:
                self.color = c
            self.add(*s, join=join)
            return self
        self.__setattr__(c, add)
        
    @property
    def _fmtxt(self):
        return ''.join(self.parts)
        
    @property
    def _pltxt(self):
        return ''.join(self.parts_plaintext)

    def add(self, *s, join=' '):
        p = join.join([f"{x}" for x in s])
        style = '+'.join(list(set(self.style))) if self.style else None
        fmt = color(p,
                  fg=self.color
                  if type(self.color) == int
                  else getattr(self.ansi, self.color or 'white'),
                  style=style)
        self.parts.append(fmt)
        self.parts_plaintext.append(p)
        return self
    
    def ansi(self, code: int = 0):
        self.color = int(code)
        return self

    def bold(self, *s, join=' '):
        self.style.append('bold')
        self.add(*s)
        return self
    
    def underline(self, *s, join=' '):
        self.style.append('underline')
        self.add(*s)
        return self

    def dim(self, *s, join=' '):
        self.style.append('faint')
        self.add(*s)
        return self
    
    def norm(self, *s, join=' '):
        self.style = []
        self.add(*s)
        return self

    def reset(self, *s, join=' '):
        self.color = None
        self.style = []
        self.add(*s)
        return self

    def print(self, should_log=True, override_no_console=False, end=None, plain=False):
        if config.no_console and not override_no_console:
            return
        if should_log:
            Log.info(self._pltxt)
        if plain or config.plaintext:
            print(patterns.ANSI_ESCAPE.sub('', self._pltxt), end=end)
        else:
            print(self._fmtxt, end=end)

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
        Console().pink("Thanks for using Fylm. Be kind, and please rewind.").print()

    def print_exit_early(self):
        """Print the early exit message.
        """
        Console().pink('\n\nThat\'s it, I quit.').print()

    @staticmethod
    def print_film_header(film: 'Film'):
        c = Console('\n')
        
        header = film.name if film._year else film.main_file.name
        Console().gray(f'\n{INDENT}{header}').white(S.size(film)).print(end="")
                        
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
    def print_film_src(film):
        parent = film.src.parent if film._year else film.src
        Console().dark_gray(f'{INDENT}{parent}').print()
    
    @staticmethod
    def print_interactive_success(film: 'Film'):
        c = Console().green(f' {ARROW} {S.name(film)}')
        if film.tmdb.id:
            c.gray(S.tmdb_id(film))
            c.dark_gray(S.percent(film))
        c.print()
        
    @staticmethod
    def print_interactive_uncertain(film: 'Film'):
        Console().light_blue(f' {UNCERTAIN} {film.title} ({film.year})').print()
        
    @staticmethod
    def print_src_dst(film: 'Film'):
        if config.interactive:
            return
        
        Console().dark_gray(f'{INDENT}{film.src}').print()
        if not film.should_ignore:
            Console().gray(f'{INDENT}{film.dst}').print()
   
    @staticmethod
    def print_skip(film: 'Film'):
        if film.should_ignore:
            if config.interactive and film.ignore_reason == IgnoreReason.SKIP:
                Console.print_interactive_skipped()
            else:
                Console().red().dim(
                    f'{INDENT}Ignoring because {film.ignore_reason.display_name}').print()

    @staticmethod
    def print_rename_only(film: 'Film'):
        Console().red().dim(
            f'{INDENT}Ignoring because {film.ignore_reason.display_name}').print()

    @staticmethod
    def print_duplicates_old(film: 'Film'):

        # Import duplicates' should_replace function here to prevent circular imports.
        if not config.duplicates.enabled:
        # FIXME:
            duplicate_count = len(film.verified_duplicate_files)

            if duplicate_count > 0:
                
                c = Console().blue().add(INDENT_WIDE)
                c.add(f"{duplicate_count} {ƒ.pluralize('duplicate', duplicate_count)} found")

                if config.interactive is True:
                    c.add(' for ').light_blue(f'{film.all_valid_files[0].new_filename_and_ext}')
                    c.blue(':').print()
                else:
                    c.add(':').print()

                if config.interactive is False:
                    Console.print_duplicates(film)

    @staticmethod
    def print_duplicates(new: 'Film.File', duplicates: '[Duplicates.Map]'):
        # If any duplicates determine that the current file should be ignored,
        # we only show the skip recommendation.
        
        if not duplicates:
            return

        c = Console().blue(f"{INDENT}Found {ƒ.num_to_words(len(duplicates))} ")
        c.add(f"{ƒ.pluralize('duplicate', len(duplicates))} for '{new.name}'")
        c.dim(f" ({new.size.pretty()})").print()
        
        keeps = list(filter(lambda mp: mp.action == Should.KEEP_EXISTING, duplicates))
        duplicates = keeps[:1] if keeps else duplicates
        
        def fixcase(s): return s.capitalize() if not config.interactive else s
            
        for mp in duplicates:
            
            c = Console(INDENT)
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
                        f"the same quality\n{INDENT}"))
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
    def print_ask(s):
        """Print an interactive question.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Console().yellow(INDENT, s, join='').print()
        
    @staticmethod
    def print_io_reject(verb, dst):
        if config.rename_only:
            verb = 'rename'
        Console().red(INDENT, f"Unable to {verb}, a file with the same name ",
                      f"already exists in\n{INDENT}'{dst.parent}'.", join='').print()


    @staticmethod
    def print_interactive_error(s):
        """Print an interactive error.

        Args:
            s: (str, utf-8) String to print/log.
        """
        Console().red(f'      {s}').print()

    @staticmethod
    def print_interactive_skipped():
        """Print an interactive skip message.
        """
        Console().dark_gray(f'{INDENT}Skipped').print()

    @staticmethod
    def print_choice(idx, choice):
        """Print a question choice.

        Args:
            idx: (int or str) Index of choice (first letter or number)
            choice: (str, utf-8) Choice to print/log.
        """

        c = Console().white(INDENT_WIDE, f'{idx})')
        if choice.startswith('['):
            c.dark_gray(f' {choice}')
        else:
            match = re.search(patterns.TMDB_ID, choice)
            tmdb_id = match.group('tmdb_id') if match else ''
            c.light_gray(f" {re.sub(patterns.TMDB_ID, '', choice)}")
            c.dark_gray(tmdb_id)
        c.print()

    def print_move_or_copy(self, src, dst_path, dst):

        # Do not print if source and destination root path are the same.
        if src == dst_path:
            return

        from fylmlib.operations import dirops
        Console().gray().add(INDENT_WIDE, 
            f"{'Copying' if (config.safe_copy or not dirops.is_same_partition(src, dst)) else 'Moving'}" \
            f" '{os.path.basename(dst)}' to {os.path.dirname(dst)}"
        ).print()

    @staticmethod
    def print_copy_progress_bar(copied, total):
        """Print progress bar to terminal.
        """
        if not config.plaintext:
            print(INDENT + Progress.bar(100 * copied / total), end='\r')
            # Catch stdout if None
            if sys.stdout:
                sys.stdout.flush()

    @classmethod
    def get_input(cls, p):
        """Prompt the user for input

        Args:
            p (str): Query to print.
        """
        return input(color(PROMPT, fg=Console.ansi.white) + color(p, fg=Console.ansi.yellow))

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
            halo.start = lambda: Console(s).print()
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
        def verb(film: 'Film') -> (str, str):
            from fylmlib.filmpath import Info
            if Info.will_copy(film):
                return ('copy', 'copied', 'copying')
            elif config.rename_only:
                return ('rename', 'renamed', 'renaming')
            else:
                return ('move', 'moved', 'moving')

    class _AnsiColors:

        """Color handling for console output.

        ANSI color map for console output. Get a list of colors here = 
        http://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#256-colors

        You can change the colors the terminal outputs by changing the 
        ANSI values here.

            ansi is the main property exported by this module.
        """

        def __init__(self):
            with open(Path(__file__).parent.parent / 'colors.yaml', 'r') as f:
                colormap = yaml.safe_load(f)    
                for k, v in colormap.items():
                    self.__setattr__(k, v)
                    
        def discover(self):
            """Print all 256 colors in a matrix on your system."""
            print('\n')
            for i in range(0, 16):
                for j in range(0, 16):
                    code = str(i * 16 + j)
                    sys.stdout.write(u"\u001b[38;5;" + code + "m " + code.ljust(4))
                print(u"\u001b[0m")
            
            

Console.ansi = Console._AnsiColors()
S = Console.strings
