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

"""Progress bar handling for long-running operations.

This module generates a progress bar from a percentage and width.

    console: the main class exported by this module.
"""

from colors import color
import fylmlib.config as config

class Progress:

    def bar(percentage, width=50):
        """Generates a progress bar for writing to console.

        Args:
            percentage: (float) percent complete of long-running operation.
            width: (int) width of terminal/progress bar
        Returns:
            A compiled progress bar for outputting to console.
        """

        from .console import Tinta

        if config.plaintext:
            FULL_BLOCK = "X"
            INCOMPLETE_BLOCK_GRAD = ["-", "-", "="]
        else:
            FULL_BLOCK = color('█', fg=Tinta.ansi.pink)
            INCOMPLETE_BLOCK_GRAD = [color('░', fg=Tinta.ansi.dark_gray),
                                     color('▒', fg=Tinta.ansi.dark_gray),
                                     color('▓', fg=Tinta.ansi.dark_gray)]

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
        str_perc = f'{percentage:.1f}'

        # Subtract 1 because the percentage sign is not included.
        perc_widget = f'{str_perc.ljust(len(max_perc_widget) - 3)}%'

        # Generate progress bar
        progress_bar = f"{''.join(blocks_widget)}{separator}{perc_widget}"

        # Return the progress bar as string.
        return ''.join(progress_bar)
