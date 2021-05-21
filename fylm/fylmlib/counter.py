#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

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

"""Singleton to count the number of successfully moved films.

This module must be loaded using `import counter` in order to preserve its
singleton nature. It is used to keep track of successful moves/renames.

    count: main property exported by this module.
"""

# Counter property
COUNT = 0

def add(num):
    """Increment the COUNT property by value (num)

    Args:
        num: (int) the number to add to the existing count.
    """

    # Pull in the module's (global) count variable.
    global COUNT

    # Increment the COUNT property.
    COUNT += num
