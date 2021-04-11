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
import warnings
import asyncio
import functools
warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

import tmdbsimple as tmdb
from rapidfuzz import fuzz

import fylmlib.config as config
from fylmlib.console import console
from fylmlib.log import log
import fylmlib.compare as compare
import fylmlib.patterns as patterns
import fylmlib.formatter as formatter

if config.tmdb.enabled:
    tmdb.API_KEY = config.tmdb.key

MAX_WORKERS = 50  # Number of concurrent requests
_sem = asyncio.Semaphore(MAX_WORKERS)

class TmdbResult:
    """An internal class for handling a TMDb search result object.

    An internal class that accepts a raw movie result from the
    TMDb API and translates it into a usable object.

    Attributes:
        query:              Search string that was used to retrieve this result
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

        vote_count:         The TMDb vote count ranking of the search result.

        title_similarity:   Returns a decimal value between 0 and 1 representing
                            the similarity between parsed title and proposed title.

        year_deviation:     Absolute difference in years between the parsed year and
                            the proposed release year.

        is_potential_match: Performs a checking heuristic to determine if the search
                            result qualifies as a potential match.
    """
    def __init__(self, 
        query='', 
        search_year=None, 
        year=None, 
        title=None, 
        proposed_title=None, 
        proposed_year=None, 
        raw_result=None):

        self.query = query
        self.title = query
        self.proposed_title = proposed_title
        self.search_year = search_year
        self.year = search_year or year
        self.proposed_year = proposed_year
        self.popularity = 0
        self.vote_count = 0
        self.overview = None
        self.poster_path = None
        self.tmdb_id = None

        if raw_result is not None:
            self._merge(raw_result)

    def __eq__(self, other):
        """Use __eq__ method to define duplicate search results"""
        return (self.proposed_title == other.proposed_title 
            and self.proposed_year == other.proposed_year
            and self.tmdb_id == self.tmdb_id)

    def __hash__(self):
        return hash(('proposed_title', self.proposed_title, 
            'proposed_year', self.proposed_year,
            'tmdb_id', self.tmdb_id))

    def _merge(self, raw_result):
        """Map properties to this object from a raw JSON result.

        Maps all the properties in the TMDb API JSON result onto
        this instance.

        Args:
            raw_result: (TmdbResult) raw TMDb search result object
        """
        for key, value in {
            "tmdb_id": raw_result['id'],
            "overview": raw_result['overview'],
            "poster_path": raw_result['poster_path'].strip("/") if raw_result['poster_path'] else None,
            "popularity": raw_result['popularity'],
            "vote_count": raw_result['vote_count'],
            "proposed_title": raw_result['title'],
            "proposed_year": 0 if 'release_date' not in raw_result or len(raw_result['release_date']) == 0 else int(raw_result['release_date'][:4])
        }.items():
            setattr(self, key, value)

    @property
    def title_similarity(self):
        """Compare parsed title to TMDb title.

        Performs a comparison between parsed title and proposed title.

        Returns:
            A decimal value between 0 and 1 representing the similarity between
            the two titles.
        """
        return compare.title_similarity(self.title, self.proposed_title)

    @property
    def year_deviation(self) -> int:
        """Compare parsed year to TMDb release year.

        Returns:
            An absolute integer value representing the difference between
            the parsed year and the TMDb result's release year.
        """
        return int(compare.year_deviation(self.year, self.proposed_year))

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

        # Check to see if the first letter of both titles match, otherwise we
        # might get some false positives when searching for shorter titles. E.g.
        # "Once" would still match "At Once" if title_similarity is set to 0.5,
        # but we can rule it out because the first chars don't match.
        initial_chars_match = compare.initial_chars_match(
            formatter.strip_the(self.title),
            formatter.strip_the(self.proposed_title), 1)

        # Check for an instant match: high title similarity, year match within
        # max_year_diff (default 1 year off), and is at most the second result. 
        # This limitation is imposed based on the theory that if by the second 
        # result is no good result is found, we should check for all potential 
        # results and find the best.
        if (self.title_similarity >= ideal_title_similarity
            and self.year_deviation <= config.tmdb.max_year_diff
            and initial_chars_match
            and i < 3):
            debug(f'Instant match: {self.proposed_title} ({self.proposed_year})')
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
        TmdbResult object.

        The arguments passed here are used to construct modified search
        functions, and must remain intact in order to validate results.

        Args:
            title: (str, utf-8) original parsed title of the film.
            year: (int) original parsed year of the film.

        Returns:
            An array of functions and a TmdbResult objects each result
            will be mapped to.
        """
        self.searches = [
            (lambda: _primary_year_search(title, year), TmdbResult(title, year)),
            (lambda: _basic_search(title, year), TmdbResult(title, year)),
            (lambda: _strip_articles_search(title, year), TmdbResult(title, year)),
            (lambda: _basic_search(title, None), TmdbResult(title, None, year)),
            (lambda: _recursive_rstrip_search(title, year), TmdbResult(title, year)),
            (lambda: _recursive_rstrip_search(title, None), TmdbResult(title, None, year))
        ]


class dispatch_search_set():
    """A handler class for asynchronous concurrent lookups from TMDb.
    """

    def __init__(self, films):
        self.films = [film for film in films if not film.should_skip]

    def run(self):
        """Generate a set of tasks and dispatch asyncronously
        """
        loop = asyncio.get_event_loop()
        tasks = asyncio.gather(*[
            asyncio.ensure_future(self._worker(i, film))
            for (i, film) in enumerate(self.films)
        ])
        return loop.run_until_complete(tasks)

    async def _worker(self, i, film):
        async with _sem:  # semaphore limits num of simultaneous calls
            debug(f">> Async worker {i} started - '{film.title}'")
            await film.search_tmdb()
            debug(f">> Async worker {i} done - '{film.title}'")
            return film

async def search(query, year=None):
    """Search TMDb for the specified string and year.

    This function proxies the query and year to functions
    constructed by a _TmdbSearchConstructor, then processes
    the results to determine if any of the TMDb results are
    potential (or instant) matches.

    Args:
        query: (str, utf-8 OR int) string or TMDB ID to search for.
        year: (int) year to search for.

    Returns:
        An array of TmdbResult objects.
    """

    # If the search string is empty or None, abort.
    if query is None or query == '':
        return []

    # If querying by ID (an int), search immediately and return the result.
    if isinstance(query, int):
        r = await _id_search(query)
        debug(f'\nInitializing lookup by ID: {query}')
        return [TmdbResult(raw_result=r)] if r else []

    # On macOS, we need to use a funky hack to replace / in a filename with :,
    # in order to output it correctly.
    # Credit: https://stackoverflow.com/a/34504896/1214800
    query = query.replace(r':', '-')

    debug(f"\nInitializing search for '{query}' / {year}\n")

    # Initialize a array to store potential matches.
    potential_matches = []

    # Initialize a counter to track the number of results checked.
    count = 0

    # Iterate the search constructor's array of search functions.
    for search, tmdb_result in _TmdbSearchConstructor(query, year).searches:

        # Execute search() and iterate the raw JSON results.
        raw_results = await search()
        for r in raw_results:

            # First, increment the counter, because we've performed a search
            # and will inspect the result.
            count += 1

            # Create a copy of the origin TmdbResult object, and map the raw
            # search result JSON to it.
            result = copy.deepcopy(tmdb_result)
            result._merge(r)

            # Check for an instant match first.
            if result.is_instant_match(count):

                # If one is found, return it immediately (as a list of one), 
                # and break the loop.
                return [result]

            # Otherwise, check for a potential match, and append it to the results
            # array.
            else: 
                potential_matches.append(result)

    # If no instant match was found, we need to figure out which are the most likely matches

    # Debug helper to show all results after disqualified ones have been removed:
    # debug("\nAll matches found:")
    # for r in potential_matches:
    #     debug(f"   > {r.proposed_title}" \
    #                   f" ({r.proposed_year}), " \
    #                   f"   T_{r.title_similarity}, " \
    #                   f"Y_{r.year_deviation}, " \
    #                   f"P_{(r.vote_count + r.popularity)}")

    # Strip duplicate results and remove results that don't match the configured
    # match threshold:
    filtered_results = list(filter(
        lambda x: 
            (x.year_deviation == 0 
                and (x.vote_count + x.popularity) >= 100
                and x.title_similarity == config.tmdb.min_title_similarity / 1.4) or
            (int(x.year_deviation) <= config.tmdb.max_year_diff 
                and x.popularity >= config.tmdb.min_popularity
                and x.title_similarity == config.tmdb.min_title_similarity) or
            (x.year_deviation <= 2
                and x.title_similarity >= 1.0) or
            (x.year_deviation <= 1
                and x.title_similarity >= 0.8) or
            (x.year_deviation == 0
                and x.title_similarity >= (config.tmdb.min_title_similarity / 1.5)), 
        set(potential_matches)
    ))

    # Sort the results by:
    #   - Sort by highest popularity rank first
    #   - Then prefer a matching title similarity first (a 0.7 is better than a 0.4)
    #   - Then prefer lowest year deviation (0 is better than 1)
    sorted_results = list(sorted(filtered_results, 
        key=lambda x: (-(x.vote_count + x.popularity), -x.title_similarity, x.year_deviation)
    ))

    # Debug helper to show all results after disqualified ones have been removed:
    debug("\nFiltered matches found:")
    for r in sorted_results:
        debug(f"   > {r.proposed_title}" \
                      f" ({r.proposed_year}), " \
                      f"   T_{r.title_similarity}, " \
                      f"Y_{r.year_deviation}, " \
                      f"P_{(r.vote_count + r.popularity)}")

    # Return the sorted and filtered list
    return sorted_results

async def _id_search(tmdb_id):
    """Search TMDb by ID.

    Search TMDb for the specified ID.

    Args:
        tmdb_id: (int) TMDb ID to search for.
        year: (int) year to search for.

    Returns:
        A raw array of one TMDb result.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=KEY

    debug(f'Searching by ID: {tmdb_id}')

    # Build the search query and execute the search in the rate limit handler.
    return await do_search(tmdb_id=tmdb_id)

