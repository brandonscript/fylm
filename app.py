#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import config, utils

from film import Film
from pyfancy import *

import re, sys, os, shutil, urllib, time, datetime, subprocess, glob, errno
from itertools import islice

import argparse
import requests
import plexapi

if (os.name == "nt"):
    SLASH = "\\"
else:
    SLASH = "/"

timestamp = time.ctime()

# Arg parser construction
parser = argparse.ArgumentParser(description = 'A film renaming script')
parser.add_argument('--silent', action="store_true", default=False) # Do not send notifications or update services
parser.add_argument('--testMode', action="store_true", default=False) # Run in non-destructive test mode only; do not rename or move files
parser.add_argument('--limit', action="store", default=0, dest="limit", type=int) # Limit the number of files to rename and move
args = parser.parse_args()
if args.testMode: config.testMode=args.testMode
if args.limit: config.limit=args.limit

utils.log('\n{}{}{}'.format(('-'*50), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ('-'*50)))
print("Scanning subfolders and files in " + ', '.join(config.sourceDirs))
print("Please wait...\n")

if config.testMode:
    utils.log(' *** TEST MODE *** ')
    pyfancy().magenta('  *** TEST MODE ***\nNo changes will be made\n').output()

for searchDir in config.sourceDirs:

    # Clean trailing slashes
    searchDir = searchDir.rstrip(SLASH) + SLASH
    destDirRoot = config.destDir.rstrip(SLASH) + SLASH

    for d in (d for d in [searchDir, destDirRoot] if not os.path.exists(d)): 
        utils.error("'{}' does not exist; check folder path in config.py".format(d))

    # Enumerate files in search dir(s), alphabetically, case insensitive
    sortedFileList = [Film(os.path.join(searchDir, file)) for file in sorted(os.listdir(searchDir), key=lambda s: s.lower())]

    # Clean known filesystem extras
    sortedFileList = [f for f in sortedFileList if f.originalFilename != '.DS_Store' and f.originalFilename != 'Thumbs']
    
    for film in islice(sortedFileList, config.limit if config.limit > 0 else None):

        utils.logFilm(film)

        if film.hasIgnoredStrings:
            utils.printSkip(film, '(skip - ignored string)')
            continue      

        if film.isFile and not film.isAllowedExtension:
            utils.printSkip(film, '(skip - not a film)')
            continue      

        if film.isTVShow:
            utils.printSkip(film, '(skip - TV show)')
            continue     

        if film.title is None:
            utils.printSkip(film, '(skip - unknown title)')
            continue      

        if film.isDir and film.year is None:
            utils.printSkip(film, '(skip - probably not a film)')
            continue

        if film.size < config.minSizeInMiB * 1024 * 1024 and film.isFilm:
            utils.printSkip(film, '(skip - {} is too small)'.format(utils.prettySize(film.size)))
            continue

        # Search TMDb for film (if enabled)
        film.searchTMDb()

        if film.year is None or (config.TMDb['enabled'] and film.id is None):
            # Lookup failed, or is disabled and has no year
            utils.printSkip(film, '(skip - unable to identify)')
            continue
        else:
            # Lookup succeeded
            utils.printFilmDetails(film)

        # Determine the full directory the file will be moved to

        destDir = os.path.join(destDirRoot, film.newFilename if config.useFolders else None)

        # Create destination folder(s) if they don't exist
        if not config.testMode:
            if not os.path.exists(destDir):
                try: 
                    os.makedirs(destDir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        utils.error('Unable to create {}'.format(destDir))

        # If it's a file, check to make sure it's one we want
        if film.isFile and utils.isValidExtension(film.sourcePath):

            
            utils.rename(film.sourcePath, film.newFilenameWithExt)
            
            pyfancy().dark_gray('\t→ Renamed ').yellow(film.newFilenameWithExt).output()
            utils.logDetails('Renamed {}'.format(film.newFilenameWithExt))

            pyfancy().dark_gray('\t→ Moving {}'.format(os.path.join(destDir, film.newFilenameWithExt))).output()
            utils.logDetails('Moving {}'.format(film.newFilenameWithExt))

            dst = os.path.join(destDir, film.newFilenameWithExt)
            utils.safeMove(os.path.join(searchDir, film.newFilenameWithExt), dst)
            film.sourcePath = dst
                    
        # Or if it's a directory, clean it up
        elif film.isDir:
            deletedFiles = 0

            # Check for valid file types inside this dir; if none, skip
            validFiles = []
            for ext in config.videoFileExts + config.extraExts:
                ext = '{}*{}'.format(SLASH, ext)
                validFiles.extend(glob.glob(film.sourcePath + ext))

            if len(validFiles) == 0:
                pyfancy().red('\t→ No valid files found in this folder').output()
                utils.logDetails('No valid files found in this folder')
                continue

            # Enumerate files inside folder
            for innerFile in os.listdir(film.sourcePath):

                currentFile = os.path.join(film.sourcePath, innerFile)

                # Delete files we don't want to keep
                if not utils.isValidExtension(innerFile) or utils.hasIgnoredStrings(innerFile):
                    if not config.testMode and config.cleanUnwantedFiles:
                        os.remove(currentFile)
                        deletedFiles = deletedFiles + 1
                        continue

                # Rename files we want to keep and move them if not using folders
                if utils.isValidExtension(innerFile) and not utils.hasIgnoredStrings(innerFile):
                    
                    # Create new filename based on innerFile's ext
                    newFilename = '{}{}'.format(film.newFilename, os.path.splitext(innerFile)[1])
    
                    utils.rename(currentFile, newFilename)

                    src = os.path.join(film.sourcePath, newFilename)
                    dst = os.path.join(destDir, newFilename)

                    pyfancy().dark_gray('\t→ Renamed ').yellow(newFilename).output()
                    utils.logDetails('Renamed {}'.format(newFilename))

                    if os.path.exists(dst):
                        abortStr = 'Aborting; duplicate file found ({})'.format(utils.sizeDiffString(src, dst))
                        pyfancy().red('\t→ {}'.format(abortStr)).output()
                        utils.logDetails(abortStr)
                    else:
                        pyfancy().dark_gray('\t→ Moving {}'.format(dst)).output()
                        utils.logDetails('Moving {}'.format(dst))
                        utils.safeMove(src, dst)

            # TODO Fix this so that renamed files size are calculated

            # When all copying is done, update the film's sourcePath    
            film.sourcePath = destDir

            # Print results of cleaning
            if config.cleanUnwantedFiles:
                cleanStr = 'Cleaned {} unwanted file{}'.format(deletedFiles, 's' if deletedFiles > 1 else '')
                pyfancy().dim('\t→ {}'.format(cleanStr)).output()
                utils.logDetails(cleanStr)
                
            # Clean up parent folder, if safe to do so and enabled
            # check that source folder is now empty and < 1 KB
            if config.cleanUpSource:
                if utils.size(film.originalPath) < 1000 and utils.countFilesInDir(film.originalPath) == 0:
                    utils.cleanOriginalPath(film)

                    pyfancy().dim('\t→ Removing parent folder').output()
                    utils.logDetails('Removing parent folder')
                else:
                    pyfancy().red('\t→ Could not remove parent folder because it is not empty').output()
                    utils.logDetails('Could not remove parent folder because it is not empty')