#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandoncript

# This program is bound to the Hippocratic License 2.1
# Full text is available here:
# https: // firstdonoharm.dev/version/2/1/license

# Further to adherence to the Hippocratic Licenese, this program is
# free software: you can redistribute it and / or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. Full text is avaialble here:
# http: // www.gnu.org/licenses

# Where a conflict or dispute would arise between these two licenses, HLv2.1
# shall take precedence.

import os
import itertools

try:
    from math import isclose
except ImportError:
    from pytest import approx
    def isclose(a, b, abs_tol=0.0):
        return a == approx(b, abs_tol)

import pytest
from pathlib import Path

import fylmlib.config as config
from fylmlib import Film, Find
import fylm
import conftest
from make import Make, MB, GB

SRC = conftest.src_path
DST = conftest.dst_paths

# An array of potential duplicate file prefixes
NEW_AQUA = 'Aquaman.2018'
NEW_ROGUE = 'Rogue.One.A.Star.Wars.Story.2016'
NEW_MI = 'Mission.Impossible.Rogue.Nation.2015'
NEW_STB = 'Star.Trek.Beyond.2016'
NEW_STID = 'Star.Trek.Into.Darkness.2013'
NEW_YOLT = 'You.Only.Live.Twice.1967'

MOVED_AQUA = 'Aquaman (2018)'
MOVED_ROGUE = 'Rogue One - A Star Wars Story (2016)'
MOVED_MI = 'Mission Impossible - Rogue Nation (2015)'
MOVED_STB = 'Star Trek Beyond (2016)'
MOVED_STID = 'Star Trek Into Darkness (2013)'
MOVED_YOLT = 'You Only Live Twice (1967)'

def new(s: str, res='SD', media='BluRay', proper=False, hdr=False) -> Path:
    proper = '.PROPER' if proper else ''
    hdr = '.10-bit.HDR' if hdr else ''
    if res == '4K' or res == '2160p':
        return SRC / f'{s}.2160p.{media}{proper}{hdr}.DTS.x264-group.mp4'
    elif res == '1080p':
        return SRC / f'{s}.1080p.{media}{proper}.DTS.x264-group.mkv'
    elif res == '720p':
        return SRC / f'{s}.720p.{media}{proper}.DTS.x264-group.mkv'
    elif res == 'SD':
        return SRC / f'{s}.{media}.avi'
    
def moved(s: str, res='SD', media='Bluray', proper=False, hdr=False) -> Path:
    proper = ' Proper' if proper else ''
    hdr = ' HDR' if hdr else ''
    if res == '4K' or res == '2160p':
        return DST['2160p'] / f'{s}/{s} {media}-2160p{proper}{hdr}.mp4'
    elif res == '1080p':
        return DST['1080p'] / f'{s}/{s} {media}-1080p{proper}.mkv'
    elif res == '720p':
        return DST['720p'] / f'{s}/{s} {media}-720p{proper}.mkv'
    elif res == 'SD':
        return DST['SD'] / f'{s}/{s}.avi'
    
