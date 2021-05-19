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

"""A set of regular expression patterns.

This module exports a set of regular expressions used for matching values
in file/folder paths.
"""

import re
import sys

_ROMAN_NUMERALS = r'(?:(?=[MDCLXVI])M*(?:C[MD]|D?C{0,3})(?:X[CL]|L?X{0,3})(?:I[XV]|V?I{0,3}))'

# A list of articles
ARTICLES = ['&', 'a', 'an', 'and', 'as', 'at', 'by',
            'for', 'in', 'is', 'of', 'or', 'the', 'to', 'with']

# Compiled pattern that matches a 4-digit year between 1921 and 2159.
# We ignore 2160 because it would conflict with 2160p, and we also
# ensure that it isn't at the beginning of the string and that it's
# preceded by a word boundary. (Looking at you, 2001 and BT2020). We
# also ignore 1920 because of 1920x1080 resolution. It also cannot be
# at the start of the input string or after a /.
YEAR = re.compile(r'(?<![\/])(?!^)\b(?P<year>192[1-9]|19[3-9]\d|20[0-9]\d|21[0-5]\d)\b')

# Compiled pattern that matches 720p, 1080p, or 2160p, case insensitive.
RESOLUTION = re.compile(r'\b(?P<resolution>(?:(?:72|108|216)0p?)|4K)\b', re.I)

# Compiled pattern that matches BluRay, WEB-DL, or HDTV, case insensitive.
MEDIA = re.compile(r'\b(?:'
                    r'(?P<bluray>blu-?ray|bdremux|bdrip)|'
                    r'(?P<webdl>web-?dl|webrip|amzn|nf|hulu|dsnp|atvp)|'
                    r'(?P<hdtv>hdtv)|'
                    r'(?P<dvd>dvd)|'
                    r'(?P<sdtv>sdtv))\b', re.I)

# Compiled pattern that matches Proper, case insensitive.
PROPER = re.compile(r'\d{4}.*?\b(?P<proper>proper)\b', re.I)

# Compiled pattern that matches HDR.
HDR = re.compile(r'\b(?P<hdr>hdr)\b', re.I)

# Compiled pattern that "Part n" where n is a number or roman numeral.
# Can only occur after a year, to avoid false positives like Back to the Future.
PART = re.compile(
    r'(?<=\d{4})[^\\/]*\bpart\W?(?P<part>(?:\d+|' + _ROMAN_NUMERALS + r'))\b', re.I
)

# Retrieves tmdb_id in [XXXX] format from a string
TMDB_ID = re.compile(r'(?P<tmdb_id>\[\d+\])$')

# Compiled pattern to match roman numerals
ROMAN_NUMERALS = re.compile(r'\b(' + _ROMAN_NUMERALS + r')\b', re.I)

# Compiled pattern that matches all unwanted characters that should be
# stripped from a title:
#   - From entire title: . (period) _ (underscore) and {}[]() (brackets/braces)
#   - From the end of a string: non-word chars and whitespace
STRIP_FROM_TITLE = re.compile(r'([\._\[\]{}\(\)]|[\s\W]+$)')

# Uncompiled pattern that matches illegal OS chars. Must remain uncompiled here.
ILLEGAL_CHARS = r'/?<>\:*|"' if (sys.platform == "win32") else r':'

# Compiled pattern of chars/articles to remove when using the _strip_articles
# TMDb search option.
STRIP_WHEN_SEARCHING = re.compile(r'(^(the|a)\s|, the$)', re.I)

# Compiled pattern that matches articles 'the' and 'a' from the beginning, and
# ', the' from the end of a string. Used for comparing local titles to potential
# TMDb matches.
STRIP_WHEN_COMPARING = re.compile(r'([\W]|\b\d\b|^(the|a)\b|, the)', re.I)

# Beginning or end of string "The" or ", The", ignoring non-word characters
# at the end of the string.
THE_PREFIX_SUFFIX = re.compile(r'(^the\W+|, the\W*$)', re.I)

# ANSI character escaping
ANSI_ESCAPE = re.compile(r'(^\s+|(\x9B|\x1B\[)[0-?]*[ -/]*[@-~])', re.I)

# Intra-word special chars that we want to keep, and capitalize the following
# letter.
INTRA_WORD_SPECIAL_CHARS = re.compile(r'(?<=[^\W])([:\-_•·.])(?=[^\W])', re.I)

# Non-word chars to strip from the end of a title
TRAILING_NONWORD_CHARS = re.compile(r'[\b\s]*[-_:]\s*$', re.I)

# Matches all non-word chars in a string
ALL_NONWORD_CHARS = re.compile(r'[^0-9a-zA-Z]+')

# Zero-width space
ZERO_SPACE = u'\u200c'

# TV show
TV_SHOW = re.compile(r"\bS\d{2}(E\d{2})?\b", re.I)

# Unpacking
UNPACK = re.compile(r"^_UNPACK", re.I)

# Encoding
ENCODING = re.compile(f"x26[45].*$", re.I)

# Sample
SAMPLE = re.compile(r"\bsample\b", re.I)
