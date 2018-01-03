#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import config
from film import Film
from utils import *

import os
from itertools import islice

import argparse, requests, plexapi

# Arg parser construction
parser = argparse.ArgumentParser(description = 'A film renaming script')
parser.add_argument('--silent', action="store_true", default=False) # Do not send notifications or update services
parser.add_argument('--test', action="store_true", default=False) # Run in non-destructive test mode only; do not rename or move files
parser.add_argument('--debug', action="store_true", default=False) # Run in debug mode with extra console output
parser.add_argument('--strict', action="store", default=True, dest="strict") # Disable strict mode
parser.add_argument('--source', action="store", default=None, dest="source", type=str) # Temporarily overwrite the configured source dir
parser.add_argument('--limit', action="store", default=0, dest="limit", type=int) # Limit the number of files to rename and move
args = parser.parse_args()
if args.test: config.testMode=args.test
if args.debug: config.debugMode=args.debug
if args.strict == 'no': config.strictMode=False
if args.source: config.sourceDirs = [args.source]
if args.limit: config.limit=args.limit

o.start()
o.testMode()

for searchDir in config.sourceDirs:

    # Clean trailing slashes
    searchDir = searchDir.rstrip(fs.SLASH) + fs.SLASH
    destDirRoot = config.destDir.rstrip(fs.SLASH) + fs.SLASH

    for d in (d for d in [searchDir, destDirRoot] if not os.path.exists(d)): 
        o.logError("'{}' does not exist; check folder path in config.py".format(d))

    # Enumerate files in search dir(s), alphabetically, case insensitive
    sortedFileList = [Film(os.path.join(searchDir, file)) for file in sorted(os.listdir(searchDir), key=lambda s: s.lower())]

    # Clean known filesystem extras
    sortedFileList = [f for f in sortedFileList if f.originalFilename != '.DS_Store' and f.originalFilename != 'Thumbs']
    
    for film in islice(sortedFileList, config.limit if config.limit > 0 else None):

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

        if film.size < config.minSizeInMiB * 1024 * 1024 and film.isFilm:
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
            
            # Create destination folder(s) if they don't exist
            fs.recursiveCreateDir(destDir)

            # Rename the source file
            fs.rename(film.sourcePath, film.newFilenameWithExt)
            
            o.interesting('⌥', film.newFilenameWithExt)

            dst = os.path.join(destDir, film.newFilenameWithExt)
            src = os.path.join(searchDir, film.newFilenameWithExt)
            
            # Abort the job if a duplicate is found
            if os.path.exists(dst):
                o.warn('Aborting; duplicate file found ({})'.format(stringutils.sizeDiffString(src, dst)))
                continue
            else:
                o.info('Moving to {}'.format(dst))

                # Move the file
                fs.safeMove(src, dst)
                film.sourcePath = dst
                    
        # Or if it's a directory, clean it up
        elif film.isDir:
            deletedFiles = 0

            # Check for valid file types inside this dir; if none, skip
            validFiles = fs.validFiles(film.sourcePath)
            if len(validFiles) == 0:
                o.warn('No valid files found in this folder')
                continue

            # Create destination folder(s) if they don't exist
            fs.recursiveCreateDir(destDir)

            # Enumerate what's left and move
            for file in validFiles:

                # Generate new filename based on file's ext
                newFilename = '{}{}'.format(film.newFilename, os.path.splitext(file)[1])

                # Rename the file
                fs.rename(file, newFilename)

                # Generate a new source path based on the new filename
                src = os.path.join(os.path.dirname(file), newFilename)
                dst = os.path.join(destDir, newFilename)

                o.interesting('⌥', newFilename)

                # Abort the job if a duplicate is found
                if os.path.exists(dst):
                    o.warn('Aborting; duplicate file found ({})'.format(stringutils.sizeDiffString(src, dst)))
                    continue
                else:
                    o.info('Moving to {}'.format(dst))

                    # Move the file
                    fs.safeMove(src, dst)

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
                if fs.size(film.originalPath) < 1000 and fs.countFilesInDir(film.originalPath) == 0:
                    o.notice('Removing parent folder')
                    fs.recursiveDeleteDir(film.originalPath)
                else:
                    o.warn('Could not remove parent folder because it is not empty')