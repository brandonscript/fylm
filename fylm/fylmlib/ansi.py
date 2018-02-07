# -*- coding = utf-8 -*-
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
        self.yellow = 220
        self.amber = 208
        self.olive = 106
        self.orange = 166
        self.purple = 18
        self.pink = 197
        self.gray = 243
        self.dark_gray = 238
        self.light_gray = 248
        self.white = 255

ansi = _AnsiColors()