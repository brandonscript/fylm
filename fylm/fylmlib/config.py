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

"""Config loader for Fylm runtime options

This module loads configuration options from config.yaml, and optionally
CLI argumants.

    config: an instance of the main class (Config) exported by this module.
"""

import argparse
import os
import sys
import codecs
from datetime import timedelta
import yaml
from yaml import Loader, SafeLoader
from pathlib import Path

from addict import Dict
import requests_cache

from fylmlib.enums import Resolution

# TODO: Deprecate?
def construct_yaml_str(self, node):
    """Hijack the yaml module loader to return unicode.

    Args:
        node: (str, utf-8) A constructor string.
    Returns:
        yaml string constructor
    """

    # Override the default string handling function
    # to always return unicode objects.
    return self.construct_scalar(node)

# Add unicode yaml constructors.
Loader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)
SafeLoader.add_constructor(u'tag:yaml.org,2002:str', construct_yaml_str)

class Config(object):
    """Main class for handling app options.
    """

    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(Config, cls).__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self):
        """Load config.yaml and map CLI arguments, if applicable.
        """

        if self.__initialized: 
            return
        self.__initialized = True

        # Generate a working dir path to config. (This is required for running tests from a
        # different working dir).
        # FIXME:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

        # Load the config file and map it to a 'Dict', a dot-notated dictionary.
        self._defaults = Dict({})
        with codecs.open(config_path, encoding='utf-8') as yaml_config_file:
            self._defaults.update(Dict(yaml.safe_load(
                yaml_config_file.read()), sequence_type=list))

        # Initialize the CLI argument parser.
        parser = argparse.ArgumentParser(description = 'A delightful filing and renaming app for film lovers.')

        # -q, --quiet
        # This option will suppress notifications or updates to services like Plex.
        parser.add_argument(
            '-q',
            '--quiet',
            action="store_true",
            default=self._defaults.quiet,
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
            default=self._defaults.test,
            dest="test",
            help='Run in non-destructive test mode only (nothing is renamed, moved, or deleted)')

        # -d, --debug
        # This option will print (a lot) of additional information out to the console. Useful
        # when developing or debugging difficult titles/files.
        parser.add_argument(
            '-d',
            '--debug',
            action="store_true",
            default=self._defaults.debug,
            dest="debug",
            help='Display extra debugging information in the console output')

        # --no-console
        # This option disables console output and stdout.
        parser.add_argument(
            '--no-console',
            action="store_true",
            default=self._defaults.no_console,
            dest="no_console",
            help='Disable console output and stdout')

        # --plaintext
        # This will output to the console without pretty formatting.
        parser.add_argument(
            '--plaintext',
            action="store_true",
            default=self._defaults.plaintext,
            dest="plaintext",
            help='Only output in the default console output color (no colored formatting)')

        # -r, --rename
        # This option will rename films in place without moving or copying them.
        parser.add_argument(
            '-r',
            '--rename',
            action="store_true",
            default=self._defaults.rename_only,
            dest="rename_only",
            help='Rename films in place without moving or copying them')

        # -c, --copy
        # This option will force copy behavior even when src and dst are on the same partition.
        parser.add_argument(
            '-c',
            '--copy',
            action="store_true",
            default=self._defaults.always_copy,
            dest="always_copy",
            help="Always copy instead of move files, even if they're on the same partition")

        # --hide-bad
        # This option will hide bad films from the console output.
        parser.add_argument(
            '--hide-bad',
            action="store_true",
            default=self._defaults.hide_bad,
            dest="hide_bad",
            help='Hide bad films from the console output')

        # -i, --interactive
        # This option enables prompts to confirm or correct TMDb matches.
        parser.add_argument(
            '-i',
            '--interactive',
            action="store_true",
            default=self._defaults.interactive,
            dest="interactive",
            help='Interactively prompt to confirm or correct TMDb matches or look up corrections')

        # --no-strict
        # This option disables the intelligent string comparison algorithm that verifies titles
        # (and years) are a match. Use with caution; likely will result in false-positives.
        parser.add_argument(
            '--no-strict',
            action="store_false",
            default=self._defaults.strict,
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
            default=self._defaults.force_lookup,
            dest="force_lookup",
            help='Assume that all files/folders (except TV shows) in source dir(s) are films, and look them all up')

        # --no-duplicates
        # This option disables duplicate checking.
        parser.add_argument(
            '--no-duplicates',
            action="store_false",
            default=self._defaults.duplicates.enabled,
            dest="duplicates_enabled",
            help='Disable duplicate checking')

        # -o, --overwrite
        # This option will cause duplicate files to be forcibly overwritten. Use with EXTREME CAUTION,
        # because this could be very destructive. (suggest running in test mode first!).
        parser.add_argument(
            '-o',
            '--overwrite',
            action="store_true",
            default=self._defaults.duplicates.force_overwrite,
            dest="force_overwrite",
            help=('Forcibly overwrite any file (or matching files inside a film folder) with the same name, \regardless of size difference)'))

        # --source
        # This option overrides the source dirs configured in config.yaml.
        parser.add_argument(
            '-s',
            '--source',
            action='store',
            nargs='*',
            default=self._defaults.source_dirs,
            dest="source_dirs",
            type=str,
            help='Override the configured source dir(s) (comma separate multiple folders)')

        # -l, --limit
        # This option limits the number of files/folders processed during a single operation.
        parser.add_argument(
            '-l',
            '--limit',
            action="store",
            default=self._defaults.limit,
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
            default=self._defaults.tmdb.min_popularity,
            dest="tmdb__min_popularity",
            type=float,
            help='Minimum popularity ranking on TMDb to consider a valid match')

        # Parse known args and discard any we don't know about.
        args, _ = parser.parse_known_args()

        # Re-map any deeply nested arguments
        args.tmdb = Dict({'min_popularity': args.tmdb__min_popularity})

        # Re-map arg values onto known options already loaded from config.yaml.
        self._defaults.update(Dict(vars(args)))

        # Supress console if no_console is true.  
        if self._defaults.no_console is True:
            sys.stdout = None

        # If using environment variables, overwrite defaults
        if os.environ.get('DEBUG') is not None:
            self._defaults.debug = True
        if os.environ.get('PLEX_TOKEN') is not None:
            self._defaults.plex.token = os.environ.get('PLEX_TOKEN')
        if os.environ.get('PLEX_URL') is not None:
            self._defaults.plex.baseurl = os.environ.get('PLEX_URL')
        if os.environ.get('PUSHOVER_APP_TOKEN') is not None:
            self._defaults.pushover.app_token = os.environ.get('PUSHOVER_APP_TOKEN')
        if os.environ.get('PUSHOVER_USER_KEY') is not None:
            self._defaults.pushover.user_key = os.environ.get('PUSHOVER_USER_KEY')
        if os.environ.get('TMDB_KEY') is not None:
            self._defaults.tmdb.key = os.environ.get('TMDB_KEY')
        
        # Map paths in source_dirs to Path and remove duplicates.
        self._defaults.source_dirs = list(set(map(Path, self._defaults.source_dirs)))
                                          
        # Map paths in destination_dirs to Path.
        for k, v in self._defaults.destination_dirs.items():
            self._defaults.destination_dirs[k]=Path(v)

        # Create placeholder var for mock inputs in interactive mode.
        self._defaults.mock_input = None

        # Set no_duplicates and force_overwrite nested properties in duplicates
        self._defaults.duplicates.enabled = self._defaults.duplicates_enabled
        del self._defaults.duplicates_enabled
        self._defaults.duplicates.force_overwrite = self._defaults.force_overwrite
        del self._defaults.force_overwrite

        # Set up cache.
        if self._defaults.cache is True:
            cache_ttl = self._defaults.cache_ttl or 1
            requests_cache.install_cache(str(Path('.').resolve() / '.cache.fylm'),
                                         expire_after=timedelta(hours=cache_ttl))
            requests_cache.remove_expired_responses()

        for k, v in self._defaults.items():
            setattr(self, k, Dict(v) if isinstance(v, dict) else v)
        del self._defaults
        
    def destination_dir(self, resolution: Resolution = Resolution.UNKNOWN) -> Path:
        """Returns the destination root path based on the file's resolution.

        Args:
            resolution (Resolution): Resolution of film or file to check.

        Returns:
            The root Path for the specified resolution, e.g. 
            /volumes/movies/HD or /volumes/movies/SD
        """
        return self.destination_dirs[resolution.key]
    
    def reload(self):
        """Reload config from config.yaml."""

        __instance = None
        self.__initialized = False
        self.__init__()

        sys.modules[__name__] = self

# Apply attributes to globals() so this can be imported using `import config`
sys.modules[__name__] = Config()
