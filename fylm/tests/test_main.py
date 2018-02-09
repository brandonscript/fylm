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

from __future__ import unicode_literals, print_function, absolute_import

from fylmlib.config import config
import fylm
import conftest

# Enable this to turn on test mode in config
# config.test = True

# Set up the source and destination for test files.
config.source_dirs = [conftest.films_src_path]
config.destination_dirs = conftest.films_dst_paths

# Overwrite the app's pre-loaded config.
fylm.config = config

# Execute
fylm.main()

# assert 0