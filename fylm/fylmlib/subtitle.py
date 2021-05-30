#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

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
from pathlib import Path
from typing import Union

from fylmlib.languages import Languages
import fylmlib.constants as constants
from fylmlib import Console

_LANGUAGES = Languages().load()

class Subtitle:
    """A subtitle object that contains information about its language.

    Attributes:
        path: Subtitle path.
    """
    def __init__(self, path):

        if not Path(path).suffix.lower() in constants.SUB_EXTS:
            Console.error(f"{INDENT}'{path}' is not a valid subtitle file")
            return

        # Path to original subtitle file.
        self.path = path

        # The 2-character language identifier code of the subtitle.
        self.code = None

        # The full-length language of the subtitle.
        self.language = None

        # The language string captured from the original filename, e.g. 'english' or 'en'.
        self.captured = None

        def pattern(s):
            return re.compile(r'\b(?P<lang>' + re.escape(s) + r'(?:-\w{2})?)\b', re.I)

        # First we loop through languages to determine if the path contains
        # a descriptive language string, e.g. 'english', 'dutch', or 'fr'
        for lang in _LANGUAGES:

            patterns = []

            # Compile patterns that matches language strings and codes, case insensitive.
            patterns.append(pattern(lang.code))
            for n in list(filter(None, lang.names)):
                patterns.append(pattern(n))
                patterns.append(pattern(n[:3]))

            # Iterate the array of patterns that we want to check for.
            for p in patterns:

                # Search for rx match.
                match = re.search(p, self.path.name)
                if match and match.group('lang'):

                    # If a match exists, store it
                    self.captured = match.group('lang')

                    # If we find a match, set the values of the subtitle, and break.
                    self.code = lang.code
                    self.language = lang.primary_name

                    break

            # Break from parent if captured is set.
            if self.captured:
                break

    def path_with_lang(self, path: Union[str, Path, 'FilmPath']) -> Path:
        """Returns a new path that includes the captured language string.

        Returns:
            Path: A new path with the subtitle language included in the path.
        """

        assert self.path, "Subtitle was not initalized before 'new_name' was called."

        if isinstance(path, str):
            path = Path(path)

        return path.with_suffix('.' + self.captured + path.suffix) if self.captured else path
