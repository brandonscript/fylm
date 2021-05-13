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

import re
import os
from pathlib import Path

import pytest

import fylmlib.config as config
import fylmlib.patterns as patterns
import fylmlib.tmdb as tmdb
import fylm
import conftest
from make import Make, GB, MB, KB
from fylmlib import Film
from fylmlib import Create
from fylmlib import IO
from fylmlib import TMDb
from fylmlib import Find
from fylmlib.tools import *
from fylmlib.enums import *

SRC = conftest.src_path
ALITA_SD = 'Alita.Battle.Angel.2019.HDTV.x264-NMaRE'
BTTF = 'Back.to.the.Future.Part.II.1989.1080p.BluRay.x264.DTS-HD'
JEDI = 'Last Jedi, The (2017) Bluray-1080p'
ROGUE_SD = 'Rogue.One.2016.HDTV.DVD.x264-group'
ROGUE_720 = 'Rogue.One.2016.720p.BluRay.DTS.x264-group'
ROGUE = 'Rogue.One.2016.1080p.BluRay.DTS.x264-group'
ROGUE_PROPER = 'Rogue.One.2016.1080p.BluRay.PROPER.DTS.x264-group'
ROGUE_4K = 'Rogue.One.2016.2160p.BluRay.HDR.10-bit.x265-group'
STARFIGHTER = 'The.Last.Starfighter.1984.1080p.BluRay.x264.DTS-HD/tls-score.mkv'
STARLORD = 'Starlord.2022.1080p/Starlord.mkv'
TTOP = '2001.A.Space.Odyssey.1968.1080p'
TTOP_WEB = '2001.A.Space.Odyssey.1968.1080p.WEB-DL'
ZELDA = 'Zelda.A.Link.To.The.Past.1991.1080p.Bluray.mkv'

