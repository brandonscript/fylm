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

"""Cursor controls for console output.

This module adds show and hide cursor controls for console output.

    cursor: the main class exported by this module.
"""

import sys
import os

import fylmlib.config as config

if os.name == 'nt':
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = [("size", ctypes.c_int),
                    ("visible", ctypes.c_byte)]

class Cursor:
    """Main class for cursor controls.

    All methods are class methods, thus this class should never be instantiated.
    """

    @classmethod
    def hide(cls):
        """Hides the cursor in the console.
        """
        if not config.plaintext:
            try:
                if os.name == 'nt':
                    ci = _CursorInfo()
                    handle = ctypes.windll.kernel32.GetStdHandle(-11)
                    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                    ci.visible = False
                    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
                elif os.name == 'posix':
                    sys.stdout.write("\033[?25l")
                    sys.stdout.flush()
            except Exception:
                pass

    @classmethod
    def show(cls):
        """Shows the cursor in the console.
        """
        if not config.plaintext:
            try:
                if os.name == 'nt':
                    ci = _CursorInfo()
                    handle = ctypes.windll.kernel32.GetStdHandle(-11)
                    ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                    ci.visible = True
                    ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
                elif os.name == 'posix':
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
            except Exception:
                pass
