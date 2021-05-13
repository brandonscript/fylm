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
# import warnings
# warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

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
    def is_equal_quality(file, other):
        """Determine if a film is the same quality as another, 
        without comparing size.

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
        an identical duplicate, it must pass is_duplicate, is_equal_quality, and
        the file sizes must be equal.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            True if the files are identical, else False
        """

        if not is_equal_quality(file, other):
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
        
        if file.resolution == other.resolution:
            return ComparisonResult.EQUAL
        else:
            return (ComparisonResult.HIGHER 
                    # A lower number == higher resolution
                    if file.resolution.value < other.resolution.value 
                    else ComparisonResult.LOWER)    

    @staticmethod
    def media(file, other) -> ComparisonResult:
        """Compare two file medias to determine if one is better than the other.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            ComparisonResult: EQUAL, HIGHER, LOWER, or NOT_COMPARABLE
        """
        
        if file.media == other.media:
            return ComparisonResult.EQUAL
        else:
            return (ComparisonResult.HIGHER 
                    # A lower number == higher media
                    if file.media.value < other.media.value 
                    else ComparisonResult.LOWER)    
            
    @staticmethod
    def proper(file, other) -> ComparisonResult:
        """Compare two files to determine if one is proper vs. the other.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns:
            ComparisonResult: EQUAL, HIGHER, LOWER, or NOT_COMPARABLE
        """
        
        if file.is_proper == other.is_proper:
            return ComparisonResult.EQUAL
        else:
            return (ComparisonResult.HIGHER 
                    if file.is_proper and not other.is_proper
                    else ComparisonResult.LOWER)    

    @staticmethod
    def quality(file, other) -> (ComparisonResult, ComparisonReason):
        """Compare two file qualities to determine if one is better than the other.
        This method compares resolution, media, edition, proper, and HDR, but does 
        NOT compare file size.

        Args:
            file: (Film.File) the first file to compare.
            other: (Film.File) the second file to compare.
        Returns: 
            Tuple(ComparisonResult, ComparisonReason)
        """
        
        Result = ComparisonResult
        Reason = ComparisonReason
        
        rez = Compare.resolution(file, other)
        media = Compare.media(file, other)
        size = Compare.size(file, other)
        proper = Compare.proper(file, other)
        
        if Compare.title_similarity(file.title, other.title) < 0.9:
            Console.error(
                f"Cannot compare quality of different titles '{file.title}' and '{other.title}'")
            return (Result.NOT_COMPARABLE, Reason.NAME_MISMATCH)
        
        # Resolution
        if rez != Result.EQUAL:
            return (rez, Reason.RESOLUTION)

        if media != Result.EQUAL:
            return (media, Reason.MEDIA)
            
        # Edition
        if file.edition != other.edition and not config.duplicates.ignore_edition:
            return (Result.DIFFERENT, Reason.EDITION)
            
        # HDR
        if file.is_hdr != other.is_hdr:
            return (Result.DIFFERENT, Reason.HDR)

        # Proper
        if proper != Result.EQUAL:
            return (proper, Reason.PROPER)
            
        # Size
        if size == ComparisonResult.EQUAL:
            return (Result.EQUAL, ComparisonReason.IDENTICAL)
        else:
            return (size, Reason.SIZE)

        # At this point, we must assume that the files aren't comparable, but 
        # this is a last resort fallback and should never be reached.
        return (Result.NOT_COMPARABLE, Result.NOT_COMPARABLE)

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
