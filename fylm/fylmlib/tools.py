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

"""A set of general use helper functions"""

from __future__ import unicode_literals, print_function
from builtins import *
from typing import Iterable, Union

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
    except:
        return default

def iterempty(iterable: Iterable) -> bool:
    """Checks if an iterable is empty.

    Args:
        iterable (Iterable): Iterable to check
        
    Returns:
        bool: True if the iterable is empty.
    """
    return any(True for _ in iterator)

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
    