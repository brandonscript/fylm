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

"""Set of enum values as constants.

This module handles all the enumerable constants for Fylm.
"""
from __future__ import unicode_literals, print_function
from builtins import *

from enum import Enum

Should = Enum('Should', 'UPGRADE IGNORE KEEP_BOTH DELETE')
ComparisonResult = Enum('ComparisonResult', 'HIGHER EQUAL LOWER NOT_COMPARABLE')
Resolutions = Enum('Resolutions', '2160P 1080P 720P 576P 480P UNKNOWN')

class Media(Enum):
    BLURAY = 1
    WEBDL = 2
    HDTV = 3
    DVD = 4
    SDTV = 5
    UNKNOWN = 6
    @property
    def display_name(self):
        if self == self.BLURAY:
            return "Bluray"
        elif self == self.UNKNOWN:
            return None
        else:
            return self.name
