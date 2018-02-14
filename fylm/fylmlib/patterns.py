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

"""A set of regular expression patterns.

This module exports a set of regular expressions used for matching values
in file/folder paths.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import re
import sys

# Compiled pattern that matches a 4-digit year between 1921 and 2159.
# We ignore 2160 because it would conflict with 2160p, and we also
# ensure that it isn't at the beginning of the string and that it's
# preceded by a non-word char. (Looking at you, BT2020). We also ignore
# 1920 because of 1920x1080 resolution.
year = re.compile(r'\W+(?P<year>192[1-9]|19[3-9]\d|20[0-9]\d|21[0-5]\d)')

# Compiled pattern that matches 720p, 1080p, of 2160p, case insensitive.
quality = re.compile(r'(?P<quality>(?:72|108|216)0p?)', re.I)

# Compiled pattern that matches BluRay, WEB-DL, or HDTV, case insensitive.
media = re.compile(r'(?:(?P<bluray>bluray|bdremux)|(?P<web>web-?dl|webrip)|(?P<hdtv>hdtv))', re.I)

# Compiled pattern that matches all unwanted characters that should be
# stripped from a title:
#   - From entire title: . (period) _ (underscore) - (hyphen) and {}[]() (brackets/braces)
#   - From the end of a string: non-word chars and whitespace
strip_from_title = re.compile(r'([\._·\-\[\]{}\(\)]|[\s\W]+$)')

# Uncompiled pattern that matches illegal OS chars. Must remain uncompiled here.
illegal_chars = r'/?<>\:*|"' if (sys.platform == "win32") else r':'

# Compiled pattern of chars/articles to remove when using the _strip_articles
# TMDb search option.
strip_articles_search = re.compile(r'(^(the|a)\s|, the$)', re.I)

# Compiled pattern that matches articles 'the' and 'a' from the beginning, and
# ', the' from the end of a string. Used for comparing local titles to potential
# TMDb matches.
strip_when_comparing = re.compile(r'([\W]|\b\d\b|^(the|a)\b|, the)', re.I)