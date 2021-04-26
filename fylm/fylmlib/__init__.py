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

# Config and static functions
import fylmlib.config as config
import fylmlib.counter as counter
import fylmlib.constants as constants
import fylmlib.languages as languages
import fylmlib.patterns as patterns
import fylmlib.enums as enums

# Low-level library dependencies (init first)
from fylmlib.ansi import ansi
from fylmlib.log import Log
from fylmlib.formatter import Format
from fylmlib.progress import Progress
from fylmlib.console import Console
from fylmlib.parser import Parser
from fylmlib.cursor import Cursor
from fylmlib.operations import *

# Higher level functions (init after)
from fylmlib.compare import Compare
from fylmlib.tmdb import TMDb
from fylmlib.duplicates import Duplicates
from fylmlib.film import Film
from fylmlib.interactive import Interactive
from fylmlib.notify import Notify
from fylmlib.subtitle import Subtitle
from fylmlib.app import App