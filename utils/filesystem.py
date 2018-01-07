#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import unicode_literals

import os, shutil, glob
import config
import stringutils
import output as o

from itertools import ifilter

SLASH = "\\" if (os.name == "nt") else "/"

def safeMove(src, dst):

    o.debug("\nWill move '{}'".format(src))
    o.debug("To: '{}'\n".format(dst))

    # Only perform destructive changes if not running in test mode
    if not config.testMode:
        # If safeCopy is enabled, files will always be copied even if they're on a different partition
        try:
            if config.safeCopy: shutil.copy(src, dst)
            else: shutil.move(src, dst)
            return True
        except:
            return False

    # TODO check that src and destination file size match approximately, and catch IOError

def rename(src, newFilename):
    # Only perform destructive changes if not running in test mode
    if not config.testMode:
        shutil.move(src, os.path.join(os.path.dirname(src), newFilename))

def countFilesInDir(path):
    return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])

def remove(file):
    o.debug("Removing unwanted file {}".format(file))
    if not config.testMode:
        try:
            os.remove(file)
            return 1
        except Exception as e:
            o.warn('Unable to remove {}'.format(file))
            return 0
    else: return 1

# Delete files we don't want to keep, keeping track of the count
# Be careful not to accidentally delete something critical here... like /
def recursiveRemoveUnwantedFiles(path, count=0):
    if config.cleanUnwantedFiles and (not hasValidExt(path) or hasIgnoredSubstrings(os.path.basename(path))):
        if os.path.isfile(path):
            count = count + remove(path)
        else: 
            for f in (f for f in recursiveSearchDir(path) if not hasValidExt(f) or hasIgnoredSubstrings(f)):
                count = count + remove(f)
    return count


def recursiveCreateDir(dir):
    o.debug("Creating destination {}".format(dir))           
    if not config.testMode:
        if not os.path.exists(dir):
            try: 
                os.makedirs(dir)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    o.error('Unable to create {}'.format(dir))

def recursiveSearchDir(rootDir, include=None, ignore=None, func=None):
    include = tuple(include) if include else None
    ignore = tuple(ignore) if ignore else None
    results = []
    for root, dirs, files in os.walk(rootDir):
        for file in files:
            if func is not None and func(os.path.basename(file)):
                continue
            if (ignore is not None and file.endswith(ignore)):
                continue
            if include is None or file.endswith(include):
                results.append(os.path.join(root, file))
    return results

# Recursively delete dir, if less than maxSize in bytes (50 KB)
def recursiveDeleteDir(dir, maxSize=50000):
    if dirSize(dir) < 50000:
        o.debug("Recursively deleting {}".format(dir))

        # Built in some idiot checking just in case there's an attempt to delete / or one of the sourcePaths
        if dir == '/' or dir in config.sourceDirs:
            raise Exception("Somehow you tried to delete '{}' by calling recursiveCreateDir()... Don't do that!".format(dir)) 

        elif not config.testMode:
            try:
                shutil.rmtree(dir)
            # Catch resource busy error
            except OSError as e:
                if e.args[0] == 16:
                    o.error('Tried to remove {} but file is in use'.format(dir))
    else:
        o.debug("Will not delete {} because it is not empty".format(dir))


def size(path, mockBytes=None):
    """ Determine size of file or dir at path, or return mocked bytes """
    if mockBytes:
        return mockBytes
    elif os.path.exists(path):
        if os.path.isdir(path):
            return dirSize(path)
        else:
            return os.path.getsize(path)
        return bytes
    else:
        return None

def dirSize(path):
    totalSize = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            totalSize += (os.path.getsize(fp) if os.path.isfile(fp) else 0)
    return totalSize

# Checks if specified file has a valid extension, per config
def hasValidExt(filename):
    return any([filename.endswith(ext) for ext in config.videoFileExts + config.extraExts]) 

# Check if string has ignored strings
def hasIgnoredSubstrings(filename):
    return any(word.lower() in filename.lower() for word in config.ignoreStrings)

def findDuplicates(srcFilm, dst, existingFilms, ignoreEdition=False):

    if config.destDir in config.sourceDirs or not config.checkForDuplicates:
        o.debug('Ignoring duplicates because destDir and sourceDir are the same')
        return []

    from film import Film

    dstFilm = Film(dst)
   
    o.debug('Searching for duplicates of {} {}'.format(srcFilm.title, srcFilm.year))

    # Use fast ifilter to find duplicates
    duplicates = []

    for film in ifilter(lambda dstFilm: isDuplicate(srcFilm, dstFilm, ignoreEdition), existingFilms):
        duplicates.append(film)

    if len(duplicates) > 0:
        o.warn('Aborting; {} duplicate{} found:'.format(len(duplicates), 's' if len(duplicates) > 1 else ''))
        for d in duplicates:
            o.warn("  '{}' is {} ({})".format(d.newFilenameWithExt, stringutils.sizeDiffString(srcFilm.sourcePath, d.sourcePath), stringutils.prettySize(size(d.sourcePath))))

    o.debug('Found {} duplicates'.format(len(duplicates)))
    return duplicates

# Algorithm to determine if one film is a duplicate of another
def isDuplicate(srcFilm, dstFilm, ignoreEdition):
    # Strip restricted chars and compare lowercase (because we're not doing TMDb lookups on the dstFilm)
    srcTitle = stringutils.ireplaceChars(config.restrictedChars, '', srcFilm.title).lower()
    dstTitle = stringutils.ireplaceChars(config.restrictedChars, '', dstFilm.title).lower()

    # Strip edition from title if it wasn't removed
    if srcFilm.edition is not None:
        dstTitle = stringutils.ireplace(srcFilm.edition, '', dstTitle).rstrip()

    # Compare titles, years, and edition (default enabled)
    return srcTitle == dstTitle and srcFilm.year == dstFilm.year and (ignoreEdition == True or srcFilm.edition == dstFilm.edition)

# Check for valid file types inside this dir
def validFiles(path):
    validFiles = recursiveSearchDir(path, config.videoFileExts + config.extraExts, None, hasIgnoredSubstrings)
    for f in validFiles:
        o.debug("Found {}".format(f))
    return validFiles
