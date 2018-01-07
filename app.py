#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import unicode_literals

import os, unicodedata, itertools
import config
from film import Film
from utils import *

from itertools import islice

import tmdbsimple as tmdb
if config.TMDb['enabled']:
    tmdb.API_KEY = config.TMDb['key']

import argparse, requests, plexapi

# Arg parser construction
parser = argparse.ArgumentParser(description = 'A film renaming script')
parser.add_argument('--silent', action="store_true", default=False) # Do not send notifications or update services
parser.add_argument('--test', action="store_true", default=False) # Run in non-destructive test mode only; do not rename or move files
parser.add_argument('--debug', action="store_true", default=False) # Run in debug mode with extra console output
parser.add_argument('--strict', action="store", default=True, dest="strict") # Disable strict mode
parser.add_argument('--source', action="store", default=None, dest="source", type=str) # Temporarily overwrite the configured source dir
parser.add_argument('--limit', action="store", default=0, dest="limit", type=int) # Limit the number of files to rename and move
parser.add_argument('--pop', action="store", default=None, dest="pop", type=int) # Limit the number of files to rename and move
args = parser.parse_args()
if args.test: config.testMode=args.test
if args.debug: config.debugMode=args.debug
if args.strict == 'no': config.strictMode=False
if args.source: config.sourceDirs = [args.source]
if args.limit: config.limit=args.limit
if args.pop: config.minPopularity=args.pop
config.silentMode = True if args.silent else False

def main():

    count = 0

    o.start()
    o.testMode()
 
    # Enumerate destination directory for checking duplicates
    existingFilms = [Film(os.path.join(config.destDir, file)) for file in [unicodedata.normalize('NFC', file) for file in os.listdir(config.destDir)]]

    # Search

    # TODO add ability to skip certain files

    for searchDir in config.sourceDirs:

        # Clean trailing slashes
        searchDir = searchDir.rstrip(fs.SLASH) + fs.SLASH
        destDirRoot = config.destDir.rstrip(fs.SLASH) + fs.SLASH

        for d in (d for d in [searchDir, destDirRoot] if not os.path.exists(d)): 
            o.error("'{}' does not exist; check folder path in config.py".format(d))

        # Sort and filter the search dir, convert to normalized (NFC) for MacOS
        sortedDir = [unicodedata.normalize('NFC', file) for file in sorted(os.listdir(searchDir), key=lambda s: s.lower()) if file != '.DS_Store' and file != 'Thumbs.db']

        # Enumerate files in search dir(s), alphabetically, case insensitive
        films = [Film(os.path.join(searchDir, file)) for file in sortedDir]
        
        for film in islice(films, config.limit if config.limit > 0 else None):

            o.logFilm(film)

            if film.hasIgnoredSubstrings:
                o.skip(film, '(ignored string)')
                continue      

            if film.isFile and not film.isAllowedExtension:
                o.skip(film, '(not a film)')
                continue      

            if film.isTVShow:
                o.skip(film, '(TV show)')
                continue     

            if film.title is None:
                o.skip(film, '(unknown title)')
                continue      

            if film.isDir and film.year is None:
                o.skip(film, '(probably not a film)')
                continue

            if film.size < config.minSizeInMiB * 1024 * 1024 and film.isFilmFile:
                o.skip(film, '({} is too small)'.format(stringutils.prettySize(film.size)))
                continue

            # Search TMDb for film (if enabled)
            o.debug(' ')
            film.searchTMDb()

            if film.year is None or (config.TMDb['enabled'] and film.id is None):
                # Lookup failed, or is disabled and has no year
                o.skip(film, '(unable to identify)')
                continue
            else:
                # Lookup succeeded
                o.filmDetails(film)

            # Determine the full directory the file will be moved to

            destDir = os.path.join(destDirRoot, film.newFilename if config.useFolders else None)

            # TODO: Add console prompts to accept and cancel, and an ability to retry searching


            # If it's a file, check to make sure it's one we want
            if film.isFile and fs.hasValidExt(film.sourcePath):

                # Rename the source file
                fs.rename(film.sourcePath, film.newFilenameWithExt)
                o.interesting('⌥', film.newFilenameWithExt)

                # src won't be updated if we're running in test mode; use original path if required
                src = os.path.join(searchDir, film.newFilenameWithExt) if not config.testMode else film.sourcePath
                dst = os.path.join(destDir, film.newFilenameWithExt)

                # TODO Figure out how to determine handle multiple editions stored in the same folder

                # Check for duplicates and abort
                if len(fs.findDuplicates(film, destDir, existingFilms)) > 0:
                    continue
                else:
                    
                    # Create destination folder(s) if they don't exist
                    fs.recursiveCreateDir(destDir)                

                    o.info('Moving to {}'.format(dst))
                    # Move the file
                    if fs.safeMove(src, dst):
                        count = count + 1
                    film.sourcePath = dst
                        
            # Or if it's a directory, clean it up
            elif film.isDir:
                deletedFiles = 0

                # Check for valid file types inside this dir; if none, skip
                validFiles = fs.validFiles(film.sourcePath)
                if len(validFiles) == 0:
                    o.warn('No valid files found in this folder')
                    continue

                # Check for duplicates and abort
                if len(fs.findDuplicates(film, destDir, existingFilms)) > 0:
                    continue    

                # Create destination folder(s) if they don't exist
                fs.recursiveCreateDir(destDir)

                # Enumerate what's left and move
                for file in validFiles:

                    # Generate new filename based on file's ext
                    newFilename = '{}{}'.format(film.newFilename, os.path.splitext(file)[1])

                    # Rename the file
                    fs.rename(file, newFilename)
                    o.interesting('⌥', newFilename)

                    # Generate a new source path based on the new filename
                    src = os.path.join(os.path.dirname(file), newFilename)
                    dst = os.path.join(destDir, newFilename)

                    o.info('Moving to {}'.format(dst))

                    # Move the file
                    if fs.safeMove(src, dst):
                        count = count + 1

                # Recursively delete unwanted files and update the count
                deletedFiles = fs.recursiveRemoveUnwantedFiles(film.sourcePath, deletedFiles)

                # TODO Fix this so that renamed files size are calculated

                # When all copying is done, update the film's sourcePath    
                film.sourcePath = destDir

                # Print results of cleaning
                if config.cleanUnwantedFiles:
                    o.notice('Cleaned {} unwanted file{}'.format(deletedFiles, 's' if deletedFiles > 1 else ''))
                    
                # Clean up parent folder, if safe to do so and enabled
                # check that source folder is now empty and < 1 KB
                if config.cleanUpSource:
                    o.debug('Removing parent folder {}'.format(film.originalPath))
                    # Ensure the original folder is empty before we remove it, or assume we did (if in test mode)
                    if (fs.size(film.originalPath) < 1000 and fs.countFilesInDir(film.originalPath) == 0) or config.testMode:
                        o.notice('Removing parent folder')
                        fs.recursiveDeleteDir(film.originalPath)
                    else:
                        o.warn('Could not remove parent folder because it is not empty')

    plex.notify()
    o.end(count)

if __name__ == "__main__":
    main()