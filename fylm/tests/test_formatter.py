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
import time
from multiprocessing import Process, Pipe

import pytest

import fylmlib.config as config
from fylmlib import Film, IO, Find
import conftest
from make import Make

# def async_safe_copy(conn, *args):
#     copy = ops.fileops.safe_move(*args)
#     conn.send(copy)
#     conn.close()

SRC = conftest.src_path
DST = conftest.dst_paths
NEW_GIRL = 'The.Girl.Who.Kicked.The.Hornets.Nest.2009.Part.2.1080p.BluRay.x264-group'
MOVED_GIRL = 'The Girl Who Kicked The Hornets Nest (2009)'
NEW_ROGUE = 'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON'
NEW_ROGUE_PROPER = 'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.DTS.x264-DON'
NEW_ROGUE_4KHDR = 'Rogue.One.A.Star.Wars.Story.2016.HDR.10-bit.2160p.BluRay.DTS.x265-AMiABLE'
NEW_ROGUE_4KHDR_BADBRACKET = 'Rogue.One.A.Star.Wars.Story.2016.(2160p BluRay x265 HEVC 10bit HDR AAC 7.1 Tigole)'
MOVED_ROGUE = 'Rogue One A Star Wars Story (2016)'
NEW_TTSF = 'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy'
NEW_TTSF_PROPER = 'the.last.starfighter.25th.anniversary.ed.1984.PROPER.1080p.bluray.x264.dts-hd 5.1-lazy'
MOVED_TTSF = 'The Last Starfighter (1984)'

class TestFormat(object):

    def test_title_case(self):

        # Placeholder
        # s = "stAr waRs ePISOde vi a new hope and a tauntaun"
        # Nausicaä of the Valley of the Wind
        # ['Face:off']
        # ['Face-off']
        # Somethign with &
        # WALL E
        # The Good Bad, & the Ugly
        # Mack the Knife
        # Kingsman the Golden Circle
        # Crush the Skull
        # Rogue One A Star Wars Story
        # Harry Potter 1 and the Philospher's Stone
        # The Chronicles of Narnia 1 The Lion Witch and the Wardrobe
        # V for Vendetta
        # This Should:Only capitalize the letter if it is not an-the article
        # The Chronicles of Narnia The Lion, the Witch and the Wardrobe
        # 'S.W.A.T.' not S.W..T

        # Test dot replace
        # 'L A'
        # 'L.A.'
        # 'L A '
        # 'L A Confidential'
        # 'L.A.Confidential'
        # 'Liar Liar'
        # 'Liar'
        # 'S W A T'
        # 'S.W.A.T.'
        # 'S W A T '

        return

    def test_title_year(self):

        src = SRC / f'{NEW_ROGUE}/{NEW_ROGUE}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE}.mkv'

        config.rename_pattern.file = r'{title} {(year)}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_the_year(self):

        src = SRC / f'{NEW_TTSF}/{NEW_TTSF}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'Last Starfighter, The (1984)/Last Starfighter, The (1984).mkv'

        config.rename_pattern.file = r'{title-the} {(year)}'
        config.rename_pattern.folder = r'{title-the} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_year_hyphen_edition(self):

        src = SRC / f'{NEW_TTSF}/{NEW_TTSF}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_TTSF}/{MOVED_TTSF} - 25th Anniversary Edition.mkv'

        config.rename_pattern.file = r'{title} {(year)}{ - edition}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_year_sqbk_edition(self):

        src = SRC / f'{NEW_TTSF}/{NEW_TTSF}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_TTSF}/{MOVED_TTSF} [25th Anniversary Edition].mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    

    def test_title_year_sqbk_edition_quality_full(self):

        src = SRC / f'{NEW_TTSF_PROPER}/{NEW_TTSF_PROPER}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_TTSF}/{MOVED_TTSF} [25th Anniversary Edition] Bluray-1080p Proper.mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_year_noedition_quality(self):

        src = SRC / f'{NEW_ROGUE}/{NEW_ROGUE}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE} Bluray-1080p.mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_year_noedition_quality_full(self):

        src = SRC / f'{NEW_ROGUE}/{NEW_ROGUE}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE} Bluray-1080p Proper.mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_folder_title_year_quality_full_proper(self):

        src = SRC / f'{NEW_ROGUE}/{NEW_ROGUE}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_ROGUE} Bluray-1080p Proper/{MOVED_ROGUE} Bluray-1080p Proper.mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)} {[edition]} {quality-full}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_hdr(self):

        src = SRC / f'{NEW_ROGUE_4KHDR}/{NEW_ROGUE_4KHDR}.mp4'

        Make.mock_file(src)

        expect = DST['2160p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE} Bluray-2160p HDR.mp4'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_bad_bracket(self):

        src = SRC / f'{NEW_ROGUE_4KHDR_BADBRACKET}/{NEW_ROGUE_4KHDR_BADBRACKET}.mp4'

        Make.mock_file(src)

        expect = DST['2160p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE} Bluray-2160p HDR.mp4'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_title_year_unknown_media(self):

        src = SRC / f'{NEW_ROGUE_PROPER}/{NEW_ROGUE_PROPER}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_ROGUE}/{MOVED_ROGUE} 1080p Proper.mkv'

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()
        
        assert(film.main_file.did_move)
        assert expect.exists()

    def test_part(self):
        src = SRC / f'{NEW_GIRL}/{NEW_GIRL}.mkv'

        Make.mock_file(src)

        expect = DST['1080p'] / f'{MOVED_GIRL}/{MOVED_GIRL}, Part 2 Bluray-1080p.mkv'

        config.rename_pattern.file = r'{title} {(year)} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        film.main_file.move()

        assert(film.main_file.did_move)
        assert expect.exists()

