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

"""Set of enum values.

This module handles all the enumerable constants for Fylm.
"""

from enum import Enum

Should = Enum('Should', 'UPGRADE IGNORE KEEP_BOTH DELETE')
ComparisonResult = Enum('ComparisonResult', 'HIGHER EQUAL LOWER NOT_COMPARABLE')
RenameMask = Enum('RenameMask', 'FILE DIR')
Units = Enum('Units', 'B KiB MiB GiB KB MB GB')

class Resolution(Enum):
    UHD_2160P = 1
    HD_1080P = 2
    HD_720P = 3
    SD_576P = 4
    SD_480P = 5
    UNKNOWN = 6
    @property
    def display_name(self):
        if self == self.UHD_2160P: return "2160p"
        elif self == self.HD_1080P: return "1080p"
        elif self == self.HD_720P: return "720p"
        elif self == self.SD_576P: return "576p"
        elif self == self.SD_480P: return "480p"
        elif self == self.UNKNOWN: return None
        else: return self.name

class Media(Enum):
    BLURAY = 1
    WEBDL = 2
    HDTV = 3
    DVD = 4
    SDTV = 5
    UNKNOWN = 6
    @property
    def display_name(self) -> str:
        if self == self.BLURAY: return "Bluray"
        elif self == self.UNKNOWN: return None
        else: return self.name

class IgnoreReason(Enum):
    UNPACKING = 1
    IGNORED_STRING = 2
    SAMPLE = 3
    TV_SHOW = 4
    INVALID_EXT = 5
    NO_VIDEO_FILES = 6
    UNKNOWN_YEAR = 7
    TOO_SMALL = 8
    DOES_NOT_EXIST = 9
    NO_TMDB_RESULTS = 10
    SYS = 11
    @property
    def str(self) -> str:
        # Ignoring because...
        if self == self.UNPACKING: return "it is unpacking"
        elif self == self.SAMPLE: return "it is a sample"
        elif self == self.IGNORED_STRING: return "it contains an ignored word"
        elif self == self.TV_SHOW: return "it is a TV show"
        elif self == self.INVALID_EXT: return "it does not have a valid file extension"
        elif self == self.NO_VIDEO_FILES: return "it doesn't contain video files"
        elif self == self.UNKNOWN_YEAR: return "it doesn't have a year"
        elif self == self.TOO_SMALL: return "it is too small"
        elif self == self.DOES_NOT_EXIST: return "this file or folder no longer exists"
        elif self == self.NO_TMDB_RESULTS: return "no TMDb results were found"
        elif self == self.SYS: return "it is a system file or dir"
        else: return None