class TestFilm(object):
    
    def test_init(self):
        
        Make.mock_file(SRC / ROGUE / f'{ROGUE}.mkv')
        
        film = Film(SRC / ROGUE)
        
        assert(film == Path(film))
        assert(film.origin == SRC / ROGUE)
        assert(film.src == SRC / ROGUE)
        
    def test_bad_files(self):
        rogue = Film(SRC / ROGUE)

        Make.mock_files(rogue / f'{ROGUE}.mkv',
                        rogue / f'{ROGUE}.sample.mkv',
                        rogue / f'{ROGUE}.nfo',
                        rogue / f'{ROGUE}.en.srt')

        assert(iterlen(rogue.bad_files) == 2)

    def test_dst(self):

        alita_sd = Film(SRC / ALITA_SD / f'{ALITA_SD}.avi')
        rogue720 = Film(SRC / ROGUE_720 / f'{ROGUE_720}.mkv')
        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue4k = Film(SRC / ROGUE_4K / f'{ROGUE_4K}.mp4')

        Make.mock_files(alita_sd, rogue720, rogue1080, rogue4k)

        TMDb.Search.parallel(alita_sd, rogue720, rogue1080, rogue4k)

        assert(alita_sd.dst == conftest.dst_paths['SD'] / 'Alita - Battle Angel (2019)')
        assert(rogue720.dst == conftest.dst_paths['720p'] / 'Rogue One - A Star Wars Story (2016)')
        assert(rogue1080.dst == conftest.dst_paths['1080p'] / 'Rogue One - A Star Wars Story (2016)')
        assert(rogue4k.dst == conftest.dst_paths['2160p'] / 'Rogue One - A Star Wars Story (2016)')
        
    def test_files(self):
        rogue = Film(SRC / ROGUE)
        
        Make.mock_files(rogue / f'{ROGUE}.mkv',
                        rogue / f'{ROGUE}.sample.mkv',
                        rogue / f'{ROGUE}.nfo',
                        rogue / f'{ROGUE}.en.srt')
        
        assert(iterlen(rogue.files) == 4)
        assert(all(type(f) == Film.File for f in rogue.files))
        assert(iterlen(rogue.files) == 4)

    def test_ignore_reason(self):

        unpack = SRC / f'_UNPACK_{ROGUE}/'
        sample = SRC / 'Test.File.sample.avi'
        string = SRC / 'Test.File.fylmignore.avi'
        tv = SRC / 'Test.Show.S01E12.mkv'
        bad_ext = SRC / 'Test.File.nfo'
        no_files = SRC / 'Test.Dir/note.txt'
        no_year = SRC / 'A.Great.File.1080p.mkv'
        small = SRC / 'Small.File.2003.1080p.mkv'
        tmdb = SRC / 'A.Wayward.Sword.1941.1080p.Bluray.x264.mkv'
        sys = SRC / '.DS_Store'
        sys_ea = SRC / '@eaDir/'

        Create.dirs(unpack)
        Make.mock_file(sample)
        Make.mock_file(string)
        Make.mock_file(tv)
        Make.mock_file(bad_ext)
        Make.mock_file(no_files)
        Make.mock_file(no_year)
        Make.mock_file(small, 2 * MB)
        Make.mock_file(tmdb)
        Make.mock_file(sys)
        Create.dirs(sys_ea)

        assert(Film(unpack).ignore_reason == IgnoreReason.UNPACKING)
        assert(Film(sample).ignore_reason == IgnoreReason.SAMPLE)
        assert(Film(string).ignore_reason == IgnoreReason.IGNORED_STRING)
        assert(Film(tv).ignore_reason == IgnoreReason.TV_SHOW)
        assert(Film('No.Spoon.1999/').ignore_reason ==
               IgnoreReason.DOES_NOT_EXIST)
        assert(Film(bad_ext).ignore_reason == IgnoreReason.INVALID_EXT)
        assert(Film(no_files.parent).ignore_reason ==
               IgnoreReason.NO_VIDEO_FILES)
        assert(Film(no_year).ignore_reason == IgnoreReason.UNKNOWN_YEAR)
        assert(Film(SRC / small).ignore_reason == IgnoreReason.TOO_SMALL)
        f = Film(SRC / tmdb)
        f.search_tmdb_sync()
        assert(f.ignore_reason == IgnoreReason.NO_TMDB_RESULTS)
        assert(Film(sys).ignore_reason == IgnoreReason.SYS)
        assert(Film(sys_ea).ignore_reason == IgnoreReason.SYS)

    def test_main_file(self):

        Make.mock_files(
            SRC / ROGUE / 'sith.txt',
            SRC / ROGUE / f'{ROGUE}.en.srt',
            SRC / ROGUE / f'{ROGUE}.mkv',
            SRC / ROGUE / f'{ROGUE}.sample.mkv'
        )

        film = Film(SRC / ROGUE)

        assert(film.main_file == SRC / ROGUE / f'{ROGUE}.mkv')

    def test_new_name(self):

        jedi = Film(SRC / JEDI / f'{JEDI}.mkv')
        rogue = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        starfighter = Film(SRC / STARFIGHTER)
        ttop = Film(SRC / TTOP / f'{TTOP}.mkv')

        Make.mock_files(jedi, rogue, starfighter, ttop)

        TMDb.Search.parallel(jedi, rogue, starfighter, ttop)

        assert(jedi.new_name == 'Star Wars - The Last Jedi (2017)')
        assert(rogue.new_name == 'Rogue One - A Star Wars Story (2016)')
        assert(starfighter.new_name == 'The Last Starfighter (1984)')
        assert(ttop.new_name == '2001 - A Space Odyssey (1968)')
        
    def test_origin(self):

        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')
        Make.mock_file(src)

        found = Find.deep(SRC)
        film = first((Film(f) for f in found), where=lambda x: x == SRC / ROGUE)

        assert(film.origin == SRC)
        assert(film.main_file.origin == SRC)

    def test_search_tmdb(self):
        # Covers film.tmdb and .tmdb_search()

        Make.mock_file(SRC / ROGUE / f'{ROGUE}.mkv')
        film = Film(SRC / ROGUE)
        assert(film == Path(film))

        film.search_tmdb_sync()

        assert(film.title == 'Rogue One: A Star Wars Story')
        assert(film.tmdb.new_title == film.title)
        assert(film.tmdb.id == 330459)
        assert(film.year == 2016)
        assert(film.tmdb.new_year == 2016)
        assert(film.new_name == 'Rogue One - A Star Wars Story (2016)')
        assert(film.tmdb.title_similarity == 0.5)
        assert(film.tmdb.overview)
        assert(film.tmdb.poster_url)
        assert(len(film.tmdb_matches) > 0)

    def test_should_ignore(self):

        unpack = SRC / f'_UNPACK_{ROGUE}/'
        Create.dirs(unpack)
        assert(Film(unpack).should_ignore)

        star = SRC / STARFIGHTER
        Make.mock_file(star)
        assert(not Film(star).should_ignore)

    def test_src(self):

        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')
        dst = Path(SRC / ROGUE / f'Rogue One.mkv')

        film = Film(SRC / ROGUE)
        Make.mock_file(src)

        assert(src.exists())
        assert(not dst.exists())
        film.search_tmdb_sync()
        IO.move(src, dst)
        assert(not src.exists())
        assert(dst.exists())

        # Ensure that even though we moved it, src didn't change
        assert film.src == SRC / ROGUE
    
    def test_title(self):
        
        Make.mock_files(
            SRC / JEDI / f'{JEDI}.mkv',
            SRC / ROGUE / f'{ROGUE}.mkv',
            SRC / STARFIGHTER
        )

        assert(Film(SRC / JEDI).title == 'The Last Jedi')
        assert(Film(SRC / ROGUE).title == 'Rogue One')
        assert(Film(SRC / STARFIGHTER).title == 'The Last Starfighter')
        
    def test_title_the(self):
               
        Make.mock_files(
            SRC / STARFIGHTER,
            SRC / JEDI / f'{JEDI}.mkv',
        )

        assert(Film(SRC / JEDI).title == 'The Last Jedi')
        assert(Film(SRC / STARFIGHTER).title == 'The Last Starfighter')
        assert(Film(SRC / JEDI).title_the == 'Last Jedi, The')
        assert(Film(SRC / STARFIGHTER).title_the == 'Last Starfighter, The')

    def test_tmdb_none(self):

        assert(type(Film(SRC / JEDI).tmdb).__name__ == 'Result')
        assert(not Film(SRC / JEDI).tmdb.id)
        
    def test_wanted_files(self):
        rogue = Film(SRC / ROGUE)

        Make.mock_files(rogue / f'{ROGUE}.mkv',
                        rogue / f'{ROGUE}.sample.mkv',
                        rogue / f'{ROGUE}.nfo',
                        rogue / f'Cover.jpg',
                        rogue / f'{ROGUE}.en.srt')

        assert(iterlen(rogue.wanted_files) == 2)
        
    def test_year(self):
                
        jedi = Film(SRC / JEDI / f'{JEDI}.mkv')
        rogue = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        starfighter = Film(SRC / STARFIGHTER)
        starlord = Film(SRC / STARLORD)
        string = Film(SRC / 'String.Theory.Documentary.mkv')
        ttop = Film(SRC / TTOP / f'{TTOP}.mkv')
        zelda = Film(SRC / ZELDA)
        
        Make.mock_files(jedi, rogue, starfighter, starlord, string, ttop, zelda)
        
        assert(jedi.year == 2017)
        assert(rogue.year == 2016)
        assert(starfighter.year == 1984)
        assert(starlord.year == 2022)
        assert(not string.year)
        assert(ttop.year == 1968)
        assert(zelda.year == 1991)
        
