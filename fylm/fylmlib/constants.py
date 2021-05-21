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

"""Set of constants.

This module handles all the enumerable constants for Fylm.
"""

SYS_FILES = ['@eaDir', 'Thumbs.db', '.DS_Store']
VIDEO_EXTS = ['.mkv', '.mp4', '.m4v', '.avi']
SUB_EXTS = ['.srt', '.sub']
ARROW = '➜'
ARROW2 = '»'
INDENT = '   '
INDENT_WIDE = '    '
INDENT_ARROW = f'{INDENT}{ARROW}'
PROMPT =       f'{INDENT}{ARROW2} '
WARN = '!'
CHECK = '✓'
FAIL = '×'
UNCERTAIN = '~'
FROM = ' '  # '⠖'
TO = '⠒'  # '⠓'
CURSOR_UP_ONE = '\x1b[1A'
ERASE_LINE = '\x1b[2K'