async def _primary_year_search(query, year=None):
    """Search TMDb for a string and a primary release year.

    Search TMDb for the specified search string and year, using the
    attributes 'query' and 'primary_release_year'.

    Args:
        query: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={query}&api_key=KEY&include_adult=true

    debug(f'Searching: "{query}" / {year} - primary release year')

    # Build the search query and execute the search in the rate limit handler.
    return await do_search(
        query=query, 
        primary_release_year=year,
        include_adult='true'
    )

async def _basic_search(query, year=None):
    """Search TMDb for a string and a general year.

    Search TMDb for the specified search string and year, using the
    attributes 'query' and 'year'.

    Args:
        query: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?year={year}&query={query}&api_key=KEY&include_adult=true

    debug(f'Searching: "{query}" / {year} - basic year')

    # Build the search query and execute the search in the rate limit handler.
    return await do_search(
        query=query, 
        year=year,
        include_adult='true'
    )

async def _strip_articles_search(query, year=None):
    """Strip 'the' and 'a' from the search string when searching TMDb.

    Strip 'the' or 'a' from the beginning of the search string
    (or ', the' from the end) in order to check for mistakenly
    added prefix/suffix articles. Search TMDb with the stripped
    string and year, using the attributes 'query' and 'year'.

    Args:
        query: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={query}&api_key=KEY&include_adult=true

    debug(f'Searching: "{query}" / {year} - strip articles, primary release year')

    # Build the search query and execute the search in the rate limit handler.
    return await do_search(
        query=re.sub(patterns.strip_articles_search, '', query), 
        primary_release_year=year, 
        include_adult='true'
    )

async def _recursive_rstrip_search(query, year=None):
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
        query: (str, utf-8) string to search for.
        year: (int) year to search for.

    Returns:
        A (rather large) raw array of TMDb results.
    """

    # Example API call:
    #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={query}&api_key=KEY&include_adult=true

    # Create an empty array to handle raw API results.
    raw_results = []

    # Strip articles here, so that by the end, we aren't searching for 'The'.
    query = re.sub(patterns.strip_articles_search, '', query)

    debug(f'Searching: "{query}" / {year} - recursively remove the last word of title')

    # Iterate over each word in the search string.
    for i, _ in enumerate(query.split()):

        # Each time the iterator (i) increases in value, we strip a word
        # from the end of the search string. Then we forward a new
        # search to the primary year search method and return, and append
        # the search results.
        raw_results += await _primary_year_search(query.rsplit(' ', i)[0], year)

    # Return the raw results.
    return raw_results

async def do_search(**kwargs):
    """Asynchronous caller for TMDb search.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(_searcher, **kwargs))

def _searcher(**kwargs):
    """Asynchronous passthrough wrapper for TMDb search.
    """
    # Disable the log
    log.disable()
    # Instantiate a TMDb search object.
    search = tmdb.Search()
    # Build the search query and execute the search.
    res = None
    if 'tmdb_id' in kwargs:
        res = tmdb.Movies(kwargs['tmdb_id']).info()
    else:
        search.movie(**kwargs)
        res = search.results
    # Re-enable the log
    log.enable()
    return res
