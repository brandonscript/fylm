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

"""Main file parser for Fylm.

This module takes raw input source paths and cleans/analyzes them
to determine various properties used in the name correction
and TMDb lookup.

    parser: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
import re

import fylmlib.config as config
import fylmlib.patterns as patterns
import fylmlib.formatter as formatter

class parser:
    """Main class for film parser.

    All methods are class methods, thus this class should never be instantiated.
    """
    @classmethod
    def get_title(cls, source_path):
        """Get title from full path of file or folder.

        Use regular expressions to strip, clean, and format a file
        or folder path into a more pleasant film title.

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A clean and well-formed film title.
        """

        # Ensure source_path is a str
        source_path = str(source_path)

        # Create a title object based on the name of the file or active folder.

        title = os.path.basename(source_path)

        # If the film is a file, remove the extension.
        if os.path.isfile(source_path):
            title = os.path.splitext(title)[0]

        # Strip "tag" prefixes from the title.
        for prefix in config.strip_prefixes:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):]

        # For a title that properly begins with 'The' (which was previously
        # converted to append ', The' instead), we need to put it back to its
        # original state both for lookup validation, and so that we don't
        # end up with multiple ', the' suffixes.
        if re.search(r', the', title, re.I):
            title = f"The {re.sub(r', the', '', title, flags=re.I)}"

        # Use the 'strip_from_title' regular expression to replace unwanted
        # characters in a title with a space.
        title = re.sub(patterns.strip_from_title, ' ', title)

        # If the title contains a known edition, strip it from the title. E.g.,
        # if we have Dinosaur.Special.Edition, we already know the edition, and
        # we don't need it to appear, duplicated, in the title. Because
        # `_edition_map` returns a (key, value) tuple, we check for the search
        # key here and replace it (not the value).
        if cls._edition_map(source_path)[0] is not None:
            title = re.sub(cls._edition_map(source_path)[0], '', title)

        # Typical naming patterns place the year as a delimiter between the title
        # and the rest of the file. Therefore we can assume we only care about
        # the first part of the string, and so we split on the year value, and keep
        # only the left-hand portion.
        title = title.split(str(cls.get_year(source_path)))[0]

        # If any of the standard quality tags still remain in the title after
        # splitting on "year", remove them.
        for q in ['480p', '720p', '1080p', '2160p', 'HDTV']:
            title = formatter.replace_insensitive(q, '', title)

        # Add back in . to titles or strings we know need to to keep periods.
        # Looking at you, S.W.A.T and After.Life.
        for keep_period_str in config.keep_period:
            title = re.sub(re.compile(r'\b' + keep_period_str + r'\b', re.I), keep_period_str, title)

        # Remove extra whitespace from the edges of the title and remove repeating
        # whitespace.
        title = formatter.strip_extra_whitespace(title.strip())
        return title

    @classmethod
    def get_year(cls, source_path):
        """Get year from full path of file or folder.

        Use regular expressions to identity a year value between 1910 and 2159,
        getting the right-most match if there is more than one year found (looking
        at you, 2001: A Space Odyssey).

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A 4-digit integer representing the release year, or None if
            no year could be determined.
        """

        # Ensure source_path is a str
        source_path = str(source_path)

        # Find all matches of years between 1910 and 2159 (we don't want to
        # match 2160 because 2160p, and hopefully I'll be dead by then and
        # no one will use python anymore). Also convert the matches iterator
        # to a list.
        matches = list(re.finditer(patterns.year, os.path.basename(source_path)))

        # Get the last element, and retrieve the 'year' capture group by name.
        # If there are no matches, return None.
        return int(matches[-1].group('year')) if matches else None

    @classmethod
    def get_media(cls, source_path):
        """Get media from full path of file or folder.

        Use regular expressions to identity the original media of the file.

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A string representing the original media format, or None, if no
            match is found.
        """
        match = re.search(patterns.media, os.path.basename(source_path))
        if match and match.group('bluray'):
            return "BluRay"
        elif match and match.group('web'):
            return "WEB-DL"
        elif match and match.group('hdtv'):
            return "HDTV"
        else:
            return None

    @classmethod
    def get_edition(cls, source_path):
        """Get and correct special edition from full path of file or folder.

        Iterate a map of strings (or, more aptly, regular expressions) to
        search for, and correct, special editions. This map is defined in
        config.edition_map.

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A corrected string representing the film's edition, or None.
        """

        # Because _edition_map returns a (key, value) tuple, we need to
        # return the second value in the tuple which represents the corrected
        # string value of the edition.
        return cls._edition_map(os.path.basename(source_path))[1] or None

    @classmethod
    def get_quality(cls, source_path):
        """Get quality (resolution) from full path of file or folder.

        Use a regular expression to retrieve release quality from the source path
        (e.g. 720p, 1080p, or 2160p).

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A corrected string representing the film's edition, or None.
        """

        # Search for any of the known qualities.
        match = re.search(patterns.quality, os.path.basename(source_path))

        # If a match exists, convert it to lowercase.
        quality = match.group('quality').lower() if match else None

        # If the quality doesn't end in p, append p.
        if quality is not None and 'p' not in quality:
            quality += 'p'
        return quality

    @classmethod
    def get_part(cls, source_path):
        """Get part # from full path of file or folder.

        Use regular expressions to identity the part # of the file.

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A string representing the part # of the title, or None, if no
            match is found.
        """

        # Search for a matching part condition
        match = re.search(patterns.part, os.path.basename(source_path))
        
        # If a match exists, convert it to lowercase.
        return match.group('part').upper() if match else None

    @classmethod
    def _edition_map(cls, source_path):
        """Internal method to search for special edition strings in a source_path.

        This method iterates through config.edition_map, generates regular
        expressions for each potential match, then returns a (key, value)
        tuple containing the first matching regular expression.

        Args:
            source_path: (str, utf-8) full path of file or folder.

        Returns:
            A (key, value) tuple containing either a matching regular expression and its
            corrected counterpart, or (None, None).
        """

        # Iterate over the edition map.
        for key, value in config.edition_map:
            # Generate a regular expression that searches for the search key, separated
            # by word boundaries.
            rx = re.compile(r'\b' + key + r'\b', re.I)

            # Because this map is in a specific order, of we find a suitable match, we
            # want to return it right away.
            if re.search(rx, os.path.basename(source_path)):
                # Return a tuple containing the matching compiled expression, and its
                # corrected value and break the loop.
                return (rx, value)

        # If no matches are found, return (None, None)
        return (None, None)