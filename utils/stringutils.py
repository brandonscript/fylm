#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import config, patterns
import re
import filesystem as fs
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

# Pretty format filesize in bytes
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
    sizeDiff = fs.size(dst) - fs.size(src)
    if sizeDiff < 0:
        return '{}{}'.format(prettySize(abs(sizeDiff)), ' smaller')
    elif sizeDiff > 0:
        return '{}{}'.format(prettySize(abs(sizeDiff)), ' bigger')
    else:
        return 'identical size'

def percent(num):
    return "{0:.0f}%".format(num * 100)

# String cleaning

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
        cleanedTitle = ireplace(word, '', cleanedTitle)

    # Set 'always lowercase' chars to lower, 'always uppercase' to upper, and a fix for ', The'
    cleanedTitle = titleCase(cleanedTitle, config.alwaysLowercase, config.alwaysUppercase).strip()

    # Remove extra whitespace
    cleanedTitle = stripExtraWhitespace(cleanedTitle)
    return cleanedTitle

def stripExtraWhitespace(str):
    return ' '.join(str.split()).strip()

def ireplace(find, repl, str):
    return re.compile(re.escape(find), re.I).sub(repl, str)

def ireplaceChars(chars, repl, str):
    return re.sub('[' + re.escape(''.join(chars)) + ']', repl, str, flags=re.I)

def titleCase(str, alwaysLowercase, alwaysUppercase):
    wordList = re.split(' ', str)
    final = [wordList[0].capitalize()]
    for word in wordList[1:]:
        final.append(word.lower() in alwaysLowercase and word.lower() or word.upper() in alwaysUppercase and word.upper() or word.capitalize())
    return ' '.join(final)