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

"""TMDb search handler for Fylm.

This module performs searches and handles results from TMDb.

    search: the main method exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *

import os
import re
import copy
import time

import tmdbsimple as tmdb

from fylmlib.config import config
from fylmlib.console import console
from fylmlib.log import log
import fylmlib.compare as compare
import fylmlib.patterns as patterns
import fylmlib.formatter as formatter

if config.tmdb.enabled:
    tmdb.API_KEY = config.tmdb.key

class _TmdbResult:
    """An internal class for handling a TMDb search result object.

    An internal class that accepts a raw movie result from the
    TMDb API and translates it into a usable object.

    Attributes:
        search_string:      Search string that was used to retrieve this result
                            from the TMDb API.

        title:              Original title that was parsed from the file/folder.

        proposed_title:     The title of the TMDb search result, cleaned and
                            filesystem-friendly.

        search_year:        Year that was used to retrieve this result from the
                            TMDb API.

        year:               Original year that was parsed from the film's path.
                            Used primarily to compare the year we expect the film
                            was released, to what a TMDb result thinks it is.

        overview:           TMDb short description (overview) of the film.

        proposed_year:      The primary release year of the TMDb search result.

        tmdb_id:            The TMDb ID of the search result.

        popularity:         The TMDb popularity ranking of the search result.

        title_similarity:   Returns a decimal value between 0 and 1 representing
                            the similarity between parsed title and proposed title.

        year_deviation:     Absolute difference in years between the parsed year and
                            the proposed release year.

        is_potential_match: Performs a checking algorithm to determine if the search
                            result qualifies as a potential match.
    """
    def __init__(self, search_string, search_year, year=None, overview=None, title=None, proposed_title=None, proposed_year=None):
        self.search_string = search_string
        self.title = search_string
        self.proposed_title = proposed_title
        self.search_year = search_year
        self.year = search_year or year
        self.overview = None
        self.proposed_year = proposed_year
        self.tmdb_id = None
        self.popularity = 0

    def _map_raw_result(self, raw_result):
        """Map properties to this object from a raw JSON result.

        Maps all the properties in the TMDb API JSON result onto
        this instance.
        """
        for key, value in {
            "tmdb_id": raw_result['id'],
            "overview": raw_result['overview'],
            "popularity": raw_result['popularity'],
            "proposed_title": raw_result['title'],
            "proposed_year": int(raw_result['release_date'][:4]) if len(raw_result['release_date']) > 0 else 0
        }.items():
            setattr(self, key, value)

    @property
    def title_similarity(self):
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
        title_stripped = re.sub(patterns.strip_when_comparing, '', self.title).lower()
        proposed_title_stripped = re.sub(patterns.strip_when_comparing, '', self.proposed_title or '').lower()

        # Compare the strings and return the float value.
        return compare.string_similarity(title_stripped, proposed_title_stripped)

    @property
    def year_deviation(self):
        """Compare parsed year to TMDb release year.

        Returns:
            An absolute integer value representing the difference between
            the parsed year and the TMDb result's release year.
        """
        return compare.year_deviation(self.year, self.proposed_year)

    def is_potential_match(self, i):
        """Determine if a search result is a viable match candidate.

        config.yaml contains several options that govern search results.
        This method checks the result against these expectations to
        determine if the result is a potential match.

        Args:
            i: (int) count of the number of results that have been checked.
               For debugging purposes only.

        Returns:
            True if the TMDb result is a viable match candidate, else False.
        """

        # TODO: Remove this overbearing console debug in a future release
        # console.debug('   Comparing match {}: {}=={} / {}=={} ({} match, {} year diff)'.format(
        #     i,
        #     self.search_string,
        #     self.proposed_title,
        #     self.year,
        #     self.proposed_year,
        #     formatter.percent(self.title_similarity),
        #     self.year_deviation))

        # Check that the year deviation is acceptable and check that the
        # popularity is acceptable.
        if (self.year_deviation <= config.tmdb.max_year_diff
            and self.popularity >= config.tmdb.min_popularity):

            # Construct a string for outputting debug details.
            debug_quality_string = "({} / {} year diff)".format(formatter.percent(self.title_similarity), self.year_deviation)

            # Check to see if the first letter of both titles match, otherwise we
            # might get some false positives when searching for shorter titles. E.g.
            # "Once" would still match "At Once" if title_similarity is set to 0.5,
            # but we can rule it out because the first chars don't match.
            initial_chars_match = compare.initial_chars_match(
                formatter.strip_the(self.title),
                formatter.strip_the(self.proposed_title), 1)

            # If strict mode is enabled, we we need to validate that the title
            # similarity is acceptable and that the initial chars match.
            if (config.strict is True
                and self.title_similarity >= config.tmdb.min_title_similarity
                and initial_chars_match):
                console.debug("   Found a potential match in strict mode {}".format(debug_quality_string))
                return True

            # Otherwise, if strict mode is disabled, we don't need to validate
            # the title, and we return True anyway.
            elif config.strict is False:
                console.debug("   Found a potential match in no-strict mode {}".format(debug_quality_string))
                return True

        # If result does not match any other criteria, return False.
        return False

    def is_instant_match(self, i):
        """Determine if a search result is an instant match.

        This method checks the result against 'ideal' expectations to
        determine if the result qualifies as an instant match.

        Returns:
            True if the TMDb result is an instant match candidate, else False.
        """

        # Define a threshold for an 'ideal' title similarity. This value
        # is used to determine an instant match.
        ideal_title_similarity = 0.85

        # Check for an instant match: high title similarity, identical years,
        # and is at most the second result. This limitation is imposed
        # based on the theory that if by the second result is no good result is
        # found, we should check for all potential results and find the best.
        if (self.title_similarity >= ideal_title_similarity
            and self.year == self.proposed_year
            and i < 3):
            console.debug('Instant match: {} ({})'.format(self.proposed_title, self.proposed_year))
            return True
        else:
            return False

class _TmdbSearchConstructor:
    """An Internal class that constructs a set of search functions.

    Sometimes the first search result isn't the best match. This class
    constructs an array of search functions, to be executed in order, if
    an 'instant match' isn't found.

    Properties:
        searches: an array of search functions to be executed.
    """
    def __init__(self, title, year):
        """Generate an array of search functions.

        These searches will be executed in order, until either an instant
        match is found, or all search functions have executed. Once
        complete, each result will be mapped to a copy of the originating
        _TmdbResult object.

        The arguments passed here are used to construct modified search
        functions, and must remain intact in order to validate results.

        Args:
            title: (str, utf-8) original parsed title of the film.
            year: (int) original parsed year of the film.

        Returns:
            An array of functions and a _TmdbResult objects each result
            will be mapped to.
        """
        self.searches = [
            (lambda: _primary_year_search(title, year), _TmdbResult(title, year)),
            (lambda: _basic_search(title, year), _TmdbResult(title, year)),
            (lambda: _strip_articles_search(title, year), _TmdbResult(title, year)),
            (lambda: _recursive_rstrip_search(title, year), _TmdbResult(title, year)),
            (lambda: _basic_search(title, None), _TmdbResult(title, None, year)),
            (lambda: _recursive_rstrip_search(title, None), _TmdbResult(title, None, year))
        ]

def search(search_string, year=None):
    """Search TMDb for the specified string and year.

    This function proxies the search_string and year to functions
    constructed by a _TmdbSearchConstructor, then processes
    the results to determine if any of the TMDb results are
    potential (or instant) matches.

    Args:
        search_string: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        An array of function references.
    """

    # If the search string is empty or None, abort.
    if search_string is None or search_string == '':
        return

    # On macOS, we need to use a funky hack to replace / in a filename with :,
    # in order to output it correctly.
    # Credit: https://stackoverflow.com/a/34504896/1214800
    search_string = search_string.replace(r':', '-')

    console.debug('\nInit search set for "{}" {}'.format(search_string, year))

    # Initialize a array to store potential matches.
    potential_matches = []

    # Initialize a counter to track the number of results checked.
    count = 0

    # Iterate the search constructor's array of search functions.
    for search, tmdb_result in _TmdbSearchConstructor(search_string, year).searches:

        # Execute search() and iterate the raw JSON results.
        for raw_result in search():

            # First, increment the counter, because we've performed a search
            # and will inspect the result.
            count += 1

            # Create a copy of the origin _TmdbResult object, and map the raw
            # search result JSON to it.
            result = copy.deepcopy(tmdb_result)
            result._map_raw_result(raw_result)

            # Check for an instant match first.
            if result.is_instant_match(count):

                # If one is found, return it immediately, breaking the loop.
                return result

            # Otherwise, check for a potential match, and append it to the results
            # array.
            elif result.is_potential_match(count):

                # If a potential match is found, we save try the next search method.
                potential_matches.append(result)

    # If no instant match was found, sort the results so we can return the most
    #  likely match. Sort criteria:
    #   - prefer lowest year deviation first (0 is better than 1), then
    #   - prefer highest title similarity second (a 0.7 is better than a 0.4)
    sorted_results = sorted(potential_matches, key=lambda r: (r.year_deviation, -r.title_similarity))

    # If debugging, print the possible matches in the correct sort order to the
    # console.
    console.debug('   {} possible matches, sorted:'.format(len(sorted_results)))
    for r in sorted_results:
        console.debug("\t- '{}', '{}', {}, {} {}".format(r.proposed_title, r.proposed_year, r.title, r.title_similarity, r.year_deviation))

    # Return the first match in the sorted list, or None
    return next(iter(sorted_results or []), None)

def _primary_year_search(search_string, year=None):
    """Search TMDb for a string and a primary release year.

    Search TMDb for the specified search string and year, using the
    attributes 'query' and 'primary_release_year'.

    Args:
        search_string: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={search_string}&api_key=KEY&include_adult=true

    console.debug('Searching: "{}" / {} - primary release year'.format(search_string, year))

    # Build the search query and execute the search in the rate limit handler.
    return _search_handler(
        query=search_string, 
        primary_release_year=year,
        include_adult='true'
    )

