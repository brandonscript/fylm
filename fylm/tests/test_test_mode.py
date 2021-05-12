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

import pytest

import fylmlib.config as config
from fylmlib import Find, App
import fylm
import conftest
from make import Make

# @pytest.mark.skip()
class TestConfig(object):
    """Tests operation impacting config options"""

    def test_config_test_mode(self):
        
        # Set test mode to true
        config.test = True
        assert(config.test is True)

        # Disable TMDb lookups for faster test
        config.tmdb.enabled = False
        assert(config.tmdb.enabled is False)
        
        Make.all_mock_files()

        before_new = Find.new()
        before_exs = Find.existing()
        
        # Execute
        moved = App.run()

        after_new = Find.new()
        after_exs = Find.existing()
        
        assert(len(before_exs) == 0 and before_exs == after_exs)
        
        config.rename_only = True
        assert(config.rename_only is True)
        
        moved = App.run()
        
        renamed_new = Find.new()
        renamed_exs = Find.existing()
        
        same = set(before_new).intersection(set(renamed_new))
        assert(len(same) == len(before_new))
        assert(len(renamed_exs) == 0)
