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

from lazy import lazy
from typing import Union

import fylmlib.config as config
import fylmlib.patterns as patterns
import fylmlib.formatter as formatter
from fylmlib.tools import last
from fylmlib.enums import Media, Resolution

class Parser(object):
    """A collection of string parsing utilities to apply regular 
    expressions and extract critical information from a path. 
    Instantiate Parser with your path, then call properties on it.
    
    Attributes:
    
        path ()
    Args:
        path (str, Path, or FilmPath): Relative or absolute path to a film file
    
    """
    def __init__(self, path: Union[str, 'Path', 'FilmPath'], mediainfo=None):
        
        if type(path) is str:
            self._p = path    
        else:
            from fylmlib.operations import FilmPath
            f = FilmPath(path)
            try:
                self._p = str(f) if f == f.filmroot else str(f.relative_to(f.filmroot))
            except:
                self._p = str(f)
            
        self.mediainfo = mediainfo
    
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

        # Determine whether to use the file or its containing folder
        # to determine the title by checking for year and resolution
        title = self.dir if self.year or self.resolution else self.file

        # Remove the file extension.
        title = Path(title).stem

        # Strip "tag" prefixes from the title.
        for prefix in config.strip_prefixes:
            if title.lower().startswith(prefix.lower()):
                title = title[len(prefix):]
        
        # Use the 'strip_from_title' regular expression to replace unwanted
        # characters in a title with a space.
        title = re.sub(patterns.strip_from_title, ' ', title)
        
        # If the title contains a known edition, strip it from the title. E.g.,
        # if we have Dinosaur.Special.Edition, we already know the edition, and
        # we don't need it to appear, duplicated, in the title. Because
        # `_edition_map` returns a (key, value) tuple, we check for the search
        # key here and replace it (not the value).
        if self._edition_map[0] is not None:
            title = re.sub(self._edition_map[0], '', title)

        # Strip all resolution and media tags from the title.
        title = re.sub(patterns.media, '', title)
        title = re.sub(patterns.resolution, '', title)

        # Typical naming patterns place the year as a delimiter between the title
        # and the rest of the file. Therefore we can assume we only care about
        # the first part of the string, and so we split on the year value, and keep
        # only the left-hand portion.
        title = title.split(str(self.year))[0]

        # If a title ends with , The, we need to remove it and prepend it to the
        # start of the title.
        if re.search(patterns.begins_with_or_comma_the, title):
            title = f"The {re.sub(patterns.begins_with_or_comma_the, '', title)}"

        # Add back in . to titles or strings we know need to to keep periods.
        # Looking at you, S.W.A.T and After.Life.
        for k in config.keep_period:
            q = k.replace('.', '[ .]')
            rx = re.compile(r'\b' + q + r'?', re.I)
            if re.search(rx, title):
                title = re.sub(rx, k + ' ', title)
                break

        # Remove trailing non-word characters like ' - '
        title = formatter.strip_trailing_nonword_chars(title)

        # Remove extra whitespace from the edges of the title and remove repeating
        # whitespace.
        title = formatter.strip_extra_whitespace(title.strip())

        # Correct the case of the title
        title = formatter.title_case(title)

        # Always uppercase strings that are meant to be in all caps
        for u in config.always_upper:
            rx = re.compile(r'\b' + u + r'\b', re.I)
            if re.search(rx, title):
                title = re.sub(rx, u, title)
        
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
        # Find all matches of years between 1910 and 2159 (we don't want to
        # match 2160 because 2160p, and hopefully I'll be dead by then and
        # no one will use python anymore). Also convert the matches iterator
        # to a list.
        m = last(re.finditer(patterns.year, self._p), default=None)
        # Get the last element, and retrieve the 'year' capture group by name.
        # If there are no matches, return None.
        return int(m.group('year')) if m else None

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
        
        if self.mediainfo:
            try:
                if self.mediainfo.width == 3840:
                    return Resolution.UHD_2160P
                elif self.mediainfo.width == 1920:
                    return Resolution.HD_1080P
                elif self.mediainfo.width == 1280:
                    return Resolution.HD_720P
                elif self.mediainfo.width == 1024:
                    return Resolution.SD_576P
                elif self.mediainfo.width == 852:
                    return Resolution.SD_480P
            except:
                pass

        # Search for any of the known qualities.
        match = re.search(patterns.resolution, self.relpath)

        # If a match exists, convert it to lowercase.
        resolution = match.group('resolution').lower() if match else None
        if resolution == '4k' or resolution.startswith('2160'):
            return Resolution.UHD_2160P
        elif resolution.startswith('1080'):
            return Resolution.HD_1080P
        elif resolution.startswith('720'):
            return Resolution.HD_720P
        elif resolution.startswith('576'):
            return Resolution.SD_576P
        elif resolution.startswith('480'):
            return Resolution.SD_480P
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

        match = re.search(patterns.media, self.relpath)
        if match and match.group('bluray'):
            return Media.BLURAY
        elif match and match.group('webdl'):
            return Media.WEBDL
        elif match and match.group('hdtv'):
            return Media.HDTV
        elif match and match.group('dvd'):
            return Media.DVD
        elif match and match.group('sdtv'):
            return Media.SDTV
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

        match = re.search(patterns.hdr, str(self.relpath))
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

        match = re.search(patterns.proper, str(self.relpath))
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
        match = re.search(patterns.part, str(self.relpath))
        
        # If a match exists, convert it to uppercase.
        return match.group('part').upper() if match else None

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
            result = re.search(rx, str(self.relpath))
            if result:
                # Return a tuple containing the matching compiled expression and its
                # corrected value after performing a capture group replace, then break 
                # the loop.
                return (rx, rx.sub(value, result.group()))

        # If no matches are found, return (None, None)
        return (None, None)
