# -*- coding: future_fstrings -*-
# Copyright 2021 Brandon Shelley. All Rights Reserved.
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

"""Set of enum values.

This module handles all the enumerable constants for Fylm.
"""
from __future__ import unicode_literals, print_function
from builtins import *

from enum import Enum

Should = Enum('Should', 'UPGRADE IGNORE KEEP_BOTH DELETE')
ComparisonResult = Enum('ComparisonResult', 'HIGHER EQUAL LOWER NOT_COMPARABLE')
Rename = Enum('Rename', 'FILE DIR')


class Resolution(Enum):
    UHD_2160P = 1
    HD_1080P = 2
    HD_720P = 3
    SD_576P = 4
    SD_480P = 5
    UNKNOWN = 6

    @property
    def display_name(self):
        if self == self.UHD_2160P:
            return "2160p"
        elif self == self.HD_1080P:
            return "1080p"
        elif self == self.HD_720P:
            return "720p"
        elif self == self.SD_576P:
            return "576p"
        elif self == self.SD_480P:
            return "480p"
        elif self == self.UNKNOWN:
            return None
        else:
            return self.name

class Media(Enum):
    BLURAY = 1
    WEBDL = 2
    HDTV = 3
    DVD = 4
    SDTV = 5
    UNKNOWN = 6
    @property
    def display_name(self) -> str:
        if self == self.BLURAY:
            return "Bluray"
        elif self == self.UNKNOWN:
            return None
        else:
            return self.name

class IgnoreReason(Enum):
    UNPACKING = 1
    IGNORED_STRING = 2
    TV_SHOW = 3
    INVALID_EXT = 4
    NO_VIDEO_FILES = 5
    UNKNOWN_TITLE = 6
    UNKNOWN_YEAR = 7
    TOO_SMALL = 8
    DOES_NOT_EXIST = 9
    NO_TMDB_RESULTS = 10
    @property
    def str(self) -> str:
        if self == self.UNPACKING:
            return "Currently unpacking"
        elif self == self.IGNORED_STRING:
            return "Contains an ignored word"
        elif self == self.TV_SHOW:
            return "TV show, not a film"
        elif self == self.INVALID_EXT:
            return "Not a valid file extension"
        elif self == self.NO_VIDEO_FILES:
            return "No video files in this folder"
        elif self == self.UNKNOWN_TITLE:
            return "Unknown title"
        elif self == self.UNKNOWN_YEAR:
            return "Unknown year"
        elif self == self.TOO_SMALL:
            return "Size is too small"
        elif self == self.DOES_NOT_EXIST:
            return "Path no longer exists"
        elif self == self.NO_TMDB_RESULTS:
            return "No results found"
        else:
            return None
