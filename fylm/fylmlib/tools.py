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

"""A set of general use helper functions"""

from typing import Iterable, Union
import itertools
import re
import math
import inflect
p = inflect.engine()

import fylmlib.patterns as patterns
from fylmlib.constants import *

# Compare a list and see if they all match

def all_match(l: list) -> bool:
    """Compare a list and see if they all match

    Args:
        l (list): List to check

    Returns:
        bool: True if all items in the list match
    """
    return all(o == l[0] for o in l if o)

def num(x):
    """Coerces any numeric type to the lowest fidelity
    possible (int or float).

    Args:
        x (numberish):    The number to coerce

    Returns:
        Number coerced to int or float, or None
    """
    if not x:
        return None
    return int(x) if math.floor(x) == float(x) else float(x)

def first(iterable: Iterable, where=None, default=None):
    """Returns the first item in the `iterable` that satisfies the `where`
    condition, or the `default` value if provided.

    Args:
        iterable (iterable):    An iterable
        where (lambda):         Condition to apply
        default: Default        value to return if no result is found

    Returns:
        First iterable, first iterable that matches condition, or default.
    """
    if iterable is None: return
    iterable = iter(iterable) if isinstance(iterable, list) else iterable
    return next((x for x in iterable if where(x))
                if where else iterable, default)

def last(iterable: Iterable, where=None, default=None):
    """Returns the last item in the `iterable` that satisfies the `where`
    condition, or the `default` value if provided.

    Args:
        iterable (iterable):    An iterable
        where (lambda):         Condition to apply
        default: Default        value to return if no result is found

    Returns:
        Last iterable, last iterable that matches condition, or default.
    """

    try:
        *_, last = ((x for x in iterable if where(x))
                    if where else iterable)
        return last
    except (StopIteration, ValueError):
        return default

def prepend(*prepend, to: Iterable):
    """Uses itertools.chain to prepend an object or list
    to the beginining of an iterator. Same as "unshift".

    Args:
        prepend (object or list): An object or list to prepend.
        to (Iterable): The iterable to prepend to."""

    for p in prepend:
        if not isinstance(p, list):
            p = [p]
        to = itertools.chain(p, to)
    return to

def iterempty(iterable: Iterable) -> bool:
    """Checks if an iterable is empty.

    Args:
        iterable (Iterable): Iterable to check

    Returns:
        bool: True if the iterable is empty.
    """
    return any(True for _ in iterator)


def iterlen(iterable: Iterable) -> int:
    """Counts the number of items in the iterator.

    Args:
        iterable (Iterable): Iterable to count.

    Returns:
        int: Counts the number of items in the iterator.
    """
    return sum(1 for _ in iterable)

def is_number(s):
    """Tests if string is likely numeric, or numberish

    Args:
        s (str, utf-8): Input string to check
    Returns:
        True if the string is a number, otherwise False
    """
    try:
        float(s)
        return True
    except:
        pass
    return any([s.isnumeric(), s.isdigit()])

def is_roman_numeral(s):
    """Tests if string is exactly a roman numeral

    Args:
        s (str, utf-8): Input string to check
    Returns:
        True if the string is a roman numeral, otherwise False
    """
    match = re.search(patterns.ROMAN_NUMERALS, s)
    return True if (match and match.group(1)) else False

def is_sys_file(path: Union[str, 'Path', 'FilmPath']) -> bool:
    """Checks to see if the path provided is a system file.

    Args:
        path (str or Pathlike): Path to check

    Returns:
        bool: True if it's a system file, otherwise False
    """
    try:
        # Try to coerce a Pathlike object to a string
        x = path.name
    except:
        x = str(path)

    return (x.lower().startswith('.')
            or x.lower() in [sys.lower() for sys in SYS_FILES])
