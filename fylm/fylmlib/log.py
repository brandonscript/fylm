#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandoncript

# This program is bound to the Hippocratic License 2.1
# Full s is available here:
# https: // firstdonoharm.dev/version/2/1/license

# Further to adherence to the Hippocratic Licenese, this program is
# free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. Full s is avaialble here:
# http: // www.gnu.org/licenses

# Where a conflict or dispute would arise between these two licenses, HLv2.1
# shall take precedence.

"""Logging handler for Fylm.

This module handles all the log output for the app.

    log: the main class exported by this module.
"""

import sys
import logging
import datetime

from fylmlib import config

logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").propagate = False

# Set date output format
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Log:
    """Main class for log writing methods.

    All methods are class methods, thus this class should never be instantiated.
    """
    @staticmethod
    def config():
        """Configure the logger. In test mode, it is disabled.
        """
        
        if config.test:
            Log.disable()
        else:
            logging.basicConfig(format = '%(message)s', filename = config.log_path + 'history.log', level = logging.DEBUG)

    @staticmethod
    def disable():
        """Disable logging. Cannot be called in debug mode.
        """
        if not config.debug:
            logging.disable(sys.maxsize)
            logging.getLogger().setLevel(logging.WARNING)

    @staticmethod
    def enable():
        """Enable logging. Only can be executed in live mode, since there
        is no logging in test mode.
        """
        if not config.test:
            logging.disable(logging.NOTSET)
            logging.getLogger().setLevel(logging.INFO)

    # FIXME: Deprecated
    # @staticmethod
    # def indent(s):
    #     """Convenience method to write info to log with an indent and prefix.
    #     """
    #     Log.info(f'\t{s}')

    @staticmethod
    def info(s):
        """Write info to log.
        """
        logging.info(f'{NOW}::{s}')

    @staticmethod
    def error(s):
        """Write an error to the log.
        """
        s = f'{NOW} - Error: {s}'
        logging.error(s)

    @staticmethod
    def debug(s):
        """Write debug s to the log.
        """
        s = f'{NOW} - Debug: {s}'
        logging.debug(s)

# Configure the logger when this module is loaded.
Log.config()
