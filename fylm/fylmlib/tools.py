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

from fylmlib.constants import *

def first(iterable: Iterable, where=None, default=None):
    """Returns the first item in the `iterable` that satisfies the `where` 
    condition, or the `default` value if provided.
    
    Args:
        iterable (iterable):    An iterable
        where (lambda):         Condition to apply
        default: Default        value to return if no result is found
    """
    
    return next((x for x in iterable if where(x)) 
                if where else iterable, default)

def last(iterable: Iterable, where=None, default=None):
    """Returns the last item in the `iterable` that satisfies the `where` 
    condition, or the `default` value if provided.
    
    Args:
        iterable (iterable):    An iterable
        where (lambda):         Condition to apply
        default: Default        value to return if no result is found
    """
    
    try:
        *_, last = ((x for x in iterable if where(x)) 
                    if where else iterable)
        return last
    except (StopIteration, ValueError):
        return default
    
def iterunshift(*prepend, to: Iterable):
    """Uses itertools.chain to prepend an object or list 
    to the beginining of an iterator.
    
    Args:
        prepend (object or list): An object or list to prepend.
        to (Iterable): The iterable to prepend to."""
    
    for p in prepend:
        if not type(p) is list:
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
