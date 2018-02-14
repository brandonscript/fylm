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

"""Progress bar handling for long-running operations.

This module generates a progress bar from a percentage and width.

    console: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

from colors import color

from fylmlib.ansi import ansi

def progress_bar(percentage, width=50):
    """Generates a progress bar for writing to console.

    Args:
        percentage: (float) percent complete of long-running operation.
        width: (int) width of terminal/progress bar
    Returns:
        A compiled progress bar for outputting to console.
    """

    FULL_BLOCK = color('█', fg=ansi.pink)
    INCOMPLETE_BLOCK_GRAD = [color('░', fg=ansi.dark_gray), color('▒', fg=ansi.dark_gray), color('▓', fg=ansi.dark_gray)]

    assert(isinstance(percentage, float) or isinstance(percentage, int))
    assert(0. <= percentage <= 100.)
    # progress bar is block_widget separator perc_widget : ####### 30%
    max_perc_widget = '100%' # 100% is max
    separator = ' '
    blocks_widget_width = width - len(separator) - len(max_perc_widget)
    assert(blocks_widget_width >= 10) # not very meaningful if not
    perc_per_block = 100.0/blocks_widget_width

    # Epsilon is the sensitivity of rendering a gradient block.
    epsilon = 1e-6

    # Number of blocks that should be represented as complete.
    full_blocks = int((percentage + epsilon)/perc_per_block)

    # The rest are incomplete.
    empty_blocks = blocks_widget_width - full_blocks

    # Build blocks widget.
    blocks_widget = ([FULL_BLOCK] * full_blocks)
    blocks_widget.extend([INCOMPLETE_BLOCK_GRAD[0]] * empty_blocks)

    # Calculate remainder due to how granular our blocks are.
    remainder = percentage - full_blocks * perc_per_block
    
    # Epsilon needed for rounding errors (check would be != 0.)
    # based on reminder modify first empty block shading, depending 
    # on remainder.
    if remainder > epsilon:
        grad_index = int((len(INCOMPLETE_BLOCK_GRAD) * remainder)/perc_per_block)
        blocks_widget[full_blocks] = INCOMPLETE_BLOCK_GRAD[grad_index]

    # Build percentage widget
    str_perc = '%.0f' % percentage

    # Subtract 1 because the percentage sign is not included.
    perc_widget = '%s%%' % str_perc.ljust(len(max_perc_widget) - 3)

    # Generate progress bar
    progress_bar = '%s%s%s' % (''.join(blocks_widget), separator, perc_widget)

    # Return the progress bar as string.
    return ''.join(progress_bar)