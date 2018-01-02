#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import os, re
import config
import patterns
import utils

class Film:

    def __init__(self, file):
        # Immutable original path of file; remains even after it moves
        self.originalPath = file

        # Current source path of film
        self.sourcePath = file

        # Internal title property for storing cleaned title
        self._title = None

        # Internal title property for storing back up file size
        self._size = None

        # Internal ext property for storing back up of ext
        self._ext = None

        self.id = None 

    @property
    # Original file name of film without extension, attempt to derive from folder first, then file
    def originalFilename(self):
        return os.path.basename(os.path.splitext(self.sourcePath)[0] if os.path.isfile(self.sourcePath) else self.sourcePath)

    @property
    # Original file extension if file is detected
    def ext(self):
        if self._ext:
            return self._ext
        else:
            self._ext = os.path.splitext(self.sourcePath)[1] if os.path.isfile(self.sourcePath) else None
            return self._ext

    @property
    # Size of file
    def size(self):
        if os.path.exists(self.sourcePath):
            self._size = utils.size(self.sourcePath)
        return self._size

    @property
    # Film title, best guess by splitting on the year and capturing everying left of 
    # By default, this is a getter method that calculates a cleaned title on the fly.
    # It also, however, supports a setter method that can overwrite the calculated title
    def title(self):
        if self._title: 
            return self._title
        else:
            self._title = utils.cleanTitle(self)
            return self._title

    # Title setter
    def setTitle(self, value):
        self._title = value

    # Re-cleans the title from the original filename, overwriting any other previous replacements
    def recleanTitle(self):
        self._title = utils.cleanTitle(self)

    @property
    # For titles that begin with 'The', move it to the end: ', The'
    def titleThe(self):
        if not self.isValidFilename: return None
        if re.search(r'(^the\b|, the)', self.title, re.I):
            return '{}{}'.format(re.sub(r'(^the\W+|, the)', '', self.title, flags=re.I), ', The')
        else: 
            return self.title

    @property
    # Year film was released, int
    def year(self):
        match = re.search(patterns.year, self.originalFilename)
        return int(match.group('year')) if match else None

    @property
    # Quality of film released, 720p, 1080p, or 2160p (SD ignored)
    def quality(self):
        match = re.search(patterns.quality, self.originalFilename)
        quality = match.group('quality') if match else None
        if quality is not None and 'p' not in quality:
            quality += 'p'
        return quality

    @property
    # Special edition keyword detection, e.g. "Unrated Extended Director's Cut Shiny Edition!"
    def edition(self):
        for key, value in config.specialEditionStrings:
            rx = re.compile(key, re.I)
            if re.search(rx, self.originalFilename):
                self.setTitle(re.sub(rx, '', self.title))
                return value

    @property
    # Originating media; currently only supports BluRay, WEBRip, and defaults to None
    def media(self):
        match = re.search(patterns.media, self.originalFilename)
        return "BluRay" if match and match.group('bluray') else None
        return "WEB-DL" if match and match.group('web') else None

    @property
    # Determine if in fact this is actually a film
    def isValidFilename(self):
        return all(check == True for check in [not self.isTVShow, self.year is not None])

    @property
    # Is this an allowed file extension? Will always return False if isDir==True
    def isAllowedExtension(self):
        return any([self.ext in config.videoFileExts + config.extraExts]) if self.isFile else False

    @property
    # Is this a film file? Will always return False if isDir==True
    def isFilm(self):
        return any([self.ext in config.videoFileExts]) if self.isFile else False

    @property
    # Check if this is a TV show; used primarily for skipping
    def isTVShow(self):
        return bool(re.search(r"\bS\d{2}(E\d{2})?\b", self.originalFilename, re.I))

    @property
    # Check if any of the ignored strings are in this file; used primarly for skipping
    def hasIgnoredStrings(self):
        return utils.hasIgnoredStrings(self.originalFilename)

    @property
    def isFile(self):
        return os.path.isfile(self.sourcePath)

    @property
    def isDir(self):
        return os.path.isdir(self.sourcePath)

    def searchTMDb(self):
        if config.TMDb['enabled']:
            result = utils.searchTMDb(self.title, self.year)
            if result is not None: 
                self.setTitle(result['title'])
                self.id = result['id']
                self.year = result['year']            

    @property
    def newFilename(self):
        # renamePattern: Permitted rename pattern objects: {title}, {title-the}, {year}, {quality}, {edition}, {media}
        # for using other characters with pattern objects, place them inside {} e.g. { - edition}
        # for escaping templating characters, use \{ \}, e.g. {|{edition\}}
        templateString = config.renamePattern

        patternReplacer = [
            ["title", self.title],
            ["title-the", self.titleThe],
            ["edition", self.edition],
            ["year", self.year],
            ["quality", self.quality],
            ["media", self.media]
        ]

        for expString, prop in patternReplacer:
            exp = re.compile(r'\{([^\{]*)' + expString + r'([^\}]*)\}', re.I)
            match = re.search(exp, templateString)
            replacement = '{}{}{}'.format(match.groups()[0], prop, match.groups()[1]) if match and match.groups() is not None else prop
            templateString = re.sub(exp, replacement if prop is not None else '', templateString)

        # Fix escaped template chars
        templateString = templateString.replace('\{', '{')
        templateString = templateString.replace('\}', '}')

        # Strip superfluous whitespace
        return ' '.join(templateString.split()).strip()

    @property
    def newFilenameWithExt(self):
        return '{}{}'.format(self.newFilename, self.ext or '')