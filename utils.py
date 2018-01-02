#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import re, os, sys, logging, datetime, shutil, math
import config, patterns
import tmdbsimple as tmdb
from pyfancy import *

if config.TMDb['enabled']:
    tmdb.API_KEY = config.TMDb['key']

def safeMove(src, dst):
    # Only perform destructive changes if not running in test mode
    if not config.testMode:
        # If safeCopy is enabled, files will always be copied even if they're on a different partition
        if config.safeCopy: shutil.copy(src, dst)
        else: shutil.move(src, dst)

    # TODO check that src and destination file size match approximately, and catch IOError

def rename(src, newFilename):
    # Only perform destructive changes if not running in test mode
    if not config.testMode:
        shutil.move(src, os.path.join(os.path.dirname(src), newFilename))

def hasIgnoredStrings(name):
    return any(word.lower() in name.lower() for word in config.ignoreStrings)

def cleanTitle(film):
    cleanedTitle = film.originalFilename

    # Fix for titles that were previously changed to ', The'
    if re.search(r', the', cleanedTitle, re.I):
        cleanedTitle = '{}{}'.format('The ', re.sub(r', the', '', cleanedTitle, flags=re.I))

    # Use regex to strip unwanted chars
    cleanedTitle = re.sub(patterns.cleanTitle, ' ', cleanedTitle)

    # Strip proper title by splitting on year (most common practice)
    cleanedTitle = cleanedTitle.split(str(film.year))[0]
    
    # Strip unwanted strings from title
    for word in config.stripStrings + ['480p', '720p', '1080p', '2160p']: 
        cleanedTitle = replaceInsensitive(word, '', cleanedTitle)

    # Set 'always lowercase' chars to lower, 'always uppercase' to upper, and a fix for ', The'
    cleanedTitle = titleCase(cleanedTitle, config.alwaysLowercase, config.alwaysUppercase).strip()

    # Remove extra whitespace
    cleanedTitle = stripExtraWhitespace(cleanedTitle)
    return cleanedTitle

def cleanOriginalPath(film):
    if not config.testMode:
        try:
            shutil.rmtree(film.originalPath)
        # Catch resource busy error
        except OSError as e:
            if e.args[0] == 16:
                error('- Tried to remove {} but file is in use'.format(film.originalPath))

def stripExtraWhitespace(str):
    return ' '.join(str.split()).strip()

def searchTMDb(title, year=None):

    # Disable logging
    logging.disable(sys.maxint)

    if title is None: return
    debug("Searching {} {}".format(title, year))

    # Search
    search = tmdb.Search()
    response = search.movie(query=title, primary_release_year=year, include_adult='true')

    # Re-enable logging
    logging.disable(logging.NOTSET)

    # If no results, we have a few things to try
    # ... stripping 'the' or 'a' from the beginning (or ', the' from the end) of the title
    stripArticles = re.compile(r'(^(the|a)\s|, the$)', re.I)
    if len(search.results) == 0 and stripArticles.match(title):
        debug('Strip the, a, ,the')
        return searchTMDb(re.sub(stripArticles, '', title), year)

    # ... omitting 'year'
    elif len(search.results) == 0 and year is not None:
        debug('Omitting year and trying again')
        return searchTMDb(title, None)

    # ... recursively removing the last word of the title
    elif len(search.results) == 0 and len(title.split()) > 1:
        debug('Stripping the last word and trying again')
        return searchTMDb(title.rsplit(' ', 1)[0], year)

    # Yeah! There are some results. Let's check them to see if they're a match
    elif len(search.results) > 0:
        debug('{} results found'.format(len(search.results)))

        # Loop through results until we find one that is a match
        for result in search.results:
            proposedTitle = replaceCharsInsensitive(config.restrictedChars, '', result['title'].encode('utf-8').strip())
            proposedYear = int(result['release_date'][:4]) if result['release_date'] else None
            popularity = result['popularity']
            id = result['id']
            
            # Verify that the result is likely to be a match
            if checkTMDbMatch(title, year, proposedTitle, proposedYear, popularity):
                return {
                    "title": proposedTitle,
                    "year": proposedYear,
                    "id": id
                }
            else:
                debug('{} failed validation, next result'.format(proposedTitle))

