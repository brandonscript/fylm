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

"""Language detection for subtitle files.

This module is used to determine the language of subtitle files based on
name or content, by loading a ISO-639-1 language.json map file.

    Subtitle: the main class exported by this module.

Sample subtitle fileames:
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.bulgarian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.croatian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.czech.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.danish.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.dutch.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.english-forced.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.english-sdh.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.english.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.estonian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.finnish.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.french.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.german.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.hungarian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.icelandic.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.italian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.latvian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.lithuanian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.norwegian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.portuguese-br.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.portuguese-pt.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.russian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.serbian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.slovenian.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.spanish-cas.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.spanish-lat.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.swedish.srt
    The.Planet.Beyond.2010.1080p.BluRay.x264-Group.ukrainian.srt

"""

from __future__ import unicode_literals, print_function
from builtins import *

import re
import os

from fylmlib.languages import languages

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
        for lang in languages:
            
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

    @classmethod
    def is_subtitle(cls, file):
        """Determine if a file is a subtitle file.

        Args:
            file: (str, utf-8) File to determine whether or not it is a subtitle file.
        Returns:
            True if the file is a subtitle file (.srt), else False.
        """
        try:
            return os.path.splitext(file)[1].lower() == '.srt'
        except IOError:
            # Return false if the file does not exist
            return False