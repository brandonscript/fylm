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

"""Config loader for Fylm runtime options

This module loads configuration options from config.yaml, and optionally
CLI argumants.

    config: an instance of the main class (_Config) exported by this module.
"""

from __future__ import unicode_literals

import argparse
import yaml
import os
import codecs
from yaml import Loader, SafeLoader

from dotmap import DotMap

def construct_yaml_str(self, node):
    """Hijack the yaml module loader to return unicode.

    Args:
        node: (unicode) A constructor string.
    Returns:
        yaml string constructor
    """

    # Override the default string handling function
    # to always return unicode objects.
    return self.construct_scalar(node)

# Add unicode yaml constructors.
Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)

class _Config:
    """Main class for handling app options.

    TODO: Convert this class to a singleton property that is only loaded once.
    """
    def __init__(self):
        """Load config.yaml and map CLI arguments, if applicable.
        """

        # Generate a working dir path to config. (This is required for running tests from a
        # different working dir).
        # TODO: Perhaps we can improve this fragile hack using __future__?
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

        # Load the config file and map it to a 'DotMap', a dot-notated dictionary.
        with codecs.open(config_path, encoding='utf-8') as yaml_config_file:
            self.config = DotMap(yaml.load(yaml_config_file.read()))

        # Initialize the CLI argument parser.
        parser = argparse.ArgumentParser(description = 'A delightful filing and renaming app for film lovers.')

        # -q, --quiet
        # This option will suppress notifications or updates to services like Plex.
        parser.add_argument(
            '-q',
            '--quiet',
            action="store_true",
            default=False,
            dest="quiet",
            help='Do not send notifications or update Plex')

        # -t, --test
        # This option will run the app in sandbox mode, whereby no changes will actually
        # be performed on the filesystem. Used primarily for checking and validating search
        # results before running a live operation.
        parser.add_argument(
            '-t',
            '--test',
            action="store_true",
            default=False,
            dest="test",
            help='Run in non-destructive test mode only (nothing is renamed, moved, or deleted)')

        # -d, --debug
        # This option will print (a lot) of additional information out to the console. Useful
        # when developing or debugging difficult titles/files.
        parser.add_argument(
            '-d',
            '--debug',
            action="store_true",
            default=False,
            dest="debug",
            help='Display extra debugging information in the console output')

        # -r, --rename
        # This option will rename films in place without moving or copying them.
        parser.add_argument(
            '-r',
            '--rename',
            action="store_true",
            default=False,
            dest="rename_only",
            help='Rename films in place without moving or copying them')

        # --no-strict
        # This option disables the intelligent string comparison algorithm that verifies titles
        # (and years) are a match. Use with caution; likely will result in false-positives.
        parser.add_argument(
            '--no-strict',
            action="store_false",
            default=True,
            dest="strict",
            help='Disable intelligent string comparison algorithm which ensure titles are a match')

        # -f, --force-lookup
        # This option will force the app to look up any file or folder in the search dirs (except
        # TV shows), even if they don't fit the naming criteria to be considered a film (e.g. have
        # a year and valid ext).
        parser.add_argument(
            '-f',
            '--force-lookup',
            action="store_true",
            default=False,
            dest="force_lookup",
            help='Assume that all files/folders (except TV shows) in source dir(s) are films, and look them all up')

        # --no-duplicates
        # This option disables duplicate checking.
        parser.add_argument(
            '--no-duplicates',
            action="store_false",
            default=True,
            dest="no_duplicates",
            help='Disable duplicate checking')

        # -o, --overwrite
        # This option will cause duplicate files to be forcibly overwritten. Use with EXTREME CAUTION,
        # because this could be very destructive. (suggest running in test mode first!).
        parser.add_argument(
            '-o',
            '--overwrite',
            action="store_true",
            default=False,
            dest="overwrite_duplicates",
            help=('Forcibly overwrite any file (or matching files inside a film folder) with the same name, '
                  'regardless of size difference) # Forcibly overwrite duplicate files regardless of size diff'))

        # --source
        # This option overrides the source dirs configured in config.yaml.
        parser.add_argument(
            '--source',
            action="store",
            default=None,
            dest="source_override",
            type=unicode,
            help='Override the configured source dir(s) (comma separate multiple folders)')

        # -l, --limit
        # This option limits the number of files/folders processed during a single operation.
        parser.add_argument(
            '-l',
            '--limit',
            action="store",
            default=0,
            dest="limit",
            type=int,
            help='Limit the number of files to rename and move in a single pass')

        # -p, --pop
        # This option overrides the minimum popularity rating that a film must be in order for
        # it to be considered a potential match. Set to 0 to disable (accept all results).
        parser.add_argument(
            '-p',
            '--pop',
            action="store",
            default=None,
            dest="min_popularity",
            type=float,
            help='Minimum popularity ranking on TMDb to consider a valid match')

        # Parse known args and discard any we don't know about.
        args, unknown = parser.parse_known_args()

        # Re-map arg values onto known options already loaded from config.yaml.
        if args.quiet is True: self.config.quiet = True
        if args.test is True: self.config.test = True
        if args.debug is True: self.config.debug = True
        if args.rename_only is True: self.config.rename_only = True
        if args.strict is False: self.config.strict = False
        if args.force_lookup is True: self.config.force_lookup = True
        if args.no_duplicates is False: self.config.check_for_duplicates = False
        if args.overwrite_duplicates is True: self.config.overwrite_duplicates = True
        if args.source_override: self.config.source_dirs = args.source_override.split(",")
        if args.limit: self.config.limit = args.limit
        if args.min_popularity is not None: self.config.min_popularity = args.min_popularity

    def __getattr__(self, name):
        """Override getter for _Config() to allow top-level DotMap retrieval.

        Args:
            name: (unicode) Key name for config property.
        Returns:
            Value for specified key
        """

        # Override the default string handling function
        # to always return unicode objects
        try:
            return self.config[name]
        except KeyError:
            # Previously this was thought to be a good idea - returning args, but it has proven
            # to return some bad data (empty DotMap objects)
            #   return getattr(self.args, name

            # Instead, just return None.
            return None

# Create a referenceable singleton for _Config()
config = _Config()