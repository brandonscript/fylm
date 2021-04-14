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

import re
import copy
import nltk
from nltk.corpus import wordnet as wn

from fylmlib.enums import *
import fylmlib.config as config
import fylmlib.patterns as patterns

try:
    nltk.data.find('wordnet')
except LookupError:
    nltk.download('wordnet', quiet=True)
    
import inflect
p = inflect.engine()
    
class Format:

    class Rename:
        r"""Build a new file or folder name from the specified renaming pattern.

        Using regular expressions and a { } templating syntax, construct
        a new filename by mapping available properties to config.rename_pattern.

        # Permitted rename pattern objects: {title}, {title-the}, {year}, {quality}, {edition}, {media}.
        # For using other characters with pattern objects, place them inside {} e.g. { - edition}.
        # For escaping templating characters, use \{ \}, e.g. {|{edition\}}.

        Args:
            A Film.File object to build a path from.

        Returns:
            A new filename/foldername based on config.rename_pattern.(file|folder).
        """

        def __init__(self, file: 'Film.File', build_for: RenameStyle):
            """Initialize the new_basename instance

            Args:
                file (Film.File): [description]
                build_for (RenameStyle): [description]
            """
            self.file = file
            self.build_for = build_for

        def build(self):

            # Create a mutable copy of the original renaming pattern
            template = copy.copy(config.rename_pattern.file if build_for ==
                                RenameStyle.FILE else config.rename_pattern.folder)

            # Generate a key-value map of available template properties,
            # each mapped to its associated film property. These need to
            # be ordered such that the most restrictive comes before the
            # most flexible match.
            quality = '-'.join(filter(
                None, [file.media.display_name if file.media else None, file.resolution or None]))

            part = f', Part {file.parent_film.part}' if file.parent_film.part and build_for == RenameStyle.FILE else ""

            pattern_map = [
                ["title-the", file.parent_film.title_the + part],
                ["title", file.parent_film.title + part],
                ["edition", file.edition],
                ["year", file.parent_film.year],
                ["quality-full",
                    f'{quality}{" Proper" if file.is_proper else ""}'],
                ["quality", f'{quality}'],
                ["hdr", " HDR" if file.is_hdr else ""]
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
            template = strip_illegal_chars(template)

            # Hack macOS titles that read / from the filesystem as :. If we don't do this,
            # we end up with the app trying to create folders for any title that contains
            # a /. Looking at you, Face/Off.
            template = template.replace(r'/', '-')

            # Strip extra whitespace from titles (e.g. `Dude   Where's My  Car` will become
            # `Dude Where's My Car`).

            return strip_extra_whitespace(template)

    @staticmethod
    def pretty_size(size_in_bytes=0, measure=None):
        """Pretty format filesize/size_in_bytes into human-readable strings.

        Maps a byte count to KiB, MiB, GiB, KB, MB, or GB. By default,
        this measurement is automatically calculated depending on filesize,
        but can be overridden by passing `measure` key.

        Args:
            size_in_bytes (int): file size in bytes
            measure (str, utf-8): (optional) key value for the pretty_size_map to force
                            formatting to a specific measurement.
        Returns:
            A human-readable formatted filesize string.
        """

        # Force size_in_bytes to be an integer
        size_in_bytes = size_in_bytes or 0

        # Map out the math required to re-calculate bytes into human-readable formats.
        pretty_size_map = {

            # Do not round.
            "B": size_in_bytes,

            # Round to nearest whole number.
            "KB": round(size_in_bytes / 1000.0, 0),
            "KiB": round(size_in_bytes / 1024.0, 0),

            # Round to one decimal place.
            "MB": round(size_in_bytes / 1000.0 / 1000.0, 1),
            "MiB": round(size_in_bytes / 1024.0 / 1024.0, 1),

            # Round to two decimal places.
            "GB": round(size_in_bytes / 1000.0 / 1000.0 / 1000.0, 2),
            "GiB": round(size_in_bytes / 1024.0 / 1024.0 / 1024.0, 2)
        }

        # If measure was specified, format and return. This is usually used when calling
        # this function recursively, but can be called manually.
        if measure:
            return f'{pretty_size_map[measure]} {measure}'
        elif pretty_size_map['GiB'] > 1:
            return pretty_size(size_in_bytes, 'GiB')
        elif pretty_size_map['MiB'] > 1:
            return pretty_size(size_in_bytes, 'MiB')
        elif pretty_size_map['KiB'] > 1:
            return pretty_size(size_in_bytes, 'KiB')
        else:
            return f'{size_in_bytes:,.0f} B'

    @staticmethod
    def pretty_size_diff(left: str, right: str):
        """Pretty format filesize comparison.

        Compares two files/folders and prints the destination's difference in size in a
        human-readable manner, e.g. if src is 500 MB and dst is 300 MB, it will print
        '200 MB smaller'.

        Args:
            left (str, utf-8): path to source file/folder
            right (str, utf-8): path to destination file/folder
        Returns:
            A human-readable formatted comparison string.
        """

        # Import size here to avoid circular import conflicts.
        from fylmlib.operations import size

        # Get the size of both source and destionation, then subtract the size of the
        # destination from the size of the source.
        size_diff = size(right) - size(left)

        # If the difference is negative, the destination is smaller than the source.
        if size_diff < 0:
            return f'{pretty_size(abs(size_diff))} smaller'

        # If the difference is positive, the destination is larger than the source.
        elif size_diff > 0:
            return f'{pretty_size(abs(size_diff))} bigger'

        # Otherwise they must be the same size.
        else:
            return 'identical size'

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
        return re.sub(patterns.begins_with_or_comma_the, '', s)

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
        s = re.sub(r'(?<=\S)[' + patterns.illegal_chars + r'](?=\S)', '-', s)

        # If it terminates another word, e.g. Mission: Impossible, we replace it
        # with space-dash-space. Duplicate whitespace will be removed later.
        s = re.sub(r'\s?[' + patterns.illegal_chars + r']\s?', ' - ', s)

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
        return re.sub(patterns.trailing_nonword_chars, '', s)

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
            elif (current.lower() in patterns.articles):
                l = current.lower()
                # There are some exceptions for when we need to re-capitalize it
                # If the current is not 'and'
                # and previous wasn't an article
                # and the previous wasn't the beginning of the title
                # and the previous word didn't end with a comma ,
                # and...
                #    the previous wasn't alphabetical, numerical, or a roman numeral
                #    (however, the roman numeral can't be the first word in the title)
                #    it's not 'a' or 'the' preceded by a possible verb
                # then we should capitalize the article.
                # (e.g., Make The Knife vs. The Chronicles of Narnia The Lion the Witch, and the Wardrobe)
                if (not current.lower() == 'and' 
                    and not prev.lower() in patterns.articles 
                    and not prev.endswith(',') 
                    and (
                        not prev.rstrip(',').isalpha()
                        or is_number(prev)
                        or (is_roman_numeral(prev) and not prev.lower() == title[0].lower())
                        or (current.lower() in ['a', 'the'] and not is_possible_verb(prev))
                    )
                ):
                    l = l.capitalize()
                title.append(l)

            # Otherwise it's just regular
            else:
                title.append(current.capitalize())

        title = list(map(capitalize_if_special_chars, title))
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
    def is_number(s):
        """Tests if string is likely numeric, or numberish

        Args:
            s (str, utf-8): Input string to check
        Returns:
            True if the string is a number, otherwise False
        """
        try:
            float(s)
            return True
        except:
            pass
        return any([s.isnumeric(), s.isdigit()])

    @staticmethod
    def is_roman_numeral(s):
        """Tests if string is exactly a roman numeral

        Args:
            s (str, utf-8): Input string to check
        Returns:
            True if the string is a roman numeral, otherwise False
        """
        match = re.search(patterns.roman_numerals, s)
        return True if (match and match.group(1)) else False

    @staticmethod
    def is_possible_verb(s):
        """Tests if string is a possible verb

        Args:
            s (str, utf-8): Input string to check
        Returns:
            True if the string is a verb, otherwise False
        """
        return 'v' in set(s.pos() for s in wn.synsets(s))

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
        m = re.compile(patterns.intra_word_special_chars)
        return ''.join(
            [t.capitalize() for t in re.split(m, s)]
        ) if re.search(m, s) else s