def _basic_search(search_string, year=None):
    """Search TMDb for a string and a general year.

    Search TMDb for the specified search string and year, using the
    attributes 'query' and 'year'.

    Args:
        search_string: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?year={year}&query={search_string}&api_key=KEY&include_adult=true

    console.debug('Searching: "{}" / {} - basic year'.format(search_string, year))

    # Build the search query and execute the search in the rate limit handler.
    return _search_handler(
        query=search_string, 
        year=year,
        include_adult='true'
    )

def _strip_articles_search(search_string, year=None):
    """Strip 'the' and 'a' from the search string when searching TMDb.

    Strip 'the' or 'a' from the beginning of the search string
    (or ', the' from the end) in order to check for mistakenly
    added prefix/suffix articles. Search TMDb with the stripped
    string and year, using the attributes 'query' and 'year'.

    Args:
        search_string: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={search_string}&api_key=KEY&include_adult=true

    console.debug('Searching: "{}" / {} - strip articles, primary release year'.format(search_string, year))

    # Build the search query and execute the search in the rate limit handler.
    return _search_handler(
        query=re.sub(patterns.strip_articles_search, '', search_string), 
        primary_release_year=year, 
        include_adult='true'
    )

def _recursive_rstrip_search(search_string, year=None):
    """Recursively remove the last word when searching TMDb.

    Perform multiple searches, each time removing the last word
    from the search string until all words (except 'The') have
    been searched. For example, when we have:

        The.Matchstick.Heist.BluRay.1080p.Some-tag.Why.2008.Year.At.End.mkv

    Because the string is initally split on 'year', we're left with:

        The.Matchstick.Heist.BluRay.1080p.Some-tag.Why

    This won't find a result right away, but we can recursively search for:

        The.Matchstick.Heist.BluRay.1080p.Some-tag.Why
        The.Matchstick.Heist.BluRay.1080p.Some-tag
        The.Matchstick.Heist.BluRay.1080p
        The.Matchstick.Heist.BluRay
        The.Matchstick.Heist

    ...and then we have a match.

    Args:
        search_string: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A (rather large) raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={search_string}&api_key=KEY&include_adult=true

    # Create an empty array to handle raw API results.
    raw_results = []

    # Strip articles here, so that by the end, we aren't searching for 'The'.
    search_string = re.sub(patterns.strip_articles_search, '', search_string)

    console.debug('Searching: "{}" / {} - recursively remove the last word of title'.format(search_string, year))

    # Iterate over each word in the search string.
    for i, word in enumerate(search_string.split()):

        # Each time the iterator (i) increases in value, we strip a word
        # from the end of the search string. Then we forward a new
        # search to the primary year search method and return, and append
        # the search results.
        raw_results += _primary_year_search(search_string.rsplit(' ', i)[0], year)

    # Return the raw results.
    return raw_results

def _search_handler(**kwargs):

    # Instantiate a TMDb search object.
    search = tmdb.Search()

    # Disable the log
    log.disable()
    while True:
        try:
            # Build the search query and execute the search.
            search.movie(**kwargs)
            break
        # Catch rate limiting errors
        except Exception as e:
            console.debug(e)
            raise e
            if re.search('^429', str(e)):
                time.sleep(5.0)
            else:
                break
        finally:
            # If Travis is running, delay so we don't
            # hit the rate limit.
            if os.environ.get('TRAVIS') is not None:
                time.sleep(0.5)

    # Re-enable the log                
    log.enable()
    return search.results