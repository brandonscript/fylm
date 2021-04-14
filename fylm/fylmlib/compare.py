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
        a = ' '.join(re.sub(patterns.strip_when_comparing, ' ', a).lower().split())
        b = ' '.join(re.sub(patterns.strip_when_comparing, ' ', b or '').lower().split())    
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
    def is_exact_duplicate(file, existing_file):
        """Determine if a film is an exact duplicate of another. To qualify as
        an exact duplicate, it must pass is_duplicate, as well as edition, quality,
        and media should match.

        Args:
            file: (Film.File) the first file to compare.
            existing_file: (Film.File) the second file to compare.
        Returns:
            True if the files are a match, else False
        """
        if not is_duplicate(file.parent_film, existing_file.parent_film):
            return False
        
        return quality(file, existing_file) == ComparisonResult.EQUAL

    @staticmethod
    def is_identical(file, existing_file):
        """Determine if a film is an identical copy of another. To qualify as
        an identical duplicate, it must pass is_duplicate, is_exact_duplicate, and
        the file sizes must be equal.

        Args:
            file: (Film.File) the first file to compare.
            existing_file: (Film.File) the second file to compare.
        Returns:
            True if the files are identical, else False
        """

        if not is_exact_duplicate(file, existing_file):
            return False

        return file.size == existing_file.size

    @staticmethod
    def resolution(file, existing_file) -> ComparisonResult:
        """Compare two file resolutions to determine if one is better than the other.

        Args:
            file: (Film.File) the first file to compare.
            existing_file: (Film.File) the second file to compare.
        Returns:
            ComparisonResult: EQUAL, HIGHER, LOWER, or NOT_COMPARABLE
        """

        resolution_hierarchy = ["2160p", "1080p", "720p", "576p", "480p"]

        # Get the index where the resolutions for both files occur in the heirarchy.
        # If the resolution isn't in the list, assume it's the lowest possible resolution.
        l = resolution_hierarchy.index(file.resolution) if file.resolution in resolution_hierarchy else 10
        r = resolution_hierarchy.index(existing_file.resolution) if existing_file.resolution in resolution_hierarchy else 10

        # Compare the indexes. A higher number means lower quality.
        if l == r:
            return ComparisonResult.EQUAL
        else:
            return ComparisonResult.HIGHER if l < r else ComparisonResult.LOWER        

    @staticmethod
    def quality(file, existing_file) -> ComparisonResult:
        """Compare two file qualities to determine if one is better than the other.
        This method compares resolution, media, edition, proper, and HDR, but does 
        NOT compare file size.

        Args:
            file: (Film.File) the first file to compare.
            existing_file: (Film.File) the second file to compare.
        Returns:
            ComparisonResult: EQUAL, HIGHER, LOWER, or NOT_COMPARABLE
        """

        # First we compare resolution; there's no point in comparing quality unless
        # resolutions match, because resolution is the first/principal quality differentiator.
        res = resolution(file, existing_file)
        if res != ComparisonResult.EQUAL:
            return res

        # If everything we're comparing is equal, we can stop here.
        if (file.media == existing_file.media
            and file.resolution == existing_file.resolution
            and file.edition == existing_file.edition
            and file.is_proper == existing_file.is_proper
            and file.is_hdr == existing_file.is_hdr):
            return ComparisonResult.EQUAL

        # If resolutions match, continue
        media_hierarchy = [Media.BLURAY, Media.WEBDL, Media.HDTV, Media.DVD, Media.SDTV]

        # Get the index where the media for both files occurs in the heirarchy.
        # If the media isn't in the list, assume it's the lowest possible media.
        l = media_hierarchy.index(file.media) if file.media in media_hierarchy else 10
        r = media_hierarchy.index(existing_file.media) if existing_file.media in media_hierarchy else 10

        # If one media is greater than the other, we can stop here
        if not l == r:
            return ComparisonResult.HIGHER if l < r else ComparisonResult.LOWER

        # If one is a proper and one is not, we can stop here
        if file.is_proper != existing_file.is_proper:
            return ComparisonResult.HIGHER if file.is_proper else ComparisonResult.LOWER

        # If one is an HDR and one is not, these aren't comparable; we can stop here
        if file.is_hdr != existing_file.is_hdr:
            return ComparisonResult.NOT_COMPARABLE

        # At this point, we must assume that the files aren't comparable, but 
        # this is a last resort fallback and should never be reached.
        return ComparisonResult.NOT_COMPARABLE