class TestDuplicates(object):

    def test_remove_duplicates_and_dirs(self):
        
        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = [] 
        
        # Replace 1080p films with 4K
        config.duplicates.upgrade_table['1080p'] = ['2160p'] 
        
        # Replace 720p films with 4K or 1080p
        config.duplicates.upgrade_table['720p'] = ['2160p', '1080p'] 

        # Replace SD with any higher quality.
        config.duplicates.upgrade_table['SD'] = ['2160p', '1080p', '720p'] 
    
        Make.mock_files(
            (new(NEW_ROGUE, '4K'), 52234 * MB),
            (moved(MOVED_ROGUE, '1080p'), 12393 * MB),
            (moved(MOVED_ROGUE, '720p'), 7213 * MB),
            (moved(MOVED_ROGUE), 786 * MB),
            (moved(MOVED_MI, '1080p'), 8522 * MB)
        )
        
        # Assert that there are 4 existing files
        existing_files = list(itertools.chain.from_iterable(
            [f.video_files for f in Find.existing()]))
        assert(len(existing_files) == 4)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(new(NEW_ROGUE, '4K')).duplicates.files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file replaced all others of lesser quality and was correctly processed
        assert(not new(NEW_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '4K').exists())
        assert(not moved(MOVED_ROGUE, '1080p').exists())
        assert(not moved(MOVED_ROGUE, '720p').exists())
        assert(not moved(MOVED_ROGUE).exists())

        # Verify that non-duplicates are not deleted
        assert(    moved(MOVED_MI, '1080p').exists())

    def test_replace_all_with_2160p(self):
        
        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = [] 
        
        # Replace 1080p films with 4K
        config.duplicates.upgrade_table['1080p'] = ['2160p'] 
        
        # Replace 720p films with 4K or 1080p
        config.duplicates.upgrade_table['720p'] = ['2160p', '1080p'] 

        # Replace SD with any higher quality.
        config.duplicates.upgrade_table['SD'] = ['2160p', '1080p', '720p'] 

        Make.mock_files(
            (new(NEW_ROGUE, '4K'), 52234 * MB),
            (moved(MOVED_ROGUE, '1080p'), 12393 * MB),
            (moved(MOVED_ROGUE, '720p'), 7213 * MB),
            (moved(MOVED_ROGUE), 786 * MB)
        )

        # Assert that there are 3 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in Find.existing()]))
        assert(len(existing_files) == 3)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(new(NEW_ROGUE, '4K')).duplicates.files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file replaced all others of lesser quality and was correctly processed
        assert(not new(NEW_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '4K').exists())
        assert(not moved(MOVED_ROGUE, '1080p').exists())
        assert(not moved(MOVED_ROGUE, '720p').exists())
        assert(not moved(MOVED_ROGUE).exists())
        
        # Assert that duplicate backup files are removed
        assert(not Path(f"{moved(MOVED_ROGUE, '1080p')}.dup~").exists())
        assert(not Path(f"{moved(MOVED_ROGUE, '720p')}.dup~").exists())
        assert(not Path(f'{moved(MOVED_ROGUE)}.dup~').exists())
        
        # Assert that empty duplicate parent dirs are removed
        assert(not moved(MOVED_ROGUE, '1080p').parent.exists())
        assert(not moved(MOVED_ROGUE, '720p').parent.exists())
        assert(not moved(MOVED_ROGUE).parent.exists())

    def test_keep_all_2160p(self):
        
        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        config.duplicates.upgrade_table['1080p'] = [] 
        
        # Replace 720p films with 1080p
        config.duplicates.upgrade_table['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        config.duplicates.upgrade_table['SD'] = ['1080p', '720p'] 
        
        Make.mock_files(
            (new(NEW_ROGUE, '4K'), 52234 * MB),
            (moved(MOVED_ROGUE, '1080p'), 12393 * MB),
            (moved(MOVED_ROGUE, '720p'), 7213 * MB),
            (moved(MOVED_ROGUE), 786 * MB)
        )

        # Assert that there are 3 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in Find.existing()]))
        assert(len(existing_files) == 3)

        # Assert that for the original source file, there are 3 duplicate files detected
        assert(len(Film(new(NEW_ROGUE, '4K')).duplicates.files) == 3)

        # Execute
        fylm.main()
        
        # Assert that the 4K file didn't replace any others and was correctly processed
        assert(not new(NEW_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '1080p').exists())
        assert(    moved(MOVED_ROGUE, '720p').exists())
        assert(    moved(MOVED_ROGUE).exists())

    def test_keep_2160p_and_1080p(self):
        
        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        config.duplicates.upgrade_table['1080p'] = [] 
        
        # Replace 720p films with 1080p
        config.duplicates.upgrade_table['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        config.duplicates.upgrade_table['SD'] = ['1080p', '720p'] 
        
        Make.mock_files(
            (new(NEW_ROGUE, '4K'), 52234 * MB),
            (new(NEW_ROGUE, '1080p'), 12393 * MB),
            (moved(MOVED_ROGUE, '720p'), 7213 * MB),
            (moved(MOVED_ROGUE), 786 * MB)
        )

        # Assert that there are 2 existing files
        existing_files = list(itertools.chain.from_iterable([f.video_files for f in Find.existing()]))
        assert(len(existing_files) == 2)

        # Assert that for each of the 2 source files, there are 2 duplicate files detected
        assert(len(Film(new(NEW_ROGUE, '4K')).duplicates.files) == 2)
        assert(len(Film(new(NEW_ROGUE, '1080p')).duplicates.files) == 2)

        # Execute
        fylm.main()
        
        # Assert that the 4K and 1080p files replaced all others of lesser quality and were correctly processed
        assert(not new(NEW_ROGUE, '4K').exists())
        assert(not new(NEW_ROGUE, '1080p').exists())
        assert(    moved(MOVED_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '1080p').exists())
        assert(not moved(MOVED_ROGUE, '720p').exists())
        assert(not moved(MOVED_ROGUE).exists())

    def test_keep_2160p_with_existing_1080p(self):
        
        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = [] 
        
        # Do not replace 1080p films with any other quality
        config.duplicates.upgrade_table['1080p'] = [] 
        
        # Replace 720p films with 1080p
        config.duplicates.upgrade_table['720p'] = ['1080p'] 

        # Replace SD with any higher quality except 2160p.
        config.duplicates.upgrade_table['SD'] = ['1080p', '720p'] 
        
        Make.mock_files(
            (new(NEW_ROGUE, '4K'), 14234 * MB),
            (moved(MOVED_ROGUE, '1080p'), 19393 * MB)
        )

        # Assert that there is 1 duplicate
        assert(len(Find.existing()) == 1)
        # Execute
        fylm.main()
        
        # Assert that the 4K and 1080p files replaced all others of lesser quality and were correctly processed
        assert(not new(NEW_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '4K').exists())
        assert(    moved(MOVED_ROGUE, '1080p').exists())

    def test_upgrade_with_proper(self):

        big_size = 12393 * MB
        sm_size = 11213 * MB

        proper = new(NEW_ROGUE, '1080p', proper=True)
        proper_moved = moved(MOVED_ROGUE, '1080p', proper=True)
        reg_moved = moved(MOVED_ROGUE, '1080p')
        
        Make.mock_files(
            (proper, sm_size),
            (reg_moved, big_size)
        )

        # Assert that there is 1 duplicate
        assert(len(Find.existing()) == 1)
        # Execute
        fylm.main()
        
        # Assert that the proper 1080p file overwrites the existing one
        assert(not proper.exists())
        assert(proper_moved.exists())
        # We need multiple the OS size by MB here because test files are ÷ 1024 on the filesystem
        assert(    isclose(Film(proper_moved).size.value, sm_size * MB, abs_tol=10))

    def test_replace_smaller_overwrite_on(self):

        big_size = 14393 * MB
        sm_size = 8213 * MB
        
        Make.mock_files(
            (new(NEW_ROGUE, '1080p'), big_size),
            (moved(MOVED_ROGUE, '1080p'), sm_size)
        )

        # Assert that there is 1 duplicate
        assert(len(Find.existing()) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, larger 1080p file overwrites the existing, smaller one
        assert(not new(NEW_ROGUE, '1080p').exists())
        assert(    moved(MOVED_ROGUE, '1080p').exists())
        assert(isclose(Film(moved(MOVED_ROGUE, '1080p')
                            ).size.value, big_size * MB, abs_tol=10))

    def test_do_not_replace_larger_overwrite_off(self):

        # Set up config
        config.duplicates.force_overwrite = False

        big_size = 14393 * MB
        sm_size = 8213 * MB
        
        Make.mock_files(
            (new(NEW_ROGUE, '1080p'), sm_size),
            (moved(MOVED_ROGUE, '1080p'), big_size)
        )

        # Assert that there is 1 duplicate
        assert(len(Find.existing()) == 1)
        # Execute
        fylm.main()
        
        # Assert that the new, smaller 1080p did not overwrite the existing, bigger one
        # and that the original was left intact (not renamed)
        assert(    new(NEW_ROGUE, '1080p').exists())
        assert(    moved(MOVED_ROGUE, '1080p').exists())
        assert(isclose(Film(moved(MOVED_ROGUE, '1080p')
                            ).size.value, big_size * MB, abs_tol=10))

    def test_multiple_editions(self):

        new_ = new(NEW_YOLT, '1080p')
        new_moved = moved(MOVED_YOLT, '1080p')
        existing = Film(DST['1080p'] / f'{MOVED_YOLT}/{MOVED_YOLT} [Extended] 1080p-Bluray.mkv')

        new_size = 9393 * MB
        existing_size = 8213 * MB
        
        Make.mock_files(
            (new_, new_size),
            (existing, existing_size)
        )

        # Assert that there is 1 duplicate
        assert(len(Find.existing()) == 1)
        # Execute
        fylm.main()
        
        # Assert that both editions exist in the end, with a console warning
        assert(not new_.exists())
        assert(    new_moved.exists())
        assert(    existing.exists())

    def test_keep_4k_and_hdr(self):
        
        new_ = [
            (Film(new(NEW_AQUA, '1080p')), 8.48),
            (Film(new(NEW_AQUA, '4K')), 32.18),
            (Film(new(NEW_ROGUE, '1080p')), 14.41),
            (Film(new(NEW_ROGUE, '4K', media='WEBDL')), 21.68),
            (Film(new(NEW_STB, '4K', hdr=True)), 18.54),
            (Film(new(NEW_STID, '4K', hdr=True)), 15.23),
            (Film(new(NEW_STID, '4K')), 22.81)
        ]
        
        existing = [
            (Film(moved(MOVED_AQUA, '1080p')), 18.53),
            (Film(moved(MOVED_ROGUE, '1080p', media='WEBDL')), 9.80),
            # Intentionally in the wrong folder
            (Film(DST['1080p'] / \
             f'{MOVED_ROGUE}/{MOVED_ROGUE} WEBDL-2160p.mkv'), 18.55),
            (Film(moved(MOVED_STB, '4K')), 20.48),
            (Film(moved(MOVED_STID, '1080p')), 12.72),
            (Film(moved(MOVED_STID, '4K')), 24.20)
        ]
        
        expect = [
            (Film(moved(MOVED_AQUA, '1080p')), 18.53),
            (Film(moved(MOVED_AQUA, '4K')), 32.18),
            (Film(moved(MOVED_ROGUE, '1080p')), 14.41),
            (Film(moved(MOVED_ROGUE, '4K', media='WEBDL')), 21.68),
            (Film(moved(MOVED_STB, '4K')), 20.48),
            (Film(moved(MOVED_STB, '4K', hdr=True)), 18.54),
            (Film(moved(MOVED_STID, '1080p')), 12.72),
            (Film(moved(MOVED_STID, '4K', hdr=True)), 15.23),
            (Film(moved(MOVED_STID, '4K')), 24.20)
        ]

        do_not_move = [new_[0], new_[6]]

        # Do not replace 2160p films with any other quality
        config.duplicates.upgrade_table['2160p'] = []

        # Do not replace 1080p films with any other quality
        config.duplicates.upgrade_table['1080p'] = []
        
        for f, s in new_:
            Make.mock_file(f, s * GB)

        for f, s in existing:
            Make.mock_file(f, s * GB)

        existing_films = Find.existing()
        # Assert that there are 6 duplicate films
        assert(len(existing_films) == 5)

        # Assert that the total duplicate files is 7
        assert(len(list(itertools.chain(*[f.wanted_files for f in map(Film, existing_films)]))) == 6)
        
        # Execute
        fylm.main()
        
        # Assert that the correct editions were moved, and those that didn't meet the criteria were left alone
        for f, s in expect:
            assert(f.exists())
            assert(isclose(f.size.value, s * GB, abs_tol=10))

        for f, s in do_not_move:
            assert(f.exists())
            assert(isclose(f.size.value, s * GB, abs_tol=10))
            
    @pytest.mark.skip(reason="Not implemented")
    def test_different_media(self):
        pass

class TestDuplicatesMap:

    @pytest.mark.skip(reason="Not implemented")
    def test_decide(self):
        pass

    @pytest.mark.skip(reason="Not implemented")
    def test_map_operators(self):
        pass
