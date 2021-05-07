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

"""String formatting tools for Fylm.

This module contains several string manipulation tools used for
string cleaning, improving comparison results, and outputting
human-readable information to the console/log.
"""

import inflect
import re
from copy import copy
from typing import Union
import locale
locale.setlocale(locale.LC_ALL, '')
infl = inflect.engine()

from fylmlib.tools import *
from fylmlib.enums import *
import fylmlib.config as config
import fylmlib.patterns as patterns
from timeit import default_timer as timer

MAX_WORKERS = 50
    
class Format:
    
    # FIXME: Format should take a string or int and init

    class Name:
        r"""Build a new file and folder name object from the specified renaming pattern.

        Using regular expressions and a { } templating syntax, construct
        a new filename by mapping available properties to config.rename_pattern.

        # Permitted rename pattern objects: {title}, {title-the}, {year}, {quality}, {edition}, {media}.
        # For using other characters with pattern objects, place them inside {} e.g. { - edition}.
        # For escaping templating characters, use \{ \}, e.g. {|{edition\}}.

        """

        def __init__(self, file: 'Film.File'):
            """Initialize the new_basename instance

            Args:
                file: A Film.File object to build new names from.
            """
            self.file = file
                
            # Map mutable copies of the original renaming patterns to names
            self.filename = self._map_template(
                copy(config.rename_pattern.file), RenameMask.FILE)
            self.dirname = self._map_template(
                copy(config.rename_pattern.folder), RenameMask.DIR)
            
        @property
        def filmrel(self) -> 'Path':
            """Generates a Path object from the given string.

            Returns:
                Path: A Path object from the given string.
            """
            if not self.filename:
                raise AttributeError(
                    f"Could not build path for '{self.path.name}', 'name' is missing.\n"
                    f"Initalize Name and call build() before accessing 'filmrel'.")
                
            if not self.dirname:
                raise AttributeError(
                    f"Could not build path for '{self.path.name}', 'parent' is missing.\n"
                    f"Initalize Name and call build() before accessing 'filmrel'.")
                
            # Handle macOS (darwin) converting / to : on the filesystem reads/writes.
            # Credit: https://stackoverflow.com/a/34504896/1214800
            if sys.platform == 'darwin' and re.search(r'/', self.filename):
                self.filename - self.filename.replace(r'/', '-')
            
            if config.use_folders:
                return Path(self.dirname) / self.filename
            else:
                return Path(self.filename)
            
        def _map_template(self, template: str, rename_mask: RenameMask) -> str:
            """Maps a pattern to a string given the template mask provided.
            
            Args:
                template (str): The template.
                rename_mask (RenameMask): RenameMask.FILE or .DIR, depending on 
                                          which is being generated.

            Returns:
                str: Name derived from the template.
            """

            # Generate a key-value map of available template properties,
            # each mapped to its associated film property. These need to
            # be ordered such that the most restrictive comes before the
            # most flexible match.
            quality = '-'.join(filter(
                None, [
                    self.file.media.display_name if self.file.media else None, 
                    self.file.resolution.display_name if self.file.resolution else None
                ]))
            
            pattern_map = [
                ["title-the", self.file.film.title_the],
                ["title", self.file.film.title],
                ["edition", self.file.edition],
                ["year", self.file.film.year],
                ["quality-full",
                    f'{quality}{" Proper" if self.file.is_proper else ""}'],
                ["quality", f'{quality}'],
                ["hdr", " HDR" if self.file.is_hdr else ""]
            ]

            # Enumerate the pattern map
            for key, value in pattern_map:

                # Generate a regular expression that suppports the keyword inside { }
                # and uses capture groups to preserve additional formatting characters.
                # The expression matches `{<anything>key<anything>}`, except where
                # { } are escaped with backslashes, i.e. \{ and \}.
                rx = re.compile(r'\{([^\{]*)' + key + r'([^\}]*)\}', re.I)

                # Check for a match
                match = re.search(rx, template)

                # Replace the template key in the pattern and strip the surrounding { }.
                # We add capture groups back in here to preserve extraneous chars that were
                # in the original match. This allows for conditional chars to be added to
                # the template string, so that `{ - edition}` will be replaced with
                # ` - Director's Cut` *only* if film.edition isn't blank.
                replacement = f'{match.groups()[0]}{value}{match.groups()[1]}' if (
                    match and match.groups() is not None) else value

                # Update the template by replacing the original template match (e.g. `{title}`)
                # with the replacement (e.g. `Furngully The Last Rainforest`).
                template = re.sub(rx, str(replacement)
                                  if value is not None else '', template)

            # Convert escaped template characters to un-escaped plain { }.
            template = template.replace(r'\{', '{')
            template = template.replace(r'\}', '}')

            # Strip illegal chars
            template = Format.strip_illegal_chars(template)

            # Hack macOS titles that read / from the filesystem as :. If we don't do this,
            # we end up with the app trying to create folders for any title that contains
            # a /. Looking at you, Face/Off.
            template = template.replace(r'/', '-')
            
            # Append Part to the file, if applicable
            if rename_mask == RenameMask.FILE and self.file.part:
                template = f"{template}, Part {self.file.part}"

            # Strip extra whitespace from titles (e.g. `Dude   Where's My  Car` will become
            # `Dude Where's My Car`).

            return Format.strip_extra_whitespace(template)

    def pretty_size(bytes: Union[int, float], 
                    units: Units = None, 
                    precision: int = None) -> str:
        """Returns a human readable string representation of bytes.

        Args:
            bytes (int, float): Bytes
            units (Units, optional): Specific Units type to format to. Defaults to None.
            precision (int, optional): Decimal places. Default is 2 for GB, 1 for MB, else 0.

        Returns:
            str: A human readable string representation of bytes, e.g. 4.12 GiB or 210.2 MB.
        """
        
        if units and 'i' in units.name or not units and config.size_units_ibi:
            sizes = ['B', 'KiB', 'MiB', 'GiB']
            cutoff = 1024
        else:
            sizes = ['B', 'KB', 'MB', 'GB']
            cutoff = 1000
            
        units = units if type(units) is list else [units.name] if units else sizes
                
        p = lambda x, u: x if x is not None else (2 if 'G' in u else 
                                               1 if 'M' in u else 0)
        
        i = 0
        u = units
        prec = 0
        while bytes > cutoff:
            bytes /= cutoff
            i += 1
            u = u[1:] if len(u) > 1 else u
            want = u[i] if len(u) > i else u[-1]
            current = sizes[i]
            prec = p(precision, current)
            if current == want:
                break
            
        return f'{bytes:,.{prec}f} {u[0]}'

    @staticmethod
    def pretty_size_diff(left: int, right: int):
        """Pretty format filesize comparison.

        Args:
            left (int): Size in bytes of first path
            right (int): Size in bytes of second path
        Returns:
            A human-readable formatted comparison string.
        """
        
        diff = right - left
        if diff < 0: return f'{Format.pretty_size(abs(diff))} smaller'
        elif diff > 0: return f'{Format.pretty_size(abs(diff))} bigger'
        else: return 'Identical'
        
    @staticmethod
    def num(d):
        """Converts an input number to a string."""
        return f'{d:n}'
    
    @staticmethod
    def num_to_words(d: int):
        """Converts an input number to words."""
        try:
            return infl.number_to_words(d)
        except:
            return d

    @staticmethod
    def percent(d):
        """Pretty format a decimal as a percent string.

        Pretty format a decimal (ideally between 0 and 1) as a human-readable percent.

        Args:
            d (float): decimal number to convert to percentage.
        Returns:
            A human-readable formatted percentage.
        """
        return f"{d * 100:.0f}"

    @staticmethod
    def replace_insensitive(find, repl, s):
        """Search and replace (case insensitive) within a string.

        Replace all occurrences of a substring in a string (case insensitive)
        with another string.

        Args:
            find (str, utf-8): substring to find in a string.
            repl (str, utf-8): string to replace it with.
            s (str, utf-8): original string to be searched
        Returns:
            A string with some substrings replaced.
        """
        return re.compile(re.escape(find), re.I).sub(repl, s)

    @staticmethod
    def strip_the(s):
        """Remove `The` from the begining or `, The` from the end of a string.

        Search for `The` at the beginning of a string (case insensitive) and
        `, The` at the end (case insensitive) and remove both.

        Args:
            s (str, utf-8): original string to be cleaned.
        Returns:
            A string without `The` at the beginning or end.
        """
        return re.sub(patterns.THE_PREFIX_SUFFIX, '', s)

    @staticmethod
    def strip_illegal_chars(s):
        """Remove all illegal characters from a title.

        Remove OS-restricted characters from filenames/paths so that the app
        doesn't attempt to write restricted chars to the filesystem.

        Args:
            s (str, utf-8): original string to be cleaned.
        Returns:
            A string without restricted chars.
        """

        # If the char separates a word, e.g. Face/Off, we need to preserve that
        # separation with a dash (-).
        s = re.sub(r'(?<=\S)[' + patterns.ILLEGAL_CHARS + r'](?=\S)', '-', s)

        # If it terminates another word, e.g. Mission: Impossible, we replace it
        # with space-dash-space. Duplicate whitespace will be removed later.
        s = re.sub(r'\s?[' + patterns.ILLEGAL_CHARS + r']\s?', ' - ', s)

        # Strip zero-width spaces
        s = s.lstrip(u'\u200c')

        return s

    @staticmethod
    def strip_trailing_nonword_chars(s):
        """Remove specific non-word characters from the end of a title.

        Args:
            s (str, utf-8): original string to be stripped of bad chars.
        Returns:
            A string without those bad chars.
        """
        return re.sub(patterns.TRAILING_NONWORD_CHARS, '', s)

    @staticmethod
    def strip_extra_whitespace(s):
        """Replace repeating whitespace chars in a string with a single space.

        Search for repeating whitespace chars in a string and replace them with
        a single space.

        Args:
            s (str, utf-8): original string to be stripped of whitespace.
        Returns:
            A string without repeating whitespace chars.
        """
        return ' '.join(s.split()).strip()

    @staticmethod
    def title_case(s):
        """Convert a film's title string to title case, with some grammatical and
        roman numeral exceptions.

        Args:
            s (str, utf-8): original string to be Title Cased.
        Returns:
            A Title Cased string.
        """
        word_list = s.split(' ')
        title = [word_list[0].capitalize()]
        for prev, current in zip(word_list[0:], word_list[1:]):

            # If it's a roman numeral, uppercase it
            if is_roman_numeral(current):
                title.append(current.upper())
            # If the word is an article, and preceded by a regular word, lowercase it
            elif (current.lower() in patterns.ARTICLES):
                l = current.lower()
                # There are some exceptions for when we need to re-capitalize it
                # If the current is not 'and'
                # and previous wasn't an article
                # and the previous wasn't the beginning of the title
                # and the previous word didn't end with a comma ,
                # and...
                #    the previous wasn't alphabetical, numerical, or a roman numeral
                #    (however, the roman numeral can't be the first word in the title)
                #    it's not 'a' or 'the'
                #       (We should check that it's not preceded by verb, but nltk 
                #       synsets is way too slow.)
                # then we should capitalize the article.
                # (e.g., Mack The Knife vs. The Chronicles of Narnia The Lion the Witch, and the Wardrobe)
                if (not current.lower() == 'and' 
                    and not prev.lower() in patterns.ARTICLES 
                    and not prev.endswith(',') 
                    and (
                        not prev.rstrip(',').isalpha()
                        or is_number(prev)
                        or (is_roman_numeral(prev) and not prev.lower() == title[0].lower())
                        or (current.lower() in ['a', 'the'])
                    )
                ):
                    l = l.capitalize()
                title.append(l)

            # Otherwise it's just regular
            else:
                title.append(current.capitalize())

        title = list(map(Format.capitalize_if_special_chars, title))
        return ' '.join(title)

    @staticmethod
    def pluralize(s, c):
        """Pluralizes a string if count <> 1.

        Take a singular form of a string, and append an s to pluralize the word
        if the count is <> 1.

        Args:
            s (str, utf-8): Singular form of a string to be pluralized.
            c (int): Count of item(s) to determine whether s should be pluralized.
        Returns:
            s, or {s}s if c <> 1
        """
        return s if c == 1 else p.plural(s)

    @staticmethod
    def capitalize_if_special_chars(s):
        """Tests if string contains a non-word char, then
        splits and capitalizes each. Important for hyphenated
        and colon-separated strings.

        Args:
            s (str, utf-8): Input string to check
        Returns:
            A split string, uppercased on the non-word char
            e.g. face:off --> Face:Off
        """
        m = re.compile(patterns.INTRA_WORD_SPECIAL_CHARS)
        return ''.join(
            [t.capitalize() for t in re.split(m, s)]
        ) if re.search(m, s) else s
