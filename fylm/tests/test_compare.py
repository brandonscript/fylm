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
import random

from lazy import lazy
import pytest

import fylmlib.config as config
from fylmlib import Compare, Film
import conftest
from make import Make, MB
from fylmlib.enums import *

Rt = ComparisonResult
Rn = ComparisonReason

chrs = 'abcdefghijklmnopqrstuvwxyz'
ran = lambda: ''.join(random.choices(chrs, k=4))
RND = ran()

SRC = conftest.src_path
ROGUE = 'Rogue.One.A.Star.Wars.Story.2016'

_4KHDR = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.BluRay.HDR.10-bit.x265-group.mp4')
_4KHDR_WEB = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.WEB-DL.HDR.10-bit.x265-group.mp4')
_4K = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.BluRay.x264-group.mp4')
_4K2 = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.BluRay.x264-other.mp4')
_4K_WEB = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.WEB-DL.x264-group.mp4')
_4K_HDTV = Film(SRC / RND / ROGUE / f'{ROGUE}.2160p.HDTV.x264-group.mp4')
_1080p = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.BluRay.x264-group.mkv')
_1080p2 = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.BluRay.x264-other.mkv')
_1080p_proper = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.PROPER.BluRay.x264-group.mkv')
_1080p_edition = Film(SRC / RND / ROGUE / f'{ROGUE}.Directors.Cut.1080p.BluRay.x264-group.mkv')
_1080p_WEB = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.WEB-DL.x264-group.mkv')
_1080p_HDTV = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.HDTV.x264-group.mkv')
_1080p_unknown = Film(SRC / RND / ROGUE / f'{ROGUE}.1080p.x264-group.mkv')
_720p = Film(SRC / RND / ROGUE / f'{ROGUE}.720p.BluRay.x264-group.mkv')
_720p_WEB = Film(SRC / RND / ROGUE / f'{ROGUE}.720p.WEB-DL.x264-group.mkv')
_720p_HDTV = Film(SRC / RND / ROGUE / f'{ROGUE}.720p.HDTV.x264-group.mkv')
_SD = Film(SRC / RND / ROGUE / f'{ROGUE}.BluRay.xvid-group.avi')
_SD_WEB = Film(SRC / RND / ROGUE / f'{ROGUE}.WEB-DL.xvid-group.avi')
_SD_HDTV = Film(SRC / RND / ROGUE / f'{ROGUE}.HDTV.xvid-group.avi')

class TestCompare:
    
    def test_4KHDR_vs_4k(self): 
        left = Make.mock_file(_4KHDR).main_file
        right = Make.mock_file(_4K).main_file
        assert(Compare.quality(left, right) == (Rt.DIFFERENT, Rn.HDR))
    
    def test_4KHDR_vs_1080p(self):
        left = Make.mock_file(_4KHDR).main_file
        right = Make.mock_file(_1080p).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_4K_vs_4k(self): 
        left = Make.mock_file(_4K, 10000).main_file
        right = Make.mock_file(_4K2, 5000).main_file
        left.size.refresh()
        right.size.refresh()
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.SIZE))
    
    def test_4K_vs_1080p(self): 
        left = Make.mock_file(_4K).main_file
        right = Make.mock_file(_1080p).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_4K_vs_720p(self): 
        left = Make.mock_file(_4K).main_file
        right = Make.mock_file(_720p).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_4K_vs_SD(self): 
        left = Make.mock_file(_4K).main_file
        right = Make.mock_file(_SD).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_1080p_vs_4K(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_4K).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_1080p_identical(self): 
        left = Make.mock_file(_1080p, 5000).main_file
        right = Make.mock_file(_1080p, 5000).main_file
        left.size.refresh()
        right.size.refresh()
        assert(Compare.quality(left, right) == (Rt.EQUAL, Rn.IDENTICAL))
    
    def test_1080p_vs_720p(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_720p).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_1080p_vs_SD(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_SD).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_720p_vs_4K(self): 
        left = Make.mock_file(_720p).main_file
        right = Make.mock_file(_4K).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_720p_vs_1080p(self): 
        left = Make.mock_file(_720p).main_file
        right = Make.mock_file(_1080p).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_720p_vs_SD(self): 
        left = Make.mock_file(_720p).main_file
        right = Make.mock_file(_SD).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_SD_vs_4K(self): 
        left = Make.mock_file(_SD).main_file
        right = Make.mock_file(_4K).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_SD_vs_1080p(self): 
        left = Make.mock_file(_SD).main_file
        right = Make.mock_file(_1080p).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_SD_vs_720p(self): 
        left = Make.mock_file(_SD).main_file
        right = Make.mock_file(_720p).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_bluray_vs_web(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_1080p_WEB).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.MEDIA))
    
    def test_bluray_vs_hdtv(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_1080p_HDTV).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.MEDIA))
    
    def test_bluray_vs_unknown(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_1080p_unknown).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.MEDIA))
    
    def test_web_vs_hdtv(self): 
        left = Make.mock_file(_1080p_WEB).main_file
        right = Make.mock_file(_1080p_HDTV).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.MEDIA))
    
    def test_web_vs_unknown(self): 
        left = Make.mock_file(_1080p_WEB).main_file
        right = Make.mock_file(_1080p_unknown).main_file
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.MEDIA))
    
    def test_different_editions(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_1080p_edition).main_file
        assert(Compare.quality(left, right) == (Rt.DIFFERENT, Rn.EDITION))
    
    def test_different_editions_ignore_off(self): 
        left = Make.mock_file(_1080p, 5000).main_file
        right = Make.mock_file(_1080p_edition, 10000).main_file
        config.duplicates.ignore_edition = True
        left.size.refresh()
        right.size.refresh()
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.SIZE))
    
    def test_proper(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(_1080p_proper).main_file
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.PROPER))
    
    def test_proper_vs_higher_quality(self): 
        left = Make.mock_file(_1080p_proper).main_file
        right = Make.mock_file(_4K).main_file
        left.is_proper = True
        assert(Compare.quality(left, right) == (Rt.LOWER, Rn.RESOLUTION))
    
    def test_proper_vs_lower_quality(self): 
        left = Make.mock_file(_1080p_proper).main_file
        right = Make.mock_file(_720p).main_file
        right.is_proper = True
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.RESOLUTION))
    
    def test_size(self): 
        left = Make.mock_file(_1080p, 10000).main_file
        right = Make.mock_file(_1080p2, 5000).main_file
        left.size.refresh()
        right.size.refresh()
        assert(Compare.quality(left, right) == (Rt.HIGHER, Rn.SIZE))
    
    def test_names_dont_match(self): 
        left = Make.mock_file(_1080p).main_file
        right = Make.mock_file(Film(SRC / 'Star.Trek.2009.1080p.Bluray.x264-group.mkv')).main_file
        assert(Compare.quality(left, right) == (Rt.NOT_COMPARABLE, Rn.NAME_MISMATCH))
        
        
