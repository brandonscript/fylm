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

"""Object comparison tools for Fylm.

This module provides tools which are used to compare different object types
during runtime.
"""

import re
import warnings
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

from rapidfuzz import fuzz

import fylmlib.config as config
from fylmlib import patterns
from fylmlib import Console
from fylmlib.enums import *

class Compare:
    
    @staticmethod
    def title_similarity(a, b):
        """Compare parsed title to TMDb title.

        Performs an intelligent string comparison between the original parsed
        title and the TMDb result.

        Returns:
            A decimal value between 0 and 1 representing the similarity between
            the two titles.
        """

        # Because we can't guarantee how similar parsed titles will be to search results,
        # (mixed case, missing symbols, or illegal OS chars), we strip unwanted chars from
        # both the original and TMDb title, and convert both to lowercase so we can get
        # a more accurate string comparison.
        a = ' '.join(re.sub(patterns.STRIP_WHEN_COMPARING, ' ', a).lower().split())
        b = ' '.join(re.sub(patterns.STRIP_WHEN_COMPARING, ' ', b or '').lower().split())    
        return fuzz.token_sort_ratio(a, b) / 100

    @staticmethod
    def year_deviation(year, proposed_year) -> int:
        """Calculate the difference between the expected year of a film to a
        counterpart release year retrieved from TMDb.

        Args:
            year: (int) the year parsed from the filename.
            proposed_year: (int) the proposed year retrieved from TMDb
        Returns:
            A deviation, in years, between the parsed year and the proposed year.
        """

        # If the original year was not specified,
        # we assume the resulting year is acceptable, and thus we return a 0 deviation.
        if proposed_year is None or year is None: return 0

        # Calculate the absolute difference in years and return the value.
        return int(abs(year - proposed_year))

    @staticmethod
    def initial_chars_match(a, b, chars):
        """Determine if the first n characters of two strings are identical (case
        insensitive).

        Args:
            a: (str, utf-8) the first string to compare.
            b: (str, utf-8) the second string to compare.
            chars: (int) the number of characters to compare
        Returns:
            True if the characters match (case insensitive), else false
        """
        return a.lower()[:chars] == b.lower()[:chars]

    # Heuristic to determine if one film is a duplicate of another
    @staticmethod
    def is_duplicate(film, existing_film):
        """Determine if a film is a duplicate of another. To qualify as
        a duplicate, it must match in title and year. Edition, quality,
        and media are ignored.

        Args:
            film: (Film) the first film to compare.
            existing_film: (Film) the second film to compare.
        Returns:
            True if the films are a match, else False
        """

        # If both films have already been looked up and have a matching TMDb IDs, 
        # we can assume they are a match.
        if (film.tmdb_id is not None 
            and existing_film.tmdb_id is not None 
            and film.tmdb_id == existing_film.tmdb_id):
            return True

        invalid_comparison_chars = re.compile(r'[^\w\d\s&.]', re.I)

        # Strip restricted chars from both films' titles, and compare lowercase (this
        # is important because we're not doing TMDb lookups on the existing film, and
        # we can't guarantee it was named with the correct case)
        title = re.sub(invalid_comparison_chars, '', formatter.strip_illegal_chars(film.title).lower())

        # Because existing_title is run through the Film init, which executes 
        # strip_from_title, we need to perform the same step on the original title.
        title = " ".join(re.sub(patterns.strip_from_title, ' ', title).strip().split())
        existing_title = " ".join(re.sub(invalid_comparison_chars, '', formatter.strip_illegal_chars(existing_film.title).lower()).strip().split())

        # Return True if title, year, and edition are equal, otherwise return False.
        # This assumes that you may want to keep two different editions of the same film,
        # but works well with identifying copies with a different resolution or quality.
        return (title == existing_title and film.year == existing_film.year)

    @staticmethod
    def is_exact_duplicate(file, other):
        """Determine if a film is an exact duplicate of another. To qualify as
        an exact duplicate, it must pass is_duplicate, as well as edition, quality,
        and media should match.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            True if the files are a match, else False
        """
        if not is_duplicate(file.parent_film, other.parent_film):
            return False
        
        return quality(file, other) == ComparisonResult.EQUAL

    @staticmethod
    def is_identical(file, other):
        """Determine if a film is an identical copy of another. To qualify as
        an identical duplicate, it must pass is_duplicate, is_exact_duplicate, and
        the file sizes must be equal.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            True if the files are identical, else False
        """

        if not is_exact_duplicate(file, other):
            return False

        return file.size == other.size

    @staticmethod
    def resolution(file, other) -> ComparisonResult:
        """Compare two file resolutions to determine if one is better than the other.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            ComparisonResult: EQUAL, HIGHER, LOWER, or NOT_COMPARABLE
        """

        resolution_hierarchy = ["2160p", "1080p", "720p", "576p", "480p"]

        # Get the index where the resolutions for both files occur in the heirarchy.
        # If the resolution isn't in the list, assume it's the lowest possible resolution.
        l = resolution_hierarchy.index(file.resolution) if file.resolution in resolution_hierarchy else 10
        r = resolution_hierarchy.index(other.resolution) if other.resolution in resolution_hierarchy else 10

        # Compare the indexes. A higher number means lower quality.
        if l == r:
            return ComparisonResult.EQUAL
        else:
            return ComparisonResult.HIGHER if l < r else ComparisonResult.LOWER        

    @staticmethod
    def quality(file, other) -> (ComparisonResult, ComparisonReason):
        """Compare two file qualities to determine if one is better than the other.
        This method compares resolution, media, edition, proper, and HDR, but does 
        NOT compare file size.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns: Tuple(ComparisonResult, ComparisonReason)
        """
        
        result = ComparisonResult
        reason = ComparisonReason
        
        res = Compare.resolution(file, other)
        size = Compare.size(file, other)
        
        if Compare.title_similarity(file.title, other.title) < 0.9:
            Console.error(
                f"Cannot compare quality of different titles '{file.title}' and '{other.title}'")
            return (result.NOT_COMPARABLE, result.NOT_COMPARABLE)
        
        # If editions don't match and not ignoring editions:
        if file.edition != other.edition and not config.duplicates.ignore_edition:
            return (result.NOT_COMPARABLE, reason.DIFFERENT_EDITIONS)
        
        # If everything we're comparing is equal, check for size.
        if (res == result.EQUAL
            and file.media == other.media
            and file.is_hdr == other.is_hdr
            and file.is_proper == other.is_proper):
                
                # Size
                if size == ComparisonResult.HIGHER:
                    return (result.EQUAL, ComparisonReason.BIGGER)
                elif size == ComparisonResult.LOWER:
                    return (result.EQUAL, ComparisonReason.SMALLER)
                return (result.EQUAL, reason.IDENTICAL)

        # Resolution
        if res == ComparisonResult.HIGHER:
            return (res, ComparisonReason.HIGHER_RESOLUTION)
        elif res == ComparisonResult.LOWER:
            return (res, ComparisonReason.LOWER_RESOLUTION)

        # Media; lower number = higher quality
        if file.media.value < other.media.value:
            return (result.HIGHER, reason.HIGHER_QUALITY)
        elif file.media.value > other.media.value:
            return (result.LOWER, reason.LOWER_QUALITY)
            
        # HDR
        if file.is_hdr != other.is_hdr:
            return (result.NOT_COMPARABLE, 
                    reason.HDR if file.is_hdr else reason.NOT_HDR)

        # Proper
        if file.is_proper != other.is_proper:
            return (result.HIGHER if file.is_proper else result.LOWER,
                    reason.PROPER if file.is_proper else reason.NOT_PROPER)

        # At this point, we must assume that the files aren't comparable, but 
        # this is a last resort fallback and should never be reached.
        return (result.NOT_COMPARABLE, result.NOT_COMPARABLE)

    @staticmethod
    def size(path, other) -> ComparisonResult:
        """Compare two files to determine if one is larger than the other.

        Args:
            file (FilmPath): First path to compare
            other (FilmPath): Second path to compare

        Returns:
            ComparisonResult
        """
        if not path.exists():
            Console().error(f"Could not compare size, '{path}' does not exist.")
            return ComparisonResult.NOT_COMPARABLE
        
        if not other.exists():
            Console().error(f"Could not compare size, '{other}' does not exist.")
            return ComparisonResult.NOT_COMPARABLE
        
        if path.size.value > (other.size.value or 0):
            return ComparisonResult.HIGHER
        elif path.size.value < (other.size.value or 0):
            return ComparisonResult.LOWER
        elif path.size.value == (other.size.value or 0):
            return ComparisonResult.EQUAL
        
        return ComparisonResult.NOT_COMPARABLE
