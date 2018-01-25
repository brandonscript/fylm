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

"""Singleton to count the number of successfully moved films.

This module must be loaded using `import counter` in order to preserve its
singleton nature. It is used to keep track of successful moves/renames.

    count: main property exported by this module.
"""

from __future__ import unicode_literals

# Counter property
count = 0

# Increment the counter property by the specified value (num)
def add(num):
    """Increment the count property by value (num)

    Args:
        num: (int) the number to add to the existing count.
    """    

    # Pull in the module's (global) count variable.
    global count

    # Increment the count property.
    count += num