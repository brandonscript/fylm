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

"""String formatting tools for Fylm.

This module contains several string manipulation tools used for
string cleaning, improving comparison results, and outputting
human-readable information to the console/log.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import re
import copy

import fylmlib.config as config
import fylmlib.patterns as patterns

def build_new_filename(film):
    """Build a new file name from the specified renaming pattern.

    Using regular expressions and a { } templating syntax, construct
    a new filename by mapping available properties to config.rename_pattern.

    # Permitted rename pattern objects: {title}, {title-the}, {year}, {quality}, {edition}, {media}.
    # For using other characters with pattern objects, place them inside {} e.g. { - edition}.
    # For escaping templating characters, use \{ \}, e.g. {|{edition\}}.

    Returns:
        A new filename based on config.rename_pattern.
    """

    # Create a mutable copy of the original renaming pattern
    template = copy.copy(config.rename_pattern)

    # Generate a key-value map of available template properties,
    # each mapped to its associated film property.
    pattern_map = [
        ["title", film.title],
        ["title-the", film.title_the],
        ["edition", film.edition],
        ["year", film.year],
        ["quality", film.quality],
        ["media", film.media]
    ]

    # Enumerate the pattern map
    for key, value in pattern_map:

        # Generate a regular expression that suppports the keyword inside { }
        # and uses capture groups to preserve additional formatting characters.
        # The expression matches `{<anything>key<anything>}`, except where
        # { } are escaped with backslashes, i.e. \{ and \}.
        rx = re.compile(r'\{([^\{]*)' + key + r'([^\}]*)\}', re.I)

        # Check for a match
        match = re.search(rx, template)

        # Replace the template key in the pattern and strip the surrounding { }.
        # We add capture groups back in here to preserve extraneous chars that were
        # in the original match. This allows for conditional chars to be added to
        # the template string, so that `{ - edition}` will be replaced with
        # ` - Director's Cut` *only* if film.edition isn't blank.
        replacement = '{}{}{}'.format(match.groups()[0], value, match.groups()[1]) if match and match.groups() is not None else value

        # Update the template by replacing the original template match (e.g. `{title}`)
        # with the replacement (e.g. `Furngully The Last Rainforest`).
        template = re.sub(rx, replacement if value is not None else '', template)

    # Convert escaped template characters to un-escaped plain { }.
    template = template.replace('\{', '{')
    template = template.replace('\}', '}')

    # Strip illegal chars
    template = strip_illegal_chars(template)

    # Hack macOS titles that read / from the filesystem as :. If we don't do this,
    # we end up with the app trying to create folders for any title that contains
    # a /. Looking at you, Face/Off.
    template = template.replace(r'/', '-')

    # Strip extra whitespace from titles (e.g. `Dude   Where's My  Car` will become
    # `Dude Where's My Car`).
    return strip_extra_whitespace(template)

def pretty_size(size_in_bytes=0, measure=None):
    """Pretty format filesize/size_in_bytes into human-readable strings.

    Maps a byte count to KiB, MiB, GiB, KB, MB, or GB. By default,
    this measurement is automatically calculated depending on filesize,
    but can be overridden by passing `measure` key.

    Args:
        size_in_bytes (int): file size in bytes
        measure (str, utf-8): (optional) key value for the pretty_size_map to force
                           formatting to a specific measurement.
    Returns:
        A human-readable formatted filesize string.
    """

    # Force size_in_bytes to be an integer
    size_in_bytes = size_in_bytes or 0

    # Map out the math required to re-calculate bytes into human-readable formats.
    pretty_size_map = {

        # Do not round.
        "B": size_in_bytes,

        # Round to nearest whole number.
        "KB": round(size_in_bytes / 1000.0, 0),
        "KiB": round(size_in_bytes / 1024.0, 0),

        # Round to one decimal place.
        "MB": round(size_in_bytes / 1000.0 / 1000.0, 1),
        "MiB": round(size_in_bytes / 1024.0 / 1024.0, 1),

        # Round to two decimal places.
        "GB": round(size_in_bytes / 1000.0 / 1000.0 / 1000.0, 2),
        "GiB": round(size_in_bytes / 1024.0 / 1024.0 / 1024.0, 2)
    }

    # If measure was specified, format and return. This is usually used when calling
    # this function recursively, but can be called manually.
    if measure:
        return '{} {}'.format(pretty_size_map[measure], measure)
    elif pretty_size_map['GiB'] > 1:
        return pretty_size(size_in_bytes, 'GiB')
    elif pretty_size_map['MiB'] > 1:
        return pretty_size(size_in_bytes, 'MiB')
    elif pretty_size_map['KiB'] > 1:
        return pretty_size(size_in_bytes, 'KiB')
    else:
        return '{} {}'.format(size_in_bytes, 'B')

def pretty_size_diff(src, dst):
    """Pretty format filesize comparison.

    Compares two files/folders and prints the destination's difference in size in a
    human-readable manner, e.g. if src is 500 MB and dst is 300 MB, it will print
    '200 MB smaller'.

    Args:
        src (str, utf-8): path to source file/folder
        dst (str, utf-8): path to destination file/folder
    Returns:
        A human-readable formatted comparison string.
    """

    # Import size here to avoid circular import conflicts.
    from fylmlib.operations import size

    # Get the size of both source and destionation, then subtract the size of the
    # destination from the size of the source.
    size_diff = size(dst) - size(src)

    # If the difference is negative, the destination is smaller than the source.
    if size_diff < 0:
        return '{}{}'.format(pretty_size(abs(size_diff)), ' smaller')

    # If the difference is positive, the destination is larger than the source.
    elif size_diff > 0:
        return '{}{}'.format(pretty_size(abs(size_diff)), ' bigger')

    # Otherwise they must be the same size.
    else:
        return 'identical size'

def percent(d):
    """Pretty format a decimal as a percent string.

    Pretty format a decimal (ideally between 0 and 1) as a human-readable percent.

    Args:
        d (float): decimal number to convert to percentage.
    Returns:
        A human-readable formatted percentage.
    """
    return "{0:.0f}%".format(d * 100)

def replace_insensitive(find, repl, s):
    """Search and replace (case insensitive) within a string.

    Replace all occurrences of a substring in a string (case insensitive)
    with another string.

    Args:
        find (str, utf-8): substring to find in a string.
        repl (str, utf-8): string to replace it with.
        s (str, utf-8): original string to be searched
    Returns:
        A string with some substrings replaced.
    """
    return re.compile(re.escape(find), re.I).sub(repl, s)

def strip_the(s):
    """Remove `The` from the begining or `, The` from the end of a string.

    Search for `The` at the beginning of a string (case insensitive) and
    `, The` at the end (case insensitive) and remove both.

    Args:
        s (str, utf-8): original string to be cleaned.
    Returns:
        A string without `The` at the beginning or end.
    """
    return re.sub(r'(^the\W+|, the)', '', s, flags=re.I)

def strip_illegal_chars(s):
    """Remove all illegal characters from a title.

    Remove OS-restricted characters from filenames/paths so that the app
    doesn't attempt to write restricted chars to the filesystem.

    Args:
        s (str, utf-8): original string to be cleaned.
    Returns:
        A string without restricted chars.
    """

    # If the char separates a word, e.g. Face/Off, we need to preserve that
    # separation with a dash (-).
    s = re.sub(r'(?<=\S)[' + patterns.illegal_chars + r'](?=\S)', '-', s)

    # If it terminates another word, e.g. Mission: Impossible, we replace it
    # and any surrounding spaces with a single space instead. This will later
    # be corrected when strip_extra_whitespace is called.
    s = re.sub(r'\s?[' + patterns.illegal_chars + r']\s?', ' ', s)
    return s

def strip_extra_whitespace(s):
    """Replace repeating whitespace chars in a string with a single space.

    Search for repeating whitespace chars in a string and replace them with
    a single space.

    Args:
        s (str, utf-8): original string to be stripped of whitespace.
    Returns:
        A string without repeating whitespace chars.
    """
    return ' '.join(s.split()).strip()

def pluralize(s, c):
    """Pluralizes a string if count <> 1.

    Take a singular form of a string, and append an s to pluralize the word
    if the count is <> 1.

    TODO: Ensure this function accomodates English language exceptions.

    Args:
        s (str, utf-8): Singular form of a string to be pluralized.
        c (int): Count of item(s) to determine whether s should be pluralized.
    Returns:
        s, or {s}s if c <> 1
    """
    return s if c == 1 else f"{s}s"