class TestFilmFile(object):

    def test_did_move(self):

        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')
        dst = Path(SRC / ROGUE / f'Rogue One.mkv')

        film = Film(SRC / ROGUE)
        Make.mock_file(src)

        assert(not film.main_file.did_move)
        assert(src.exists())
        assert(film.main_file == src)
        assert(film.main_file.src == src)
        film.main_file.move(dst)
        assert(not src.exists())
        assert(dst.exists())
        assert(film.main_file.did_move)
        assert(film.main_file == dst)
        assert(film.main_file.src == src)
    
    def test_dst(self):

        alita_sd = Film(SRC / ALITA_SD / f'{ALITA_SD}.avi')
        rogue720 = Film(SRC / ROGUE_720 / f'{ROGUE_720}.mkv')
        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue4k = Film(SRC / ROGUE_4K / f'{ROGUE_4K}.mp4')

        Make.mock_files(alita_sd, rogue720, rogue1080, rogue4k)

        TMDb.Search.parallel(alita_sd, rogue720, rogue1080, rogue4k)

        assert(alita_sd.main_file.dst == conftest.dst_paths['SD'] / 
               'Alita - Battle Angel (2019)' /
               'Alita - Battle Angel (2019) HDTV.avi')
        assert(rogue720.main_file.dst == conftest.dst_paths['720p'] / 
               'Rogue One - A Star Wars Story (2016)' /
               'Rogue One - A Star Wars Story (2016) Bluray-720p.mkv')
        assert(rogue1080.main_file.dst == conftest.dst_paths['1080p'] / 
               'Rogue One - A Star Wars Story (2016)' /
               'Rogue One - A Star Wars Story (2016) Bluray-1080p.mkv')
        assert(rogue4k.main_file.dst == conftest.dst_paths['2160p'] / 
               'Rogue One - A Star Wars Story (2016)' /
               'Rogue One - A Star Wars Story (2016) Bluray-2160p HDR.mp4')

    @pytest.mark.skip(reason="Covered by test_duplicates.py")
    def test_duplicate_action(self):
        pass

    def test_edition(self):

        starfighter = Film(SRC /
                           f'{Path(STARFIGHTER).parent}.25th.A.E.' /
                           Path(STARFIGHTER).name)
        Make.mock_files(starfighter)

        assert(starfighter.main_file.edition == '25th Anniversary Edition')

    def test_film(self):

        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')

        film = Film(SRC / ROGUE)
        Make.mock_file(src)

        assert(film.main_file.film == film)

    def test_hdr(self):

        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue4k = Film(SRC / ROGUE_4K / f'{ROGUE_4K}.mp4')

        Make.mock_files(rogue1080, rogue4k)

        assert(rogue4k.main_file.is_hdr)
        assert(not rogue1080.main_file.is_hdr)
        assert(rogue4k.main_file.hdr == 'HDR')
        assert(rogue1080.main_file.hdr == '')

    def test_ignore_reason(self):

        sample = SRC / 'Test.File.sample.avi'
        string = SRC / 'Test.File.fylmignore.avi'
        bad_ext = SRC / 'Test.File.nfo'
        small = SRC / 'Small.File.2003.1080p.mkv'
        sys = SRC / '.DS_Store'

        Make.mock_file(sample)
        Make.mock_file(string)
        Make.mock_file(bad_ext)
        Make.mock_file(small, 2 * MB)
        Make.mock_file(sys)

        assert(Film(sample).ignore_reason == IgnoreReason.SAMPLE)
        assert(Film(string).ignore_reason == IgnoreReason.IGNORED_STRING)
        assert(Film('No.Spoon.1999/').ignore_reason ==
               IgnoreReason.DOES_NOT_EXIST)
        assert(Film(bad_ext).ignore_reason == IgnoreReason.INVALID_EXT)
        assert(Film(SRC / small).ignore_reason == IgnoreReason.TOO_SMALL)
        assert(Film(sys).ignore_reason == IgnoreReason.SYS)

    @pytest.mark.skip(reason="Covered by test_duplicates.py")
    def test_is_duplicate(self):
        pass

    def test_is_subtitle(self):
        sub = Path(SRC / ROGUE / f'{ROGUE}.en.srt')
        mkv = Path(SRC / ROGUE / f'Rogue One.mkv')

        Make.mock_files(sub, mkv)

        assert(not first(Film(SRC / ROGUE).files).is_subtitle)
        assert(last(Film(SRC / ROGUE).files).is_subtitle)

    def test_is_wanted(self):

        good = SRC / ROGUE / f'{ROGUE}.mkv'
        bad_ext = SRC / 'Test.File.nfo'
        small = SRC / 'Small.File.2003.1080p.mkv'

        Make.mock_file(good)
        Make.mock_file(bad_ext)
        Make.mock_file(small, 2 * MB)

        assert(Film(good).main_file.is_wanted)
        assert(not Film(bad_ext).main_file.is_wanted)
        assert(not Film(SRC / small).main_file.is_wanted)

    def test_media(self):

        rogue_sd = Film(SRC / ROGUE_SD / f'{ROGUE_SD}.avi')
        rogue720 = Film(SRC / ROGUE_720 / f'{ROGUE_720}.mkv')
        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue4k = Film(SRC / ROGUE_4K / f'{ROGUE_4K}.mp4')
        ttop = Film(SRC / TTOP_WEB / f'{TTOP_WEB}.mkv')

        Make.mock_files(rogue_sd, rogue720, rogue1080, rogue4k, ttop)

        assert(rogue_sd.main_file.media == Media.HDTV)
        assert(rogue720.main_file.media == Media.BLURAY)
        assert(rogue1080.main_file.media == Media.BLURAY)
        assert(rogue4k.main_file.media == Media.BLURAY)
        assert(ttop.main_file.media == Media.WEBDL)
        
    @pytest.mark.skip(reason="Covered by test_did_move")
    def test_move(self):
        pass
    
    def test_origin(self):
        
        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')

        film = Film(SRC / ROGUE)
        Make.mock_file(src)

        assert(film.origin == SRC / ROGUE)
        assert(film.main_file.origin == SRC / ROGUE)

    def test_part(self):

        rogue = Film(SRC / ROGUE / f'{ROGUE}.Part.1.mkv')
        rogue2 = Film(SRC / ROGUE / f'{ROGUE}.Part.II.mkv')
        bttf = Film(SRC / BTTF / f'{BTTF}.mkv')
        Make.mock_files(rogue, rogue2, bttf)

        assert(rogue.main_file.part == '1')
        assert(rogue2.main_file.part == 'II')
        assert(not bttf.main_file.part)

    def test_proper(self):

        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue_proper = Film(SRC / ROGUE_PROPER / f'{ROGUE_PROPER}.mkv')

        Make.mock_files(rogue1080, rogue_proper)
        
        assert(rogue_proper.main_file.is_proper)
        assert(not rogue1080.main_file.is_proper)

    def test_resolution(self):

        rogue_sd = Film(SRC / ROGUE_SD / f'{ROGUE_SD}.avi')
        rogue720 = Film(SRC / ROGUE_720 / f'{ROGUE_720}.mkv')
        rogue1080 = Film(SRC / ROGUE / f'{ROGUE}.mkv')
        rogue4k = Film(SRC / ROGUE_4K / f'{ROGUE_4K}.mp4')

        Make.mock_files(rogue_sd, rogue720, rogue1080, rogue4k)

        assert(rogue_sd.main_file.resolution == Resolution.UNKNOWN)
        assert(rogue720.main_file.resolution == Resolution.HD_720P)
        assert(rogue1080.main_file.resolution == Resolution.HD_1080P)
        assert(rogue4k.main_file.resolution == Resolution.UHD_2160P)

    def test_src(self):

        src = Path(SRC / ROGUE / f'{ROGUE}.mkv')
        dst = Path(SRC / ROGUE / f'Rogue One.mkv')

        film = Film(SRC / ROGUE)
        Make.mock_file(src)

        assert(src.exists())
        assert(not dst.exists())
        assert(film.main_file.src == src)
        IO.move(src, dst)
        assert(not src.exists())
        assert(dst.exists())

        # Ensure that even though we moved it, src didn't change
        assert film.main_file.src == src
    
    @pytest.mark.skip(reason="Covered by test_duplicates.py")
    def test_upgrade_reason(self):
        pass
