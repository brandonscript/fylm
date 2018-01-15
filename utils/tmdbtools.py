#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import unicode_literals

import logging, re, sys
import tmdbsimple as tmdb
import config
from utils import *

if config.TMDb['enabled']:
    tmdb.API_KEY = config.TMDb['key']

def search(title, year=None, recur=True, ignoreYear=False):

    # Disable logging
    o.disableLogging()

    if title is None: return

    # Handle darwin / converting to :
    # On MacOS, we need to use a funky hack to replace / in a filename with :, in order to output it correctly
    # Credit: https://stackoverflow.com/a/34504896/1214800
    if sys.platform == 'darwin':
        title = title.replace(r':', '/')

    o.debug("Searching {} {}".format(title, (year if not ignoreYear else None)))

    # Search
    s = tmdb.Search()
    response = s.movie(query=title, primary_release_year=(year if ignoreYear is False else None), include_adult='true')
    results = s.results

    # Re-enable logging
    o.enableLogging()

    # If no results, we have a few things to try

    # ... stripping 'the' or 'a' from the beginning (or ', the' from the end) of the title
    if len(results) == 0 and patterns.stripArticles.match(title):
        o.debug('0 results - strip the, a, ,the')
        return search(re.sub(patterns.stripArticles, '', title), year, recur, ignoreYear)

    # ... recursively remove the last word of the title
    elif len(results) == 0 and len(title.split()) > 1 and recur is True:
        o.debug('0 results - recursively remove the last word of the title')
        checklist = []
        for i, word in enumerate(title.split()):
            r = search(title.rsplit(' ', i)[0], year, False, ignoreYear)
            if r is not None: return r
            checklist.append(r)
        return next((t for t in checklist if t is not None), None)

    # ... omitting 'year'
    elif len(results) == 0 and ignoreYear is False:
        o.debug('0 results - omit year and try again')
        return search(title, year, recur, True)    

    # Yeah! There are some results. Let's check them to see if they're a match
    elif len(results) > 0:
        o.debug('{} results found'.format(len(results)))

        # Loop through results until we find one that is a match, provided it has a release date
        for i, result in enumerate(results):
            proposedTitle =result['title']
            # Skip completely if result does not have a release date
            if result['release_date'] == '' or result['release_date'] is None:
                continue
            proposedYear = int(result['release_date'][:4])
            popularity = result['popularity']
            id = result['id']
            
            # Verify that the result is likely to be a match
            if checkMatch(i + 1, title, year, proposedTitle, proposedYear, popularity):
                return {
                    "title": proposedTitle,
                    "year": proposedYear,
                    "id": id,
                    "similarity": stringutils.similar(title, proposedTitle)
                }
            else:
                # Try the entire search loop again wtihout year
                if ignoreYear is False: return search(title, year, recur, True)

def checkMatch(i, origTitle, year, proposedTitle, proposedYear, popularity):
    # Checks the title found from searching TMDb to see if it's a close enough match and a popular title

    # Strip non-letters, numbers, the, a, and, and & so we can compare the meat of the titles

    stripComparisonChars = re.compile(r'([\W]|\b\d\b|^(the|a)\b|, the)', re.I)

    origTitle = re.sub(stripComparisonChars, '', origTitle).lower()
    proposedTitle = re.sub(stripComparisonChars, '', proposedTitle).lower()

    yearSimilarity = yearsDeviation(year, proposedYear)
    titleSimilarity = stringutils.similar(origTitle, proposedTitle) 

    o.debug("Comparing match {}: {}=={}, {}=={} (year diff: {}, popularity: {}, title similarity: {})".format(i, origTitle, proposedTitle, year, proposedYear, yearSimilarity, popularity, titleSimilarity))

    # Possibly a valid match based on year diff and popularity
    if yearSimilarity <= config.maxYearDifference and popularity >= config.minPopularity:
        # If strictMode is enabled we also need to check the title similarity
        if config.strictMode and titleSimilarity >= config.minTitleSimilarity:
            # If we get the titles and dates matching (within 1 year), or if we find a popular title, it's a match
            o.debug("Found a suitable match in strict mode")
            return True
        elif not config.strictMode:
            o.debug("Found a suitable match")
            return True
    else: 
        o.debug('{} failed validation, next result'.format(proposedTitle))
        return False

def yearsDeviation(year, proposedYear):
    # Calculate the difference in release years; if year is not specified, we can only go by proposed year
    if proposedYear is None or year is None: return 0
    return abs(year - proposedYear) 