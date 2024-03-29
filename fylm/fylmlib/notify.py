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

"""Notification handler for Fylm.

This module handles all external services notifications.
Currently only Plex is supported, but Pushover is coming soon.
"""

from urllib.parse import urljoin
import os
import shutil
from pathlib import Path

from plexapi.server import PlexServer
from .pushover import init, Client
import requests

import fylmlib.config as config
from . import Log
from . import Console
from .console import Tinta


class Notify:

    @staticmethod
    def plex():
        """Plex notification handler.

        Notify Plex that it should check for updates.
        """

        # Check if Plex notifications are enabled, and that we're not running in
        # quiet or rename modes.
        if (config.plex.enabled is True
            and config.quiet is False
            and config.rename_only is False
                and config.test is False):

            # Disable the log so that HTTP ops aren't printed to the log.
            Log.disable()
            try:
                # Create a connection to the Plex server
                plex = PlexServer(baseurl=config.plex.baseurl,
                                  token=config.plex.token, timeout=10)
            except Exception as e:
                # If the connection fails, log the error and print a response to the console.
                Log.enable()
                Tinta().red(
                    f'Could not connect to Plex server on {config.plex.baseurl}').print()
                Console.error(e)
                return

            Tinta().white('\nUpdating plex...').print()

            # If the connection was successful, tell Plex to update specified sections if running
            # in live mode. No need to notify in test mode since there won't be any changes.
            if not config.test:
                for section in (plex.library.section(section) for section in config.plex.sections):
                    section.refresh()

            Tinta().green('Done ✓').print()

            # Re-enable logging when done.
            Log.enable()

    @staticmethod
    def pushover(film):
        """Pushover notification handler.

        Notify Pushover that an action has been performed.
        """

        # Check if Pushover notifications are enabled, and that we're not running in
        # quiet or rename modes.
        if (config.pushover.enabled is True
            and config.quiet is False
            and config.rename_only is False
                and config.test is False):

            attachment = None
            images_path = Path.cwd() / 'fylm/__images__'
            if not images_path.exists():
                images_path.mkdir(exist_ok=True, parents=True)

            img_path = ''
            if film.tmdb.poster_url:
                img = film.tmdb.poster_url.strip('/')
                url = urljoin('https://image.tmdb.org/t/p/w185/', img)
                img_path = images_path / img
                response = requests.get(url, stream=True)
                with open(img_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
                attachment = ("image.jpg", open(img_path, "rb"), "image/jpeg")

            # Application API token/key, which can be found by selecting your app
            # from https://pushover.net/apps and copying the key.
            init(config.pushover.app_token)

            # Initialize the Pushover client with your Pushover user key, which can
            # be found at https://pushover.net
            pushover = Client(config.pushover.user_key)

            message = ('. '.join(film.tmdb.overview.split('.  ')[
                       :2]) + '.'[:200] + '...') if len(film.tmdb.overview) > 200 else film.tmdb.overview

            pushover.send_message(
                message=f"{film.title} ({film.year})\n{message}",
                attachment=attachment,
                title='Fylm Added')

            try:
                img_path.unlink()
            except:
                pass
