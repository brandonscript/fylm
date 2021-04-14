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
import fylmlib.operations as ops
from fylmlib.processor import _QueuedMoveOperation as move
from fylmlib.film import Film
import conftest
import make

def async_safe_copy(conn, *args):
    copy = ops.fileops.safe_move(*args)
    conn.send(copy)
    conn.close()

def do_every(src):
    conftest.cleanup_all()
    conftest.make_empty_dirs()
    make.make_mock_file(src, 7354 * make.mb)
    config.safe_copy = False
    config.test = False

# @pytest.mark.skip()
class TestFormatter(object):

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

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016).mkv')

        config.rename_pattern.file = r'{title} {(year)}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_the_year(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Last Starfighter, The (1984)/Last Starfighter, The (1984).mkv')

        config.rename_pattern.file = r'{title-the} {(year)}'
        config.rename_pattern.folder = r'{title-the} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_year_hyphen_edition(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/The Last Starfighter (1984) - 25th Anniversary Edition.mkv')

        config.rename_pattern.file = r'{title} {(year)}{ - edition}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_year_sqbk_edition(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/The Last Starfighter (1984) [25th Anniversary Edition].mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    

    def test_title_year_sqbk_edition_quality_full(self):

        src = os.path.join(
        conftest.films_src_path,
        'the.last.starfighter.25th.anniversary.ed.1984.PROPER.1080p.bluray.x264.dts-hd 5.1-lazy/the.last.starfighter.25th.anniversary.ed.1984.PROPER.1080p.bluray.x264.dts-hd 5.1-lazy.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'The Last Starfighter (1984)/The Last Starfighter (1984) [25th Anniversary Edition] Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_year_noedition_quality(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-1080p.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_year_noedition_quality_full(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_folder_title_year_quality_full_proper(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.BluRay.DTS.x264-DON.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016) Bluray-1080p Proper/Rogue One A Star Wars Story (2016) Bluray-1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)} {[edition]} {quality-full}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_hdr(self):

        src = os.path.join(
        conftest.films_src_path,
            'Rogue.One.A.Star.Wars.Story.2016.HDR.10-bit.2160p.BluRay.DTS.x265-AMiABLE/Rogue.One.A.Star.Wars.Story.2016.2160p.Bluray.HDR.10bit.x265.DTS-HD.7.1-AMiABLE.mp4')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['2160p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-2160p HDR.mp4')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_bad_bracket(self):

        src = os.path.join(
            conftest.films_src_path,
            'Rogue.One.A.Star.Wars.Story.2016.(2160p BluRay x265 HEVC 10bit HDR AAC 7.1 Tigole)/Rogue.One.A.Star.Wars.Story.2016.(2160p BluRay x265 HEVC 10bit HDR AAC 7.1 Tigole).mp4')

        do_every(src)

        expect = os.path.join(
            conftest.films_dst_paths['2160p'],
            'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) Bluray-2160p HDR.mp4')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))

    def test_title_year_unknown_media(self):

        src = os.path.join(
        conftest.films_src_path,
        'Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.DTS.x264-DON/Rogue.One.A.Star.Wars.Story.2016.PROPER.1080p.DTS.x264-DON.mkv')

        do_every(src)

        expect = os.path.join(
        conftest.films_dst_paths['1080p'], 
        'Rogue One A Star Wars Story (2016)/Rogue One A Star Wars Story (2016) 1080p Proper.mkv')

        config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full}'
        config.rename_pattern.folder = r'{title} {(year)}'

        film = Film(src)
        result = move(film.all_valid_files[0]).do()
        
        assert(result is True)
        assert(os.path.exists(expect))
