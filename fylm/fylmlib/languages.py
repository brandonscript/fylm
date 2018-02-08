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

"""Loads languages from a json file into a consumable format.

This module is used to load languages from a ISO-639-1 language.json 
map file.

    languages: the main variable exported by this module.

"""

from __future__ import unicode_literals, print_function

import os
import json

class _Languages:
    """An array of Language objects, loaded from language.json.
    """
    def __init__(self):
        try:
            return self.languages
        except AttributeError:
            pass

        # Load json from languages.json
        data = json.load(open(os.path.join(os.path.dirname(__file__), 'languages.json')))

        # Map raw language objects to Language class objects
        self.languages = sorted(map(lambda l: Language(l['code'], l['name']), data), key=lambda l: l.primary_name.lower())

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

languages = _Languages().languages

