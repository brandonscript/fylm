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

"""Object comparison tools for Fylm.

This module provides tools which are used to compare different object types
during runtime.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import re
import warnings
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

from fuzzywuzzy import fuzz

import fylmlib.formatter as formatter
import fylmlib.patterns as patterns

def title_similarity(a, b):
    """Compare parsed title to TMDb title.

    Performs an intelligent string comparison between the original parsed
    title and the TMDb result.

    Returns:
        A decimal value between 0 and 1 representing the similarity between
        the two titles.
    """

    # Because we can't guarantee how similar parsed titles will be to search results,
    # (mixed case, missing symbols, or illegal OS chars), we strip unwanted chars from
    # both the original and TMDb title, and convert both to lowercase so we can get
    # a more accurate string comparison.
    a = ' '.join(re.sub(patterns.strip_when_comparing, ' ', a).lower().split())
    b = ' '.join(re.sub(patterns.strip_when_comparing, ' ', b or '').lower().split())    
    return fuzz.token_sort_ratio(a, b) / 100

def year_deviation(year, proposed_year) -> int:
    """Calculate the difference between the expected year of a film to a
    counterpart release year retrieved from TMDb.

    Args:
        year: (int) the year parsed from the filename.
        proposed_year: (int) the proposed year retrieved from TMDb
    Returns:
        A deviation, in years, between the parsed year and the proposed year.
    """

    # If the original year was not specified,
    # we assume the resulting year is acceptable, and thus we return a 0 deviation.
    if proposed_year is None or year is None: return 0

    # Calculate the absolute difference in years and return the value.
    return int(abs(year - proposed_year))

def initial_chars_match(a, b, chars):
    """Determine if the first n characters of two strings are identical (case
    insensitive).

    Args:
        a: (str, utf-8) the first string to compare.
        b: (str, utf-8) the second string to compare.
        chars: (int) the number of characters to compare
    Returns:
        True if the characters match (case insensitive), else false
    """
    return a.lower()[:chars] == b.lower()[:chars]

# Heuristic to determine if one film is a duplicate of another
def is_duplicate(film, existing_film):
    """Determine if a film is a duplicate of another. To qualify as
    a duplicate, it must match in title and year. Edition, quality,
    and media are ignored.

    Args:
        film: (Film) the first film to compare.
        existing_film: (Film) the second film to compare.
    Returns:
        True if the films are identical, else False
    """

    invalid_comparison_chars = re.compile(r'[^\w\d\s&.]', re.I)

    # Strip restricted chars from both films' titles, and compare lowercase (this
    # is important because we're not doing TMDb lookups on the existing film, and
    # we can't guarantee it was named with the correct case)
    title = re.sub(invalid_comparison_chars, '', formatter.strip_illegal_chars(film.title).lower())

    # Because existing_title is run through the Film init, which executes 
    # strip_from_title, we need to perform the same step on the original title.
    title = " ".join(re.sub(patterns.strip_from_title, ' ', title).strip().split())
    existing_title = " ".join(re.sub(invalid_comparison_chars, '', formatter.strip_illegal_chars(existing_film.title).lower()).strip().split())

    # Return True if title, year, and edition are equal, otherwise return False.
    # This assumes that you may want to keep two different editions of the same film,
    # but works well with identifying copies with a different resolution or quality.
    return (title == existing_title and film.year == existing_film.year)

# Heuristic to determine if a file is higher or lower quality than another
def is_higher_quality(file, existing_file):
    """Determine if a file is a higher or lower quality than another
    for matching resolutions. Compare media and proper status.

    Args:
        file: (Film.File) the first film to compare.
        existing_file: (Film.File) the second file to compare.
    Returns:
        True if the files are identical, else False
    """

    media_hierarchy = ["bluray", "webdl", "hdtv", "dvd", "sdtv"]
    # resolution_hierarchy = ["2160p", "1080p", "720p", "576p", "480p"]

    # Because this method is primarily used to determine if one file should replace another, 
    # we throw an error if the resolution is not the same - this protects false positives
    # from being discarded when config asks to keep multiple qualities.
    if file.resolution != existing_file.resolution:
        raise Exception(f'Unable to accurately determine which of \'{file.source_path}\' and \'{existing_file.source_path}\' is the better quality')

    # Media is different, determine which one is better
    if file.media is not None and existing_file.media is not None and file.media != existing_file.media:
        return media_hierarchy.index(file.media.lower()) < media_hierarchy.index(existing_file.media.lower())
    # One is a proper, one is not
    elif file.is_proper is True and existing_file.is_proper is False:
        return True