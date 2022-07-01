#!/usr/bin/env python

# Fylm
# Copyright 2021 github.com/brandonscript

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

import multiprocessing
import conftest
from pathlib import Path
from make import Make, MB

import fylm
from fylmlib import Film, App, Subtitle

SRC = conftest.src_path
DST = conftest.dst_paths['1080p']

NEW_ROGUE = 'Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.x264-RiZE'
MOVED_ROGUE = 'Rogue One - A Star Wars Story (2016) Bluray-1080p'
MOVED_ROGUE_4K = 'Rogue One - A Star Wars Story (2016) Bluray-2160p HDR'
MOVED_ROGUE_DIR = 'Rogue One - A Star Wars Story (2016)'
NEW_VIDEO = SRC / NEW_ROGUE / f'{NEW_ROGUE}.mkv'
NEW_SUB1 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.en.srt'
NEW_SUB2 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.en-us.srt'
NEW_SUB3 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.Eng.srt'
NEW_SUB4 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.English.srt'
NEW_SUB5 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.fr.srt'
NEW_SUB6 = SRC / NEW_ROGUE / f'{NEW_ROGUE}.srt'

class TestSubtitle:
    
    def test_sub_init(self):

        sub1 = Subtitle(NEW_SUB1)
        assert sub1.captured == 'en'
        assert sub1.code == 'en'
        assert sub1.language == 'English'
        
        sub2 = Subtitle(NEW_SUB2)
        assert sub2.captured == 'en-us'
        assert sub2.code == 'en'
        assert sub2.language == 'English'
        
        sub3 = Subtitle(NEW_SUB3)
        assert sub3.captured == 'Eng'
        assert sub3.code == 'en'
        assert sub3.language == 'English'
        
        sub4 = Subtitle(NEW_SUB4)
        assert sub4.captured == 'English'
        assert sub4.code == 'en'
        assert sub4.language == 'English'
        
        sub5 = Subtitle(NEW_SUB5)
        assert sub5.captured == 'fr'
        assert sub5.code == 'fr'
        assert sub5.language == 'French'
    
    def test_path_with_lang(self):
        
        sub = Subtitle(NEW_SUB1)
        assert sub.path_with_lang(Path(f'{MOVED_ROGUE}.srt')) == Path(f'{MOVED_ROGUE}.en.srt')
        
    def test_multiple_langs(self):
        
        sub1 = Subtitle(NEW_SUB1)
        sub2 = Subtitle(NEW_SUB5)
        assert sub1.path_with_lang(Path(f'{MOVED_ROGUE}.srt')) == Path(f'{MOVED_ROGUE}.en.srt')
        assert sub2.path_with_lang(Path(f'{MOVED_ROGUE}.srt')) == Path(f'{MOVED_ROGUE}.fr.srt')
        
    def test_path_no_lang(self):
        
        sub = Subtitle(NEW_SUB6)
        assert sub.path_with_lang(Path(f'{MOVED_ROGUE}.srt')) == Path(f'{MOVED_ROGUE}.srt')
        
    def test_move_film_with_subs(self):
        
        Make.mock_files(NEW_VIDEO, NEW_SUB1, NEW_SUB5)
        
        App.run()
        
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.mkv').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.en.srt').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.fr.srt').exists()
    
    
class TestExtraWantedFiles:
    
    def test_extra_video_files(self):
        
        Make.mock_files(SRC / MOVED_ROGUE_DIR / f'{NEW_ROGUE}.mkv', 
                        SRC / MOVED_ROGUE_DIR / f'Commentary.mp4',
                        SRC / MOVED_ROGUE_DIR / f'pid.avi')
        
        App.run()
        
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.mkv').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE} Commentary.mp4').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE} Pid.avi').exists()
    
    def test_multiple_qualities(self):
        
        Make.mock_files(SRC / MOVED_ROGUE_DIR / f'{NEW_ROGUE}.mkv',
                        SRC / MOVED_ROGUE_DIR / f'Rogue.One.2160p.Bluray.HDR.mp4')
        
        App.run()
        
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.mkv').exists()
        assert (conftest.dst_paths['2160p'] / MOVED_ROGUE_DIR / f'{MOVED_ROGUE_4K}.mp4').exists()
    
    def test_multiple_mkv_files(self):
        Make.mock_files((SRC / NEW_ROGUE / f'{NEW_ROGUE}.mkv', 8000 * MB),
                        (SRC / NEW_ROGUE / f'{NEW_ROGUE}.commentary.mkv', 200 * MB),
                        (SRC / NEW_ROGUE / f'{NEW_ROGUE}.Extras.mkv', 500 * MB))
        
        App.run()
        
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE}.mkv').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE} Commentary.mkv').exists()
        assert (DST / MOVED_ROGUE_DIR / f'{MOVED_ROGUE} Extras.mkv').exists()
