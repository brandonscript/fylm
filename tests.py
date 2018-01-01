#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import unittest, os, re, sys
from glob import glob
from film import Film
import config, utils, random

print('Init tests...')

# Get all files and folder in ./tests dir, ignoring .sh creation script
files = sorted(glob(os.path.join('./tests', '*.*[!sh]')), key=os.path.getctime)

# for film in [Film(file) for file in files]:
#     if film.title is not None:
#         titleWords = film.title.split(' ')
#         for i in range(len(titleWords)):
#             result = utils.searchTMDb(' '.join(titleWords), film.year)
#             if result is not None: 
#                 film.title = result['title']
#                 film.id = result['id']
#                 film.year = result['year']
#                 break
#             else: 
#                 titleWords = titleWords[:-1]

#     print(film.title, film.year, film.id)

class FilmsTestCase(unittest.TestCase):
    # Tests for FilmRenamer app

    # @unittest.skip("Skip long running testTMDbLookup")
    def testTMDbLookup(self):
        # Look up films by name from TMDb and update title
        print('')
        for film in [Film(file) for file in files]:
            if film.isValidFilename:
                sys.stdout.write(film.originalFilename)
                result = None
                titleWords = film.title.split(' ')
                for i in range(len(titleWords)):
                    searchTitle = ' '.join(titleWords)
                    result = utils.searchTMDb(film.title, film.year)
                    if result is not None: 
                        film.setTitle(result['title'])
                        film.id = result['id']
                        film.year = result['year']
                        break
                    else: 
                        titleWords = titleWords[:-1]

                if result is not None:   
                    sys.stdout.write(" ....... ✓ {} ({})\n".format(film.title, film.year))
                    self.assertIsNotNone(film.title)
                    self.assertIsNotNone(film.id)
                    self.assertIsNotNone(film.year)
                else:
                    sys.stdout.write(" ==> Skipping {}\n".format(film.originalFilename))

    def testTitle(self):
        # Check that the title sets correctly using getter/setter
        for film in [Film(file) for file in files]:
            if film.isValidFilename:
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
            if film.isValidFilename and ', the' in film.titleThe.lower():
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

    def testIsValidFilename(self):
        # Check that file/folder names are valid objects
        for film in [Film(file) for file in files]:
            if (film.originalFilename == "The.Magicians.S01E01.720p.HDTV.x264-KILLERS"
                or film.originalFilename == "The.Magicians.S02.1080p.WEB-DL.DD5.1.H264-RARBG"
                or film.originalFilename == "Masterchef.Canada.S02E01.720p.WEB.h264-spamTV"
                or film.originalFilename == "The.Killing.S04E06.Eden.1080p.WEBRip.DD5.1.H.264-Abjex"
                or film.originalFilename == "The.Killing.S04E02.1080p.WEBRip.DD5.1.H.264-Abjex"
                or film.originalFilename == "The.Killing.S04.1080p.WEBRip.DD5.1.H.264-Abjex"
                or film.originalFilename == "2001 A Space Odyssey.BluRay.1080p.DTS.x264-CHD"
                or film.originalFilename == "rep-sausageparty.1080p.bluray.x264"
                or film.originalFilename == "rep-hellorhighwater.1080p.bluray.x264"
                or film.originalFilename == "m-nina.1080p"
                or film.originalFilename == "geckos-t2-trainspotting-1080p"
                or film.originalFilename == "pfa-outlaws.and.angels.1080p"
                or film.originalFilename == "tl-lk.1080p"
                or film.originalFilename == "The.Magicians.US.S01E04.INTERNAL.720p.HDTV.x264-KILLERS"):
                self.assertFalse(film.isValidFilename)
            else:
                self.assertTrue(film.isValidFilename)

    def testIsValidFileExt(self):
        # Check file extensions
        for film in [Film(file) for file in files]:
            if film.isFile:
                self.assertTrue(film.ext is not None and [film.ext in config.videoFileExts + config.extraExts])
            elif film.isDir:
                self.assertEqual(film.ext, None)

    def testIsFileOrFolder(self):
        # Check that files/folders are detected accurately
        for file in files:
            self.assertEqual(Film(file).isFile, os.path.isfile(file))
            self.assertEqual(Film(file).isDir, os.path.isdir(file))
            self.assertEqual(Film(file).isFile, Film(file).ext is not None and Film(file).ext in config.videoFileExts + config.extraExts)
            self.assertEqual(Film(file).isDir, Film(file).ext is None)

if __name__ == '__main__':
    unittest.main()
