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

import os

import pytest

from plexapi.server import PlexServer
from fylmlib.pushover import init, Client

import fylmlib.config as config
import fylmlib.notify as notify

@pytest.mark.skip()
class TestPlex:

    def test_plex(self):

        # Note: this test is disabled by default, because it requires a Plex server and 
        # credentials in order to pass. You can run it yourself by configuring config.yaml 
        # with your own Plex server details and removing the comment on `@pytest.mark.skip()`

        # Set up config
        config.test = False
        config.quiet = False
        assert(config.test is False)
        assert(config.quiet is False)
        assert(config.plex.enabled is True)
        assert(config.plex.baseurl == "http://127.0.0.1:32400")
        assert(config.plex.token == "YOUR_TOKEN_HERE")
        assert("Movies" in config.plex.sections)

        plex = PlexServer(baseurl=config.plex.baseurl, token=config.plex.token, timeout=10)

        for section in (plex.library.section(section) for section in config.plex.sections):
            section.update()

    @pytest.mark.xfail(raises=(OSError, IOError))
    def test_plex_fail(self):

        plex = PlexServer(baseurl="http://127.0.0.1:12701", token="BAD_TOKEN", timeout=2)
