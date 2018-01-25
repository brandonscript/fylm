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

"""Singleton to hold a cached array of existing films.

This module must be loaded using `import existing_films` in order to preserve its
singleton/cache nature. It is used to check for duplicate films.

    cache: main property exported by this module.
"""

from __future__ import unicode_literals

from fylmlib.config import config

# Cached list of existing films
cache = []

def load():
    """Load existing films from the destination dir.
    """

    # Import file operations here to avoid circular conflicts
    import fylmlib.operations as ops

    # Pull in the module's (global) cache variable.
    global cache

    # Scan the destination directory for existing films, which sets
    # the existing_films cache. This is used for duplicate checking.
    cache = ops.dirops.get_existing_films(config.destination_dir)