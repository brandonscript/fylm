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

"""TMDb search handler for Fylm.

This module performs searches and handles results from TMDb.

    search: the main method exported by this module.
"""

import os
import re
import copy
import time
import warnings
import asyncio
import functools
from typing import Union
from datetime import datetime
from timeit import default_timer as timer
import requests

# FIXME: Delete?
# warnings.filterwarnings("ignore", message="Using slow pure-python SequenceMatcher. Install python-Levenshtein to remove this warning")

import tmdbsimple as tmdb
from rapidfuzz import fuzz
from lazy import lazy
from addict import Dict
from pathlib import Path
from itertools import groupby

import fylmlib.config as config
from fylmlib import Console
from fylmlib import Log
from fylmlib import Compare
from fylmlib import Format
from fylmlib import patterns
from fylmlib.constants import *

if config.tmdb.enabled:
    tmdb.API_KEY = config.tmdb.key
    
MAX_WORKERS = 50

# TODO: A shit ton of refactoring on TMDb
class TMDb:

    class Result:
        """An class for handling a TMDb search result object.

        An class that accepts a raw movie result from the
        TMDb API and translates it into a usable object.

        Attributes:
            query:              Search string that will be used to search the TMDb API.

            query_year:         Year that will be used to search the TMDb API.
                                
            src_title:          Original title that was parsed from the file/folder.                                

            src_year:           Original year that was parsed from the film's path.
                                Used primarily to compare the year we expect the film
                                was released, to what a TMDb result thinks it is.

            new_title:          The title of the TMDb search result.

            new_year:           The primary release year of the TMDb search result.

            id (int):           The TMDb ID of the search result.

            overview:           TMDb short description (overview) of the film.

            popularity:         The TMDb popularity ranking of the search result.

            vote_count:         The TMDb vote count ranking of the search result.

            title_similarity:   Float value between 0 and 1 representing the Levenshtein 
                                distance similarity between parsed title and proposed title.

            year_deviation:     Absolute difference in years between the parsed year and
                                the proposed release year.

            is_potential_match: Performs a checking heuristic to determine if the search
                                result qualifies as a potential match.
                                
            is_verified (bool): Set to True when the search result is retrieved from TMDb
                                
            ia_accepted (bool): Set to True once a TMDb result is verified in interactive mode.
            
        """
        
        def __init__(self, 
            src_title=None, 
            src_year=None, 
            raw_result=None):
            
            self.src_title = src_title
            self.src_year = src_year
            self.new_title = None
            self.new_year = None
            self.id = None
            self.overview = None
            self.popularity = 0
            self.vote_count = 0
            self.poster_url = None
            self.is_verified = False

            if raw_result is not None:
                self._merge(raw_result)
                
        def __repr__(self):
            return f"Result" + str(tuple([str(x) for x in [
                self.new_title or self.src_title,
                self.new_year or self.src_year,
                self.id] if x]))

        def __eq__(self, other):
            """Use __eq__ method to define duplicate search results"""
            return (self.new_title == other.new_title 
                and self.new_year == other.new_year
                and self.id == self.id)

        def __hash__(self):
            return hash(('new_title', self.new_title, 
                         'new_year', self.new_year,
                         'id', self.id))

        def _merge(self, raw):
            """Map properties to this object from a raw JSON result.

            Maps all the properties in the TMDb API JSON result onto
            this instance.

            Args:
                raw: (Result) raw TMDb search result object
            """
            raw = Dict(raw)
            
            self.id = int(raw.id)
            self.overview = raw.overview
            self.poster_url = raw.poster_path
            self.popularity = raw.popularity
            self.vote_count = raw.vote_count
            self.new_title = raw.title
            if raw.title and raw.release_date:
                # It's a valid API search result, so mark as valid
                self.is_verified = True
            try:
                self.new_year = datetime.strptime(
                    raw.release_date, "%Y-%m-%d").year
            except:
                self.new_year = 0

        @lazy
        def title_similarity(self) -> float:
            """Performs a Levenshtein distance comparison between src title and 
            new title.

            Returns:
                A decimal value between 0 and 1 representing the similarity between
                the two titles.
            """
            if not self.src_title:
                return 0
            return Compare.title_similarity(self.src_title, self.new_title)

        @lazy
        def year_deviation(self) -> int:
            """Compare parsed year to TMDb release year.

            Returns:
                An absolute integer value representing the difference between
                the parsed year and the TMDb result's release year.
            """
            if not self.src_title:
                return 1000
            return int(Compare.year_deviation(self.src_year, self.new_year))

        @lazy
        def is_instant_match(self) -> bool:
            """Determine if a search result is an instant match.

            Returns:
                True if the TMDb result is an instant match candidate, else False.
            """

            if not self.src_title:
                return False
            
            # Define a threshold for an 'ideal' title similarity. This value
            # is used to determine an instant match.
            ideal_title_similarity = 0.85

            # Check to see if the first letter of both titles match, otherwise we
            # might get some false positives when searching for shorter titles. E.g.
            # "Once" would still match "At Once" if title_similarity is set to 0.5,
            # but we can rule it out because the first chars don't match.
            initial_chars_match = Compare.initial_chars_match(
                Format.strip_the(self.src_title),
                Format.strip_the(self.new_title), 1)

            # Check for an instant match: high title similarity, year match within
            # max_year_diff (default 1 year off), and is at most the second result. 
            # This limitation is imposed based on the theory that if by the second 
            # result is no good result is found, we should check for all potential 
            # results and find the best.
            if (self.title_similarity >= ideal_title_similarity
                and self.year_deviation <= config.tmdb.max_year_diff
                and initial_chars_match):
                # Console.debug(f'Instant match: {self.new_title} ({self.new_year})')
                return True
            return False
            
        def update(self, film):
            """Updates a given film with the values of this result.

            Args:
                film (Film): Film to update
            """
            film.tmdb = self
            film.title = self.new_title
            film.year = self.new_year
            lazy.invalidate(film.main_file, 'new_name')
            
    class Search:
        
        def __init__(self, query: Union[str, int], year: int = None, id: int = None):
            """A search constructor

            Args:
                query (str): Original query string to search
                year (int, optional): Year to search. Defaults to None.
            """
            
            # On macOS, we need to use a funky hack to replace / in a filename with :,
            # in order to output it correctly.
            # Credit: https://stackoverflow.com/a/34504896/1214800
            self.query = query.replace(r':', '-') if type(query) is str else query
            if self.query == '':
                raise AttributeError('Search query cannot be an empty string.')
            self.year = year
            self.id = id
            self.results = []

        class parallel:
            """Performs asynchronous concurrent lookups from TMDb.
            
            Args:
                films ([Film]): *args list of films to search.
            """
            def __init__(self, *films):
                loop = asyncio.get_event_loop()
                tasks = asyncio.gather(*[
                    asyncio.ensure_future(self._worker(i, film))
                    for (i, film) in enumerate(films)
                ])
                loop.run_until_complete(tasks)

            async def _worker(self, i, film):
                # semaphore limits num of simultaneous calls
                async with asyncio.Semaphore(MAX_WORKERS):
                    # Console().yellow(f"{ARROW} Worker {i} started '{film.title}'").print()
                    await film.search_tmdb()
                    # Console().yellow(f"{ARROW} Worker {i} done '{film.title}' - {round(timer() - start)} second(s)").print()
                    return film
                
        class Q:
            """Search query dictionary handler
            
            Args:
                query: str or int
                id: int
                year
                primary_release_year
            """
            def __init__(self, query=None, primary_release_year=None, year=None, id=None):
                self.query = query
                self.primary_release_year = primary_release_year
                self.year = year
                self.id = id
                
            def __repr__(self):
                return ' '.join(f"Q('{self.query}') "\
                        f"{self.primary_release_year or ''} "\
                        f"{self.year or ''} "\
                        f"{self.id or ''}".split())
                
            def __eq__(self, other):
                """Use __eq__ method to define duplicate queries"""
                return (self.query == other.query
                        and self.primary_release_year == other.primary_release_year
                        and self.year == self.year
                        and self.id == self.id)

            def __hash__(self):
                return hash(('query', self.query,
                             'primary_release_year', self.primary_release_year,
                             'year', self.year,
                             'id', self.id))
                
            def dict(self):
                return self.__dict__

        async def do(self) -> ['TMDb.Result']:
            """Executes a series of searches until a suitable match is found.

            Returns:
                An ordered list of TMDb.Result objects.
            """
            
            Q = Search.Q

            # If querying by ID (an int), search immediately and return the result.
            if self.id or type(self.query) is int:
                # Console.debug(f'Searching ID={self.id or self.query}')
                return await self.dispatch_search(Q(id=self.id, query=self.query))
            
            # ID search
            # Example API call:
            #    https://api.themoviedb.org/3/movie/{tmdb_id}?api_key=KEY
            
            # Primary release year search
            # Example API call:
            #    https://api.themoviedb.org/3/search/movie?primary_release_year={year}&query={query}&api_key=KEY
            
            # Basic year search
            # Example API call:
            #    https://api.themoviedb.org/3/search/movie?year={year}&query={query}&api_key=KEY

            queries = []
            stripped = re.sub(patterns.STRIP_WHEN_SEARCHING, '', self.query)
                    
            queries = [
                Q(query=self.query, year=self.year),
                Q(query=stripped, year=self.year),
                Q(query=self.query, primary_release_year=self.year),
                Q(query=stripped, primary_release_year=self.year)
            ]

            # Try separating path parts
            parts = Path(self.query).parts
            if len(parts) > 1:
                [queries.append(Q(query=p, primary_release_year=self.year)) for p in parts]
                [queries.append(Q(query=p)) for p in parts]

            # Recursively remove the last word in the query
            for i, _ in enumerate(stripped.split()):
                q = stripped.rsplit(' ', i)[0]
                queries.append(Q(query=q, primary_release_year=self.year))
                queries.append(Q(query=q))

            # Get an ordered list of unique queries
            for i, q in enumerate(list(dict.fromkeys(queries))):
                r = await self.dispatch_search(q)
                for m in r:
                    if m.is_instant_match:
                        return [m]
                self.results.extend(r)
                
            # Sort, group/aggregate by ID, then sort by number of times the result appeared
            # in all searches
            results_sorted = sorted(self.results, key=lambda x: x.id)
            aggregate_results = [(r, len(list(results))) for r, results in groupby(results_sorted)]
            aggregate_results.sort(key=lambda x: x[1], reverse=True)
            
            # If no instant match was found, we need to figure out which are the most likely 
            # matches. Strip duplicate results and remove results that don't match the 
            # configured match threshold:
            filtered_results = list(filter(
                lambda x: 
                    (x[0].year_deviation == 0 
                        and (x[0].vote_count + x[0].popularity) >= 100
                        and x[0].title_similarity == config.tmdb.min_title_similarity / 1.4) or
                    (int(x[0].year_deviation) <= config.tmdb.max_year_diff 
                        and x[0].popularity >= config.tmdb.min_popularity
                        and x[0].title_similarity == config.tmdb.min_title_similarity) or
                    (x[0].year_deviation <= 2
                        and x[0].title_similarity >= 1.0) or
                    (x[0].year_deviation <= 1
                        and x[0].title_similarity >= 0.8) or
                    (x[0].year_deviation == 0
                        and x[0].title_similarity >= (config.tmdb.min_title_similarity / 1.5)), 
                aggregate_results # aggregate results is in a tuple: (Result, number_of_times_returned)
            ))
            
            # Sort the results by:
            #   - Sort by highest popularity rank first
            #   - Then prefer a matching title similarity first (a 0.7 is better than a 0.4)
            #   - Then prefer lowest year deviation (0 is better than 1)
            sorted_results = list(sorted(filtered_results, 
                key=lambda x: (-(x[0].vote_count + x[0].popularity), -x[0].title_similarity, x[0].year_deviation)
            ))

            # Return results (0 index) from the sorted and filtered tuple list
            self.results = [x[0] for x in sorted_results]
            # Console.debug(f"Slow '{self.query}' ({round(timer() - start)} second(s))")
            return self.results

        async def dispatch_search(self, q: 'Search.Q') -> ['Search.Result']:
            """TMDb lib search executor. Performs a TMDb search using the 
            specified query params.
            
            Args:
                Q (Search.Q): Dictionary of kwargs to pass to TMDb searcher
                
            Returns:
                A list of raw result dictionary objects mapped from TMDb JSON.
            """
            # Disable the log
            Log.disable()
            # Instantiate a TMDb search object.
            search = tmdb.Search()
            # Build the search query and execute the search.
            res = []
            query = q.__dict__
            query['include_adult'] = 'true'
            if q.id:
                try:
                    r = tmdb.Movies(q.id).info()
                    res = [r] if r else []
                except requests.exceptions.HTTPError:
                    res = []
            else:
                search.movie(**query)
                res = search.results
            # Re-enable the log
            Log.enable()
            return [Result(src_title=self.query,
                           src_year=self.year,
                           raw_result=r) for r in res]

Result = TMDb.Result
Search = TMDb.Search
