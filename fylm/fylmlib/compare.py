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

"""Object comparison tools for Fylm.

This module provides tools which are used to compare different object types
during runtime.
"""

from __future__ import unicode_literals, print_function

import re
from difflib import SequenceMatcher

import fylmlib.formatter as formatter
import fylmlib.patterns as patterns

def string_similarity(a, b):
    """Use SequenceMatcher to determine how similar one string is to another,
    loosely based on the Ratcliff and Obershelp algorithm (although it actually
    predates it)

    Args:
        a: (unicode) the first string to compare.
        b: (unicode) the second string to compare.
    Returns:
        A '% similarity' value, represented as a decimal between 0 and 1.
    """
    return SequenceMatcher(None, a, b).ratio()

def year_deviation(year, proposed_year):
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
    return abs(year - proposed_year)

def initial_chars_match(a, b, chars):
    """Determine if the first n characters of two strings are identical (case
    insensitive).

    Args:
        a: (unicode) the first string to compare.
        b: (unicode) the second string to compare.
        chars: (int) the number of characters to compare
    Returns:
        True if the characters match (case insensitive), else false
    """
    return a.lower()[:chars] == b.lower()[:chars]

# Algorithm to determine if one film is a duplicate of another
def is_duplicate(film, existing_film):
    """Determine if a film is a duplicate of another.

    Args:
        film: (Film) the first film to compare.
        existing_film: (Film) the second film to compare.
    Returns:
        True if the films are identical, else False
    """

    # Strip restricted chars from both films' titles, and compare lowercase (this
    # is important because we're not doing TMDb lookups on the existing film, and
    # we can't guarantee it was named with the correct case)
    title = re.sub(r'[^\w\d\-\s&]', '', formatter.strip_illegal_chars(film.title).lower())

    # Because existing_title is run through the Film init, which executes 
    # strip_from_title, we need to perform the same step on the original title.
    title = re.sub(patterns.strip_from_title, ' ', title)
    existing_title = re.sub(r'[^\w\d\-\s&]', '', formatter.strip_illegal_chars(existing_film.title).lower())

    # Return True if title, year, and edition are equal, otherwise return False.
    # This assumes that you may want to keep two different editions of the same film,
    # but works well with identifying copies with a different resolution or quality.

    return (title == existing_title
        and film.year == existing_film.year
        and film.edition == existing_film.edition)