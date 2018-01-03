#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import logging, re
import tmdbsimple as tmdb
import config
from utils import *

if config.TMDb['enabled']:
    tmdb.API_KEY = config.TMDb['key']

def search(title, year=None, recur=True, ignoreYear=False):

    # Disable logging
    o.disableLogging()

    if title is None: return
    o.debug("Searching {} {}".format(title, (year if not ignoreYear else None)))

    # Search
    s = tmdb.Search()
    response = s.movie(query=title, primary_release_year=(year if not ignoreYear else None), include_adult='true')
    results = s.results

    # Re-enable logging
    o.enableLogging()

    # If no results, we have a few things to try
    # ... stripping 'the' or 'a' from the beginning (or ', the' from the end) of the title
    stripArticles = re.compile(r'(^(the|a)\s|, the$)', re.I)
    if len(results) == 0 and stripArticles.match(title):
        o.debug('0 results - strip the, a, ,the')
        return search(re.sub(stripArticles, '', title), year, recur, ignoreYear)

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
            proposedTitle = stringutils.ireplaceChars(config.restrictedChars, '', result['title'].encode('utf-8').strip())
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
                    "id": id
                }
            else:
                o.debug('{} failed validation, next result'.format(proposedTitle))
                # Try the entire search loop again wtihout year
                if ignoreYear is not False: return search(title, year, recur, True)

def checkMatch(i, title, year, proposedTitle, proposedYear, popularity):
    # Checks the title found from searching TMDb to see if it's a close enough match and a popular title

    # Strip non-letters, numbers, the, a, and, and & so we can compare the meat of the titles
    stripComparisonChars = re.compile(r'[\W\d]|\b(the|a|and|&)\b', re.I)

    origTitle = re.sub(stripComparisonChars, '', title).lower()
    proposedTitle = re.sub(stripComparisonChars, '', proposedTitle).lower()

    yearSimilarity = yearsDeviation(year, proposedYear)
    titleSimilarity = stringutils.similar(title, proposedTitle)

    o.debug("Comparing match {}: {}=={}, {}=={} (year diff: {}, popularity: {}, title similarity: {})".format(i, origTitle, proposedTitle, year, proposedYear, yearSimilarity, popularity, titleSimilarity))

    # If strictMode is disabled, we skip most of this
    if config.strictMode and titleSimilarity > config.minTitleSimilarity and (yearSimilarity <= config.maxYearDifference or popularity > 2):
        # If we get the titles and dates matching (within 1 year), or if we find a popular title, it's a match
        o.debug("Found a suitable match in strict mode")
        return True
    elif not config.strictMode and yearSimilarity <= config.maxYearDifference and popularity > 2:
        o.debug("Found a suitable match")
        return True
    else: 
        return False

def yearsDeviation(year, proposedYear):
    # Calculate the difference in release years; if year is not specified, we can only go by proposed year
    if proposedYear is None: return 0
    return abs(year - proposedYear) 