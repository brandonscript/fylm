#!/usr/bin/env python
# -*- coding: utf-8 -*- 
from __future__ import unicode_literals

import unittest, os, re, sys, unicodedata, io
from glob import glob
from film import Film
import config, utils, random
from tests.make import make

divider = '======================================================================'

def printTitle(title):
    print('\n{}\n{}\n{}'.format(divider, title, divider))

print('Init tests...')

make() # Make test files

files = [unicodedata.normalize('NFC', file) for file in sorted(os.listdir('tests/files'), key=lambda s: s.lower()) if file != '.DS_Store' and file != 'Thumbs.db']

with io.open("tests/index.txt", mode="r", encoding="utf-8") as f:
    idIndex = [int(i.split(' ')[0]) for i in f.readlines()]
    # a helpful regex for taking the output of this and creating a new index: (?<=\d)   \d+\s+

class FilmsTestCase(unittest.TestCase):
    # Tests for FilmRenamer app

    def testIsValidFilm(self):
        # Check that file/folder names are valid objects
        printTitle('Film.isValidFilm')
        for film in [Film(file) for file in files]:
            if (film.originalFilename == "The.Magicians.S01E01.720p.HDTV.x264-KILLERS.mkv"
                or film.originalFilename == "The.Magicians.S02.1080p.WEB-DL.DD5.1.H264-RARBG"
                or film.originalFilename == "The.Magicians.US.S01E04.INTERNAL.720p.HDTV.x264-KILLERS.mkv"
                or film.originalFilename == "Masterchef.Canada.S02E01.720p.WEB.h264-spamTV"
                or film.originalFilename == "The.Killing.S04E06.Eden.1080p.WEBRip.DD5.1.H.264-Abjex.mkv"
                or film.originalFilename == "The.Killing.S04E02.1080p.WEBRip.DD5.1.H.264-Abjex.mkv"
                or film.originalFilename == "The.Killing.S04.1080p.WEBRip.DD5.1.H.264-Abjex"
                or film.originalFilename == "2001 A Space Odyssey.BluRay.1080p.DTS.x264-CHD"
                or film.originalFilename == "2001 A Space Odyssey.BluRay.1080p.DTS.x264-CHD.mkv"
                or film.originalFilename == "rep-sausage.party.1080p.bluray.x264.mkv"
                or film.originalFilename == "rep-hellorhighwater.1080p.bluray.x264"
                or film.originalFilename == "nina.1080p.mkv"
                or film.originalFilename == "pfa-outlaws.and.angels.1080p.mkv"
                or film.originalFilename == "A Monster Calls-1080p"
                or film.originalFilename == "geckos-t2-trainspotting-1080p"
                or film.originalFilename == "pfa-outlaws.and.angels.1080p"
                or film.originalFilename == "tl-lk.1080p.mkv"
                or film.originalFilename == "geckos-t2-trainspotting-1080p.mkv"
                or film.originalFilename == "Bridesmaids.1080p.Bluray.x264-TWiZTED"):
                self.assertFalse(film.isValidFilm)
                print(' ✓ pass   Not a film: {}'.format(film.originalFilename))
            else:
                # print('Y: {}'.format(film.originalFilename))
                self.assertTrue(film.isValidFilm)

    # @unittest.skip("Skip long running testSearchTMDb")
    def testSearchTMDb(self):
        # Look up films by name from TMDb and update title
        printTitle('Film.searchTMDb()')
        idx = 0
        for film in [Film(file) for file in files]:
            if film.isValidFilm:
                
                film.searchTMDb()

                self.assertIsNotNone(film.title)
                self.assertIsNotNone(film.id)
                self.assertEqual(film.id, idIndex[idx])
                self.assertIsNotNone(film.year)
                sys.stdout.write(" ✓ pass   {} {} {} {} \n".format(film.title.ljust(40)[:40], str(film.year).ljust(6)[:6], str(film.id).ljust(10)[:10], film.originalFilename))
                idx = idx + 1
            else:
                self.assertIsNone(film.id)

    def testTitle(self):
        # Check that the title sets correctly using getter/setter
        for film in [Film(file) for file in files]:
            if film.isValidFilm:
                origTitle = film.title
                # get
                self.assertEqual(film.title, origTitle)
                self.assertEqual(film._title, origTitle)
                # set
                film.setTitle("jibberish")
                self.assertEqual(film.title, "jibberish")
                self.assertEqual(film._title, "jibberish")
                # re-clean
                film.recleanTitle()
                self.assertEqual(film.title, origTitle)
                self.assertEqual(film._title, origTitle)

    def testTitleThe(self):
        # Check that films beginning with 'The' have it moved to the end, ', The'
        for film in [Film(file) for file in files]:
            if film.isValidFilm and ', the' in film.titleThe.lower():
                self.assertFalse(film.titleThe.lower().startswith('the '))
                self.assertTrue(film.titleThe.lower().endswith(', the'))

    def testYear(self):
        # Check that year is detected correctly
        for film in [Film(file) for file in files]:
            if film.year is not None:
                self.assertGreaterEqual(film.year, 1910)
                self.assertLess(film.year, 2160)
                self.assertNotEqual(film.year, 2160)
                self.assertNotEqual(film.year, 1080)
                self.assertNotEqual(film.year, 720)

    def testQuality(self):
        # Check that quality is detected correctly
        for film in [Film(file) for file in files]:
            if film.quality is not None:
                self.assertIn(film.quality, ['720p', '1080p', '2160p'])

    def testEdition(self):
        # Check that editions, when detected, are set correctly and cleaned from original string
        for film in [Film(file) for file in files]:
            for key, value in config.specialEditionStrings:
                if key in film.originalFilename.lower():
                    self.assertEqual(film.edition, value)
                    self.assertNotIn(key, film.title.lower())
                    break

    def testIsValidFileExt(self):
        # Check file extensions
        for film in [Film(file) for file in files]:
            if film.isFile:
                self.assertTrue(film.ext is not None and [film.ext in config.videoFileExts + config.extraExts])
            elif film.isDir:
                self.assertEqual(film.ext, None)

if __name__ == '__main__':
    unittest.main()
