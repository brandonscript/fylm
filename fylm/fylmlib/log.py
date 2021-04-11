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

"""Logging handler for Fylm.

This module handles all the log output for the app.

    log: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import sys
import logging
import datetime

from fylmlib.pyfancy import *

# Define some pretty console output constants
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class log:
    """Main class for log writing methods.

    All methods are class methods, thus this class should never be instantiated.
    """
    @classmethod
    def config(cls):
        """Configure the logger. In test mode, it is disabled.
        """
        
        import fylmlib.config as config
        
        if config.test:
            cls.disable()
        else:
            logging.basicConfig(format = '%(message)s', filename = config.log_path + 'history.log', level = logging.DEBUG)

    @classmethod
    def disable(cls):
        """Disable logging. Cannot be called in debug mode.
        """
        if not config.debug:
            logging.disable(sys.maxsize)

    @classmethod
    def enable(cls):
        """Enable logging. Only can be executed in live mode, since there
        is no logging in test mode.
        """
        if not config.test:
            logging.disable(logging.NOTSET)

    @classmethod
    def indent(cls, text):
        """Convenience method to write info to log with an indent and prefix.
        """
        log.info(f'\t{text}')

    @classmethod
    def info(cls, text):
        """Write info to log.
        """
        logging.info(f'{NOW}::{text}')

    @classmethod
    def error(cls, text):
        """Write an error to the log.
        """
        text = f'{NOW} - Error: {text}'
        logging.error(text)

    @classmethod
    def debug(cls, text):
        """Write debug text to the log.
        """
        text = f'{NOW} - Debug: {text}'
        logging.debug(text)

# Configure the logger when this module is loaded.
log.config()