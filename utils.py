#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import re, os, sys, logging, datetime, shutil, math
import config, patterns
import tmdbsimple as tmdb
from pyfancy import *

if config.TMDb['enabled']:
    tmdb.API_KEY = config.TMDb['key']

history = {}

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

def lookup(film):
    film.searchTMDb()
    history[film.originalFilename] = film

def hasIgnoredStrings(name):
    return any(word.lower() in name.lower() for word in config.ignoreStrings)

def cleanTitle(film):
    cleanedTitle = film.originalFilename

    # Fix for titles that were previously changed to ', The'
    if re.search(r', the', cleanedTitle, re.I):
        cleanedTitle = '{}{}'.format('The ', re.sub(r', the', '', cleanedTitle, flags=re.I))

    # Strip proper title by splitting on year (most common practice)
    cleanedTitle = re.sub(patterns.cleanTitle, ' ', cleanedTitle.split(str(film.year))[0])

    # Strip unwanted strings from title
    for word in config.stripStrings + ['480p', '720p', '1080p', '2160p']: 
        cleanedTitle = replaceInsensitive(word, '', cleanedTitle)

    # Set 'always lowercase' chars to lower, 'always uppercase' to upper, and a fix for ', The'
    cleanedTitle = titleCase(cleanedTitle, config.alwaysLowercase, config.alwaysUppercase).strip()

    return cleanedTitle

def cleanOriginalPath(film):
    if not config.testMode:
        try:
            shutil.rmtree(film.originalPath)
        # Catch resource busy error
        except OSError as e:
            if e.args[0] == 16:
                error('- Tried to remove {} but file is in use'.format(film.originalPath))

def searchTMDb(title, year=None):
    logging.disable(sys.maxint)
    if title is None: return
    search = tmdb.Search()
    response = search.movie(query=title, primary_release_year=year, include_adult=True)
    logging.disable(logging.NOTSET)
    if len(search.results) > 0:
        bestMatch = search.results[0]
        return {
            "title": replaceCharsInsensitive(config.restrictedChars, '', bestMatch['title']),
            "year": int(bestMatch['release_date'][:4]),
            "id": bestMatch['id']
        }
    elif len(title.split()) > 1: # Retry, because there are more than one word
        retry = searchTMDb(title.rsplit(' ', 1)[0], year) # Strip the last word and try again
        if retry is not None:
            return retry
    else: 
        return None

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