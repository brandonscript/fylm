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

"""Language detection for subtitle files.

This module is used to determine the language of subtitle files based on
name or content, by loading a ISO-639-1 language.json map file.

    Subtitle: the main class exported by this module.

Sample subtitle filenames:
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.croatian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.english.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.french.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.spanish-lat.srt
    ...etc.
"""

import re
import os

from fylmlib import languages

class Subtitle:
    """A subtitle object that contains information about its language.

    Attributes:
        path: Subtitle path.
    """
    def __init__(self, path):

        # Path to original subtitle file.
        self.path = path

        # The 2-character language identifier code of the subtitle.
        self.code = None

        # The full-length language of the subtitle.
        self.language = None

        # The language string captured from the original filename, e.g. 'english' or 'en'.
        self.captured = None
        
        # First we loop through languages to determine if the path contains
        # a descriptive language string, e.g. 'english', 'dutch', or 'fr'
        for lang in languages.get():
            
            patterns = []
                
            # Compile patterns that matches language strings and codes, case insensitive.
            for n in list(filter(None, lang.names)):
                patterns.append(re.compile(r'\.(?P<lang>' + re.escape(n).lower() + r'(?:-\w+)?\b)', re.I))
            patterns.append(re.compile(r'\.(?P<lang>' + re.escape(lang.code) + r'(?:-\w+)?\b)', re.I))
            
            # Iterate the array of patterns that we want to check for.
            for p in patterns:
                
                # Search for rx match.
                match = re.search(p, path)
                if match is not None and match.group('lang') is not None:
                
                    # If a match exists, convert it to lowercase and save the entire
                    # captured string.
                    self.captured = match.group('lang')[:1].upper() + match.group('lang')[1:]

                    # If we find a match, set the values of the subtitle, and break.
                    self.code = lang.code
                    self.language = lang.primary_name
                
                    break

            # Break from parent if captured is set.
            if self.captured is not None:
                break

    def insert_lang(self, path):
        """Returns a new path that includes the captured language string.

        Args:
            path: (str, utf-8) Path to file to append language.
        Returns:
            A new path with the subtitle language included in the path.
        """
        filename, ext = os.path.splitext(path)

        # if self.language is None:
        return f'{filename}.{self.captured}{ext}' if self.captured else None
