#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import config
import output as o
from plexapi.server import PlexServer
from pyfancy import *

def notify():
    if config.plex["enabled"] is True and config.silentMode is False:
        try:
            plex = PlexServer(baseurl=config.plex["baseurl"], token=config.plex["token"], timeout=10)
        except Exception as e:
            o.red('Could not connect to Plex server on {}'.format(config.plex["baseurl"]))
            o.error(e)
            return

        p = pyfancy().white('\nUpdating plex...')
        for section in (plex.library.section(section) for section in config.plex["sections"]):
            if not config.testMode:
                section.update()
        p.green(' Done ✓').output()
