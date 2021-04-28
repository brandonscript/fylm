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

"""Main file parser for Fylm.

This module takes raw input source paths and cleans/analyzes them
to determine various properties used in the name correction
and TMDb lookup.

    parser: the main class exported by this module.
"""

import os
import re

from lazy import lazy
from typing import Union

import fylmlib.config as config
import fylmlib.patterns as patterns
from fylmlib.tools import *
from fylmlib.enums import *
from fylmlib import Format
from fylmlib import Console
from timeit import default_timer as timer

class Parser:
    """A collection of string parsing utilities to apply regular 
    expressions and extract critical information from a path. 
    Instantiate Parser with your path, then call properties on it.
    
    Attributes:
    
        path ()
    Args:
        path (str, Path, or FilmPath): Relative or absolute path to a film file
    
    """
    def __init__(self, path: Union[str, 'Path', 'FilmPath']):
        
        try:
            self.path = path.main_file.filmrel if path.exists() else path
        except:
            self.path = path
        self.s = str(self.path)
    
    @lazy
    def title(self) -> str:
        """Get title from full path of file or folder.

        Use regular expressions to strip, clean, and format a file
        or folder path into a more pleasant film title.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A clean and well-formed film title.
        """
        
        start = timer()

        # Use the FilmPath's filmrel to identify the original title, 
        # remove the extension.
        title = self.s
        
        # Strip "tag" prefixes from the title.
        for prefix in config.strip_prefixes:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):]
        
        # Use the 'STRIP_FROM_TITLE' regular expression to replace unwanted
        # characters in a title with a space.
        title = re.sub(patterns.STRIP_FROM_TITLE, ' ', title)
        
        # If the title contains a known edition, strip it from the title. E.g.,
        # if we have Dinosaur.Special.Edition, we already know the edition, and
        # we don't need it to appear, duplicated, in the title. Because
        # `_edition_map` returns a (key, value) tuple, we check for the search
        # key here and replace it (not the value).
        if self._edition_map[0] is not None:
            title = re.sub(self._edition_map[0], '', title)

        # Typical naming patterns place the year as a delimiter between the title
        # and the rest of the file. Therefore we can assume we only care about
        # the first part of the string, and so we split on the year value, and keep
        # only the left-hand portion.
        title = title.split(str(self.year))[0]
        
        # Strip all resolution and media tags from the title.
        title = re.sub(patterns.MEDIA, '', title)
        title = re.sub(patterns.RESOLUTION, '', title)

        # If a title ends with , The, we need to remove it and prepend it to the
        # start of the title.
        if re.search(patterns.THE_PREFIX_SUFFIX, title):
            title = f"The {re.sub(patterns.THE_PREFIX_SUFFIX, '', title)}"

        # Add back in . to titles or strings we know need to to keep periods.
        # Looking at you, S.W.A.T and After.Life.
        for k in config.keep_period:
            q = k.replace('.', '[ .]')
            rx = re.compile(r'\b' + q + r'?', re.I)
            if re.search(rx, title):
                title = re.sub(rx, k + ' ', title)
                break

        # Remove trailing non-word characters like ' - '
        title = Format.strip_trailing_nonword_chars(title)

        # Remove extra whitespace from the edges of the title and remove repeating
        # whitespace.
        title = Format.strip_extra_whitespace(title.strip())

        # Correct the case of the title
        title = Format.title_case(title)

        """
        # Always uppercase strings that are meant to be in all caps
        for u in config.always_upper:
            rx = re.compile(r'\b' + u + r'\b', re.I)
            if re.search(rx, title):
                title = re.sub(rx, u, title)
        """
        end = timer()
        if round(end - start) > 1:
            Console.slow(
                f"Took a long time parsing title from '{self.path.filmrel}'", end - start)
        
        return title

    @lazy
    def year(self) -> int:
        """Get year from full path of file or folder.

        Use regular expressions to identity a year value between 1910 and 2159,
        getting the right-most match if there is more than one year found (looking
        at you, 2001: A Space Odyssey) and not at the start of the input string
        or filename.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A 4-digit integer representing the release year, or None if
            no year could be determined.
        """
        start = timer()
        # Find all matches of years between 1910 and 2159 (we don't want to
        # match 2160 because 2160p, and hopefully I'll be dead by then and
        # no one will use python anymore).
        m = last(re.finditer(patterns.YEAR, self.s), default=None)
        # Get the last element, and retrieve the 'year' capture group by name.
        # If there are no matches, return None.
        year = int(m.group('year')) if m else None
        end = timer()
        if round(end - start) > 1:
            Console.slow(
                f"Took a long time parsing title from '{self.path.filmrel}'", end - start)
        return year

    @lazy
    def edition(self) -> str:
        """Get and correct special edition from full path of file or folder.

        Iterate a map of strings (or, more aptly, regular expressions) to
        search for, and correct, special editions. This map is defined in
        config.edition_map.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A corrected string representing the film's edition, or None.
        """

        # Because _edition_map returns a (key, value) tuple, we need to
        # return the second value in the tuple which represents the corrected
        # string value of the edition.
        return self._edition_map[1] or None

    @lazy
    def resolution(self) -> str:
        """Parse resolution from a path string using a regular expression,
        or optionally from a provided mediainfo object.
        
        Args:
            path (str): Relative path for a file (file.ext or dir/file.ext)

        Returns:
            A an Enum representing the file's resolution, or None.
        """

        # Search for any of the known qualities.
        m = last(re.finditer(patterns.RESOLUTION, self.s), default=None)
        # Get the last element, and retrieve the 'year' capture group by name.
        # If there are no matches, return None.
        
        if not m:
            return Resolution.UNKNOWN

        # If a match exists, convert it to lowercase.
        resolution = m.group('resolution')
    
        if resolution == '4k' or resolution.startswith('2160'): 
            return Resolution.UHD_2160P
        elif resolution.startswith('1080'): return Resolution.HD_1080P
        elif resolution.startswith('720'): return Resolution.HD_720P
        elif resolution.startswith('576'): return Resolution.SD_576P
        elif resolution.startswith('480'): return Resolution.SD_480P
        return Resolution.UNKNOWN

    @lazy
    def media(self) -> str:
        """Get media from full path of file or folder.

        Use regular expressions to identity the original media of the file.

        Args:
            path (str): Relative path of file or folder/file.

        Returns:
            An enum representing the media found.
        """

        match = re.search(patterns.MEDIA, self.s)
        if match and match.group('bluray'): return Media.BLURAY
        elif match and match.group('webdl'): return Media.WEBDL
        elif match and match.group('hdtv'): return Media.HDTV
        elif match and match.group('dvd'): return Media.DVD
        elif match and match.group('sdtv'): return Media.SDTV
        return Media.UNKNOWN

    @lazy
    def is_hdr(self) -> str:
        """Determine whether the media is an HDR file.

        Use regular expressions to identity whether the media is HDR or not.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A bool representing the HDR status of the media.
        """

        match = re.search(patterns.HDR, str(self.s))
        return True if (match and match.group('hdr')) else False

    @lazy
    def is_proper(self) -> str:
        """Determine whether the media is a proper rip.

        Use regular expressions to identity whether the file is a proper or not.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A bool representing the proper state of the media.
        """

        match = re.search(patterns.PROPER, str(self.s))
        return True if (match and match.group('proper')) else False

    @lazy
    def part(self) -> str:
        """Get part # from full path of file or folder.

        Use regular expressions to identity the part # of the file.

        Args:
            path: (str, utf-8) full path of file or folder.

        Returns:
            A string representing the part # of the title, or None, if no
            match is found.
        """

        # Search for a matching part condition
        match = re.search(patterns.PART, str(self.s))
        
        # If a match exists, convert it to uppercase.
        return match.group('part').upper() if match else None

    @lazy
    def _edition_map(self) -> (str, str):
        """Internal method to search for special edition strings in a path.

        This method iterates through config.edition_map, generates regular
        expressions for each potential match, then returns a (key, value)
        tuple containing the first matching regular expression.

        Args:
            path: (str, utf-8) full path of file or folder.

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
            result = re.search(rx, str(self.path.filmrel))
            if result:
                # Return a tuple containing the matching compiled expression and its
                # corrected value after performing a capture group replace, then break 
                # the loop.
                return (rx, rx.sub(value, result.group()))

        # If no matches are found, return (None, None)
        return (None, None)
