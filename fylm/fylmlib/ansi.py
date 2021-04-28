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

"""Color handling for console output.

ANSI color map for console output. Get a list of colors here = 
http://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#256-colors

You can change the colors the terminal outputs by changing the 
ANSI values here.

    ansi is the main property exported by this module.
"""

class _AnsiColors:
    """Main class for mapping name values to ansi color codes.
    """
    def __init__(self):
        self.green = 35
        self.red = 1
        self.blue = 32
        self.light_blue = 37
        self.yellow = 214
        self.amber = 208
        self.olive = 106
        self.orange = 166
        self.purple = 18
        self.pink = 197
        self.gray = 243
        self.dark_gray = 235
        self.light_gray = 248
        self.black = 0
        self.white = 255
        self.error = 1
        self.debug = 160

ansi = _AnsiColors()