def checkTMDbMatch(title, year, proposedTitle, proposedYear, popularity):
    # Checks the title found from searching TMDb to see if it's a close enough match and a popular title

    # If strictMode is disabled, we skip most of this

    if config.strictMode:
        # Strip non-letters, numbers, the, a, and, and & so we can compare the meat of the titles
        stripComparisonChars = re.compile(r'[\W\d]|\b(the|a|and|&)\b', re.I)

        origTitle = re.sub(stripComparisonChars, '', title).lower()
        proposedTitle = re.sub(stripComparisonChars, '', proposedTitle).lower()

        debug("Comparing match: {}=={}, {}=={}, (popularity: {})".format(origTitle, proposedTitle, year, proposedYear, popularity))

        titlesMatch = origTitle == proposedTitle # Do the titles match when comparing just word chars?
        yearsMatch = year == proposedYear # Do the dates match?

        # If we get the titles and dates matching, or if we find a popular title, it's a match
        return titlesMatch and yearsMatch or titlesMatch and popularity > 2
    else:
        
        debug("Comparing match: {}, {}=={}, (popularity: {})".format(proposedTitle, year, proposedYear, popularity))

        return year == proposedYear and popularity > 2

def replaceInsensitive(find, repl, str):
    return re.compile(re.escape(find), re.I).sub(repl, str)

def replaceCharsInsensitive(chars, repl, str):
    return re.sub('[' + re.escape(''.join(chars)) + ']', repl, str, flags=re.I)

def titleCase(str, alwaysLowercase, alwaysUppercase):
    wordList = re.split(' ', str)
    final = [wordList[0].capitalize()]
    for word in wordList[1:]:
        final.append(word.lower() in alwaysLowercase and word.lower() or word.upper() in alwaysUppercase and word.upper() or word.capitalize())
    return ' '.join(final)

def countFilesInDir(path):
    return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])

def size(path, mockBytes=None):
    if os.path.exists(path):
        bytes = mockBytes or os.path.getsize(path)
        if os.path.isdir(path):
            bytes = dirSize(path)
        return bytes
    elif not mockBytes:
        raise Exception('Could not determine file size at {}'.format(path))

def dirSize(path):
    totalSize = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            totalSize += (os.path.getsize(fp) if os.path.isfile(fp) else 0)
    return totalSize

def prettySize(bytes, measure=None):
    sizeMap = {
        "B": bytes,
        "KiB": round(bytes / 1024.0, 0),
        "MiB": round(bytes / 1024.0 / 1024.0, 1),
        "GiB": round(bytes / 1024.0 / 1024.0 / 1024.0, 2),
        "KB": round(bytes / 1000.0, 0),
        "MB": round(bytes / 1000.0 / 1000.0, 1),
        "GB": round(bytes / 1000.0 / 1000.0 / 1000.0, 2)
    }
    if measure: return '{} {}'.format(sizeMap[measure], measure)
    elif sizeMap['GiB'] > 1: return prettySize(bytes, 'GiB')
    elif sizeMap['MiB'] > 1: return prettySize(bytes, 'MiB')
    elif sizeMap['KiB'] > 1: return prettySize(bytes, 'KiB')
    else: return '{} {}'.format(bytes, 'B')

def sizeDiffString(src, dst):
    sizeDiff = size(dst) - size(src)
    if sizeDiff < 0:
        return '{}{}'.format(prettySize(abs(sizeDiff)), ' smaller')
    elif sizeDiff > 0:
        return '{}{}'.format(prettySize(abs(sizeDiff)), ' larger')
    else:
        return 'identical size'

def isValidExtension(file):
    return any([file.endswith(ext) for ext in config.videoFileExts + config.extraExts]) 

def printSkip(film, str):
    pyfancy().red(' ... {}'.format(film.originalFilename)).dark_gray(' {}'.format(str)).output()
    logDetails(str)

def printFilmDetails(film): 
    pyfancy().white(" ... {}{} ({})".format(film.originalFilename, film.ext or '', prettySize(film.size))).output()
    if config.TMDb['enabled']:
        if film.id is not None:
            pyfancy().white('\t→ ').green('✓ {} ({})'.format(film.title, film.year)).dark_gray().add(" [{}]".format(film.id)).output()
            logDetails('✓ {} ({}) [{}]'.format(film.title, film.year, film.id))
        else:
            pyfancy().white('\t→ ').red('𝗑 {} ({})'.format(film.title, film.year)).output()
            logDetails('𝗑 Not found')

logging.basicConfig(format='%(message)s', filename=config.logPath + 'history.log',level=logging.DEBUG)

def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def logFilm(film):
    log("{} ({})".format(film.sourcePath, prettySize(film.size)))

def logDetails(text):
    log('\t→ {}'.format(text))

def log(text):
    logging.info('{} ... {}'.format(now(), text))

def error(text):
    text = '{} - Error: {}'.format(now(), text)
    logging.error(text)
    raise Exception(text)

def debug(text):
    if config.debugMode: print(text)