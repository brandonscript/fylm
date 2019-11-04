# -*- coding: future_fstrings -*-
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
from builtins import *

import os

import pytest

from plexapi.server import PlexServer
from fylmlib.pushover import init, Client

import fylmlib.config as config
import fylmlib.notify as notify

@pytest.mark.skip()
class TestPlex(object):

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
