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

"""Loads languages from a json file into a consumable format.

This module is used to load languages from a ISO-639-1 language.json
map file.

    languages: the main variable exported by this module.

"""

import json
from pathlib import Path

from lazy import lazy

class Languages:
    """An array of Language objects, loaded from language.json.
    """
    def __init__(self):
        pass

    class Language:
        """A language objects to handle raw language descriptors.

        Attributes:
            code:           ISO-639-1 code of the language.
            primary_name:   Primary written name of the language.
            names:          Written names of associated languages.
        """

        def __init__(self, code, names):
            self.code = code
            self.names = [n.strip() for n in names.split(',')]
            self.primary_name = self.names[0]

        def __repr__(self):
            return f'{self.primary_name} ({self.code})'

    @lazy
    def languages(self) -> ['Language']:

        # Load json from languages.json
        # TODO: Pathify
        data = json.load(open(Path(__file__).parent / 'languages.json'))

        # Map raw language objects to Language class objects
        return list(map(lambda l: self.Language(l['code'], l['name']), data))

    def load(self) -> ['Language']:
        return self.languages
