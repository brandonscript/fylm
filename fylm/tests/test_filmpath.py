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
import sys
from timeit import default_timer as timer
import contextlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

import pytest

import fylmlib.config as config
from fylmlib.operations import *
from fylmlib.tools import *
from fylmlib.enums import *
from fylmlib import FilmPath, Film
import conftest
import fylm
from make import Make, GB, MB, KB

# Travis override for mini file sizes
# Multipy any size measurement by T to get an actual size
T = 1024 if os.environ.get('TRAVIS') else 1


def is_alphabetical_name(l: [Path]):
    return all(l[i].name.lower() <= l[i+1].name.lower()
               for i in range(len(l)-1))


SRC = conftest.src_path
SRC2 = conftest.src_path2
DST = conftest.dst_paths

AMC = "A Monster Calls-1080p/amc.mkv"
ALITA = 'Alita.Battle.Angel.2019.BluRay.1080p.x264-NMaRE'
ALITA_DST = f'Alita Battle Angel (2019) Bluray-1080p/'\
            f'Alita Battle Angel (2019) Bluray-1080p.mkv'
ATMITW = 'All.the.Money.in.the.World.2017.BluRay.1080p.x264-NMaRE'
AVATAR = 'Avatar.2009.BluRay.2160p.HDR.x265-xWinG'
DEEP = '#deep'
ROGUE = 'Rogue.One.2016.1080p.BluRay.DTS.x264-group'
ROGUE_4K = 'Rogue.One.A.Star.Wars.Story.2016.4K.BluRay.HDR.10bit.DTS.HD.MA-PlUSh.mp4'
ROGUE_4K2 = 'Rogue.One.A.Star.Wars.Story.4K.HDR.10bit.BT2020.Chroma.422.Edition.DTS.HD.MA-VISIONPLUSHDR1000.mp4'
STARLORD = 'Starlord.2022.1080p/Starlord.mkv'
TTOP = '2001.A.Space.Odyssey.1968.1080p'
TTOP_NO_YEAR = '2001.A.Space.odyssey.1080p.BluRay.x264.anoXmous'
ZELDA = 'Zelda.A.Link.To.The.Past.1991.1080p.Bluray.mkv'
ZORG = 'Zorg.2.1989.1080p.Bluray.mkv'

class TestFilmPath(object):

    # Init

    def test_init(self):

        fp = FilmPath('/') / STARLORD
        assert(fp)
        assert(fp.name == 'Starlord.mkv')
        assert(fp.stem == 'Starlord')
        assert(fp.suffix == '.mkv')

    def test_init_from_pathlib_path(self):
        fp = FilmPath(SRC / STARLORD)
        assert(fp)
        assert(fp == Path(fp))

    def test_init_with_origin(self):
        fp = FilmPath(SRC / STARLORD, origin=FilmPath(SRC))
        assert(fp)
        assert(fp == Path(fp))
        assert(fp.origin == SRC)

    def test_init_without_origin(self):
        fp = FilmPath(SRC / ALITA)
        assert(fp == Path(fp))
        assert(fp.origin == SRC / ALITA)

    def test_init_by_slash_operator(self):
        fp1 = FilmPath(SRC) / ALITA
        assert(fp1.origin == SRC)
        fp2 = FilmPath(SRC / ALITA)
        assert(fp2.origin == SRC / ALITA)
        assert(FilmPath(SRC) / ALITA).origin == SRC

    def test_init_by_comma_operator(self):
        fp1 = FilmPath(SRC, ALITA)
        assert(fp1.origin == SRC / ALITA)
        assert(FilmPath(SRC, ALITA).origin == SRC / ALITA)

    def test_init_with_dirs(self):

        Make.all_mock_files()

        dirs = [d for d in SRC.iterdir() if d.is_dir()]
        fp = FilmPath(SRC, dirs=dirs)
        assert(fp)
        assert(len(fp.dirs) == 59)

    def test_init_with_files(self):

        Make.all_mock_files()

        files = [d for d in SRC.iterdir() if d.is_file()
                 and not is_sys_file(d)]
        fp = FilmPath(SRC, files=files)
        assert(fp)
        assert(len(fp.files) == 65)

    # Internal

    def test_init_from_kwargs(self):

        alita = FilmPath((SRC / ALITA / f'{ALITA}.mkv'), origin=SRC)

        args = {**{'_parts': alita._parts}, **alita.__dict__}
        clone = FilmPath._from_kwargs(tuple(args.items()))

        assert(clone == alita)
        assert(clone.origin == SRC)

    def test_pickle(self):
        fp = FilmPath(SRC / STARLORD,
                      origin=FilmPath(SRC))
        d = pickle.dumps(fp)
        r = pickle.loads(d)
        assert(fp == r)
        assert(fp.origin == r.origin)

    # Overrides

    def test_joinpath(self):

        ttop = FilmPath(SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv', origin=SRC)
        Make.mock_file(ttop)

        test = ttop.parent.joinpath(f'{TTOP_NO_YEAR}.mkv')
        assert(test == SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv')
        assert(test.origin == SRC)

        fp = FilmPath(SRC)
        assert(fp == SRC)
        fp.origin = '/'
        assert(type(fp.origin) is type(Path()))
        assert(fp.origin == Path('/'))
        j = fp.joinpath(STARLORD)
        assert(j == SRC / STARLORD)
        assert(type(fp.origin) is type(Path()))
        assert(fp.origin == Path('/'))

    def test_parent(self):
        fp = FilmPath(SRC / STARLORD,
                      origin=FilmPath(SRC))
        assert(fp.parent.origin == SRC)
        assert(fp.parent == Path(SRC) / Path(STARLORD).parent.name)

    def test_parents(self):
        assert(len(FilmPath(SRC / STARLORD).parents)
               == len(Path(SRC / STARLORD).parents))
        for p in FilmPath(SRC / STARLORD).parents:
            assert(p.origin)

    def test_relative_to(self):
        fp = FilmPath(SRC / STARLORD,
                      origin=FilmPath(SRC))
        assert(fp.relative_to(SRC) == Path(STARLORD))
        assert(fp.relative_to(SRC).origin)

    # Attributes

    def test_origin(self):

        ttop = FilmPath(SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv', origin=SRC)
        Make.mock_file(ttop)
        assert(ttop == SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv')
        assert(ttop.origin == SRC)

        conftest.cleanup_all()

        Make.all_mock_files()
        found = Find.deep(SRC)
        for f in found:
            assert(f.origin == SRC)

    def test_branch(self):

        files = [ALITA, ATMITW]

        # Make files in alternate path
        for name in files:
            Make.mock_files((SRC / name / name).with_suffix('.mkv'))

        Make.mock_files(SRC / DEEP / ZELDA)
        Make.mock_files(SRC / DEEP / ZORG)

        found = Find.new(SRC, sort_key=lambda x: str(x).lower())

        for i in range(3, 7):
            assert(found[i].branch == SRC)

        assert(found[1].branch == SRC / DEEP)
        assert(found[2].branch == SRC / DEEP)

        Make.mock_files(FilmPath(SRC / ALITA / f'{ALITA}.mkv'))
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        assert(alita.branch == SRC)

        zelda = FilmPath(SRC) / DEEP / ZELDA
        assert(zelda.branch == SRC / DEEP)

    def test_descendents(self):
        zelda = FilmPath(SRC / DEEP / ZELDA)
        zorg = FilmPath(SRC / DEEP / ZORG)
        Make.mock_files(zelda, zorg)

        deep = FilmPath(SRC / DEEP)
        assert(len(list(deep.descendents)) == 2)

        for d in list(deep.descendents):
            assert d.name == ZELDA or d.name == ZORG
        assert(zelda.branch == SRC / DEEP)
        assert(zorg.branch == SRC / DEEP)

    def test_dirs(self):

        Make.all_mock_files()

        found = list(Find.shallow(SRC))
        dirs = list(filter(lambda x: x.is_dir(), found))

        assert(FilmPath(SRC).dirs)
        assert(len(FilmPath(SRC).dirs) == len(dirs))

    def test_dirs_if_file(self):
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        Make.mock_file(alita)
        assert(not alita.dirs)

    def test_files(self):
        Make.all_mock_files()

        found = list(Find.shallow(SRC))
        files = list(filter(lambda x: x.is_file() and not x == SRC, found))

        assert(FilmPath(SRC).files)
        assert(len(FilmPath(SRC).files) == len(files))

    def test_files_if_file(self):

        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        Make.mock_file(alita)
        assert(not alita.files)

    def test_filmrel(self):

        assert(FilmPath(STARLORD).filmrel == Path(STARLORD))

        amc = FilmPath(SRC / AMC)
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        ttop = FilmPath((SRC / DEEP / TTOP / TTOP).with_suffix('.mkv'))
        zelda = FilmPath(SRC / ZELDA)

        Create.dirs(avatar, empty)
        Make.mock_files(amc,
                        alita,
                        atmitw,
                        notes,
                        starlord,
                        ttop,
                        zelda)

        assert(amc.parent.is_filmroot)
        assert(not amc.is_filmroot)
        assert(amc.filmrel == Path(amc.parent.name) / Path(amc.name))
        assert(amc.parent.filmrel == Path(amc.parent.name) / Path(amc.name))
        assert(not FilmPath(SRC).filmrel)
        assert(alita.filmrel == Path(ALITA) / Path(f'{ALITA}.mkv'))
        assert(alita.parent.filmrel == Path(ALITA))
        assert(atmitw.filmrel == Path(ATMITW) /
               Path(ATMITW).with_suffix('.mkv'))
        assert(atmitw.parent.filmrel == Path(ATMITW))
        assert(avatar.filmrel == Path(AVATAR))
        assert(not empty.filmrel)
        assert(not notes.filmrel)
        assert(starlord.filmrel == Path(STARLORD))
        assert(ttop.filmrel == Path(TTOP) / Path(TTOP).with_suffix('.mkv'))
        assert(zelda.filmrel == Path(ZELDA))

    def test_filmroot(self):

        rogue = FilmPath(SRC / '#4K' / ROGUE_4K)
        rogue2 = FilmPath(SRC / ROGUE_4K2)

        Make.mock_files(rogue, rogue2)
        found = sorted(filter(lambda f: f.is_filmroot, Find.deep(SRC)))
        assert(len(found) == 2)
        assert(found[0] == rogue)
        assert(found[1] == rogue2)
        assert(found[0].filmroot == rogue)
        assert(not found[0].parent.is_filmroot)
        assert(found[1].filmroot == rogue2)

        conftest.cleanup_all()

        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        ttop = FilmPath((SRC / DEEP / TTOP / TTOP).with_suffix('.mkv'))
        ttop_ny = FilmPath(SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv')
        zelda = FilmPath(SRC / ZELDA)

        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        atmitw,
                        notes,
                        starlord,
                        ttop,
                        ttop_ny,
                        zelda)

        assert(not FilmPath(SRC).filmroot)
        assert(alita.filmroot == SRC / ALITA)
        assert(alita.parent.filmroot == SRC / ALITA)
        assert(atmitw.filmroot == SRC / ATMITW)
        assert(atmitw.parent.filmroot == SRC / ATMITW)
        assert(not avatar.filmroot)
        assert(not empty.filmroot)
        assert(not notes.filmroot)
        assert(starlord.filmroot == starlord.parent)
        assert(ttop.filmroot == ttop.parent)
        assert(ttop_ny.parent.filmroot == ttop_ny.parent)
        assert(ttop_ny.filmroot == ttop_ny.parent)
        assert(zelda.filmroot == zelda)

    def test_is_empty(self):

        files = [
            'Yates/Abby.mkv',
            'Yates/Gilbert/Erin.mkv',
            'Yates/Gilbert/Holtzmann/Jillian.mkv',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.mkv',
            'Yates/Thumbs.db',
            'Roman/Nancy_Grace.mkv',
            'Roman/Hamilton/Margaret.mkv',
            'Roman/Hamilton/Ride/Sally.mkv',
            'Roman/Hamilton/Ride/Jemison/Mae.mkv',
            'Roman/.DS_Store'
        ]

        for f in files:
            Make.mock_file(SRC / f)

        Create.dirs(SRC / 'Guinn',
                    SRC / 'Freese',
                    SRC / 'Wu' / 'Vera')

        assert(not FilmPath(SRC / 'Yates').is_empty)
        assert(not FilmPath(SRC / 'Yates/Gilbert').is_empty)
        assert(not FilmPath(SRC / 'Yates/Gilbert/Holtzmann').is_empty)
        assert(not FilmPath(SRC / 'Yates/Gilbert/Holtzmann/Tolan').is_empty)
        assert(not FilmPath(SRC / 'Roman').is_empty)
        assert(not FilmPath(SRC / 'Roman/Hamilton').is_empty)
        assert(not FilmPath(SRC / 'Roman/Hamilton/Ride').is_empty)
        assert(not FilmPath(SRC / 'Roman/Hamilton/Ride/Jemison').is_empty)
        assert(not FilmPath(SRC / 'Wu').is_empty)
        assert(FilmPath(SRC / 'Guinn').is_empty)
        assert(FilmPath(SRC / 'Freese').is_empty)
        assert(FilmPath(SRC / 'Wu' / 'Vera').is_empty)

    @pytest.mark.xfail(raises=NotADirectoryError)
    def test_is_empty_file(self):

        Make.mock_file(SRC / 'Yates/Abby.mkv')
        assert(FilmPath(SRC / 'Yates/Abby.mkv').is_empty)

    def test_is_origin(self):

        Make.all_mock_files()
        found = Find.deep(SRC)
        for f in found:
            assert(f != SRC and not f.is_origin and f.origin == SRC)

    def test_is_branch(self):

        Make.all_mock_files()
        found = Find.deep(SRC)
        for f in found:
            if f == SRC:
                assert(f.is_branch)
            elif f == SRC / '#4K':
                assert(f.is_branch)
            elif f == SRC / '#4K' / DEEP:
                assert(f.is_branch)
            else:
                assert(not f.is_branch)

    def test_is_filmroot(self):

        # Test a completely unknown file
        unknown = FilmPath(SRC / 'tl-lk.1080p.mkv', origin=SRC)
        Make.mock_file(unknown)
        assert(unknown.is_filmroot)

        conftest.cleanup_all()

        # Test a good file with no year
        ttop = FilmPath(SRC / TTOP_NO_YEAR / f'{TTOP_NO_YEAR}.mkv')
        Make.mock_file(ttop)
        assert(not ttop.is_filmroot)
        assert(ttop.parent.is_filmroot)

        conftest.cleanup_all()

        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        zelda = FilmPath(SRC / ZELDA)

        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        atmitw,
                        notes,
                        starlord,
                        zelda)

        assert(not FilmPath(SRC).is_filmroot)
        assert(not FilmPath(SRC / '#4K').is_filmroot)
        assert(not FilmPath(SRC / DEEP).is_filmroot)
        assert(not alita.is_filmroot)
        assert(alita.parent.is_filmroot)
        assert(not atmitw.is_filmroot)
        assert(atmitw.parent.is_filmroot)
        assert(not avatar.is_filmroot)  # empty
        assert(not avatar.parent.is_filmroot)
        assert(not empty.is_filmroot)
        assert(not empty.parent.is_filmroot)
        assert(not notes.is_filmroot)
        assert(not notes.parent.is_filmroot)
        assert(not starlord.is_filmroot)
        assert(starlord.parent.is_filmroot)
        assert(zelda.is_filmroot)
        assert(not zelda.parent.is_filmroot)

    def test_is_terminus(self):

        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        alita4k = FilmPath((SRC / '#4K' / f'{ALITA}.mkv'))
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        zelda = FilmPath(SRC / ZELDA)

        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        alita4k,
                        atmitw,
                        notes,
                        starlord,
                        zelda)

        assert(not FilmPath(SRC).is_terminus)
        assert(alita.is_terminus)
        assert(alita.parent.is_terminus)
        assert(avatar.is_terminus)
        assert(FilmPath(SRC / '#4K').is_terminus)
        assert(empty.is_terminus)
        assert(notes.is_terminus)
        assert(FilmPath(SRC / '#notes').is_terminus)
        assert(FilmPath(SRC / DEEP / STARLORD).is_terminus)
        assert(FilmPath(SRC / DEEP / STARLORD).parent.is_terminus)

    def test_is_video_file(self):

        assert(not FilmPath(SRC / '#notes' / 'my_note.txt').is_video_file)
        assert(not FilmPath(SRC / '#notes').is_video_file)
        assert(FilmPath(SRC / STARLORD).is_video_file)
        assert(FilmPath(SRC / ALITA / f'{ALITA}.mkv').is_video_file)
        assert(FilmPath((Path(ALITA) / f'{ALITA}.mkv')).is_video_file)

    def test_has_ignored_string(self):
        config.ignore_strings.extend(['sample', '@eaDir', '_UNPACK_'])
        assert(not FilmPath(
            'dir/A.File.1080p.bluray.x264-scene.mkv').has_ignored_string)
        assert(FilmPath('sample').has_ignored_string)
        assert(FilmPath('A.File.1080p.bluray.x264-scene.sample.mkv').has_ignored_string)
        assert(FilmPath('SaMpLe').has_ignored_string)
        assert(FilmPath('@eaDir').has_ignored_string)
        assert(FilmPath('@EAdir').has_ignored_string)
        assert(FilmPath('_UNPACK_a.file.named.something').has_ignored_string)
        assert(FilmPath('_unpack_a.file.named.something').has_ignored_string)

    def test_has_valid_ext(self):

        files = [
            'Test.File.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo',
            'Test.File.jpg',
        ]

        for f in files:
            Make.mock_file(SRC / f)

        assert(FilmPath(SRC / files[0]).has_valid_ext)
        assert(FilmPath(SRC / files[1]).has_valid_ext)
        assert(FilmPath(SRC / files[2]).has_valid_ext)
        assert(FilmPath(SRC / files[3]).has_valid_ext)
        assert(not FilmPath(SRC / files[4]).has_valid_ext)
        assert(not FilmPath(SRC / files[5]).has_valid_ext)

    def test_maybe_film(self):

        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        ttop = FilmPath((SRC / DEEP / TTOP / TTOP).with_suffix('.mkv'))
        zelda = FilmPath(SRC / ZELDA)
        zorg = FilmPath(SRC / ZORG)

        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        atmitw,
                        notes,
                        starlord,
                        ttop,
                        zelda,
                        zorg)

        # assert(not FilmPath(SRC).maybe_film)
        # assert(not FilmPath(SRC / '#4K').maybe_film)
        # assert(not FilmPath(SRC / DEEP).maybe_film)
        # assert(alita.maybe_film)
        # assert(alita.parent.maybe_film)
        assert(FilmPath(SRC / ALITA).maybe_film)
        assert(atmitw.maybe_film)
        assert(atmitw.parent.maybe_film)
        assert(not avatar.maybe_film)
        assert(not avatar.parent.maybe_film)
        assert(not empty.maybe_film)
        assert(not notes.maybe_film)
        assert(not notes.parent.maybe_film)
        assert(starlord.maybe_film)
        assert(starlord.parent.maybe_film)
        assert(ttop.maybe_film)
        assert(ttop.parent.maybe_film)
        assert(not ttop.parent.parent.maybe_film)
        assert(zelda.maybe_film)
        assert(not zelda.parent.maybe_film)
        assert(zorg.maybe_film)
        assert(not zorg.parent.maybe_film)

    def test_setpath(self):
        p = FilmPath(SRC / STARLORD)
        assert(p == SRC / STARLORD)
        assert(str(p) == str(SRC / STARLORD))
        p.setpath(FilmPath(SRC / ALITA / f'{ALITA}.mkv'))
        assert(p == SRC / ALITA / f'{ALITA}.mkv')
        assert(str(p) == str(SRC / ALITA / f'{ALITA}.mkv'))

    def test_siblings(self):

        files = [
            FilmPath(ALITA) / Path(f'{ALITA}.mkv'),
            FilmPath(ATMITW) / Path(ATMITW).with_suffix('.mkv'),
            FilmPath(ATMITW) / STARLORD,
            FilmPath(ATMITW) / Path(f'{ALITA}.mkv'),
            FilmPath(ATMITW) / ZELDA,
            FilmPath(ATMITW) / ZORG,
        ]

        for f in files:
            Make.mock_file(SRC / f)

        assert(iterlen((FilmPath(SRC) / ALITA).siblings) == 1)
        assert(first((FilmPath(SRC) / ALITA).siblings) == SRC / ATMITW)
        assert(iterlen((FilmPath(SRC / ATMITW / STARLORD).parent).siblings) == 4)
        assert(iterlen(FilmPath(SRC / ATMITW / STARLORD).siblings) == 0)
        assert(iterlen(FilmPath(SRC / ATMITW / ZORG).siblings) == 4)

    @pytest.mark.xfail(raises=ValueError)
    def test_siblings_not_abs(self):

        assert(iterlen(FilmPath(ALITA).siblings) == 1)

    def test_size(self):

        files = [
            (SRC / 'Test/Test.File.mkv', 10 * MB),
            (SRC / 'Test/Test.File2.mkv', 21 * MB),
            (SRC / 'Test/Test.File3.mkv', 8 * MB),
            (SRC / 'Test/Test.File.jpg', 15 * KB),
            (SRC / 'Test/Test.File.avi', 2 * MB)
        ]

        for f in files:
            Make.mock_file(f[0], f[1])

        # Assert file size matches definition
        for f in files:
            assert(abs(FilmPath(f[0]).size.value - f[1]) == 0)

        # Assert dir is at least the size of the file, probably larger
        # because the folder itself takes up some space. Diff of 1 byte.

        # Test multiple files in dir to diff of 3 bytes
        assert(abs(FilmPath(SRC / 'Test').size.value -
               sum(s for (_, s) in files) == 0))

    def test_size_cache(self):

        files = [
            (SRC / 'Test/Test.File.mkv', 10 * MB),
            (SRC / 'Test/Test.File2.mkv', 21 * MB),
            (SRC / 'Test/Test.File3.mkv', 8 * MB),
            (SRC / 'Test/Test.File.jpg', 15 * KB),
            (SRC / 'Test/Test.File.avi', 2 * MB)
        ]

        for f in files:
            Make.mock_file(f[0], f[1])

        # Assert file size matches definition
        for f in files:
            assert(abs(FilmPath(f[0]).size.value - f[1]) == 0)

        # Assert dir is at least the size of the file, probably larger
        # because the folder itself takes up some space. Diff of 1 byte.

        test = FilmPath(SRC / 'Test')

        # Test multiple files in dir to diff of 3 bytes
        assert(abs(test.size.value - sum(s for (_, s) in files) == 0))

        Delete.dir(SRC / 'Test')

        # Test the cached size, even after deleted
        assert(abs(test.size.value - sum(s for (_, s) in files) == 0))

    def test_video_files(self):

        files = [
            ALITA + '.mkv',
            ALITA + '.avi',
            ALITA + '.mp4',
            ALITA + '.nfo',
            'Thumbs.db',
            ALITA + '.srt',
            'Margaret/Margaret-2160p.mp4',
            'Sally.txt',
            '.DS_Store'
        ]

        for f in files:
            Make.mock_file(SRC / ALITA / f)

        assert(iterlen(FilmPath(SRC / ALITA).video_files) == 4)

    def test_year(self):

        assert(FilmPath(ALITA)._year == 2019)
        assert(FilmPath(ATMITW)._year == 2017)
        assert(not FilmPath(DEEP)._year)
        assert(FilmPath(STARLORD).parent._year == 2022)
        assert(FilmPath(STARLORD).filmrel._year == 2022)
        assert(FilmPath(TTOP)._year == 1968)
        assert(not FilmPath('2001.A.Space.Odyssey.1080p.x264.mkv')._year)
        assert(FilmPath(ZELDA)._year == 1991)
        assert(FilmPath(ZORG)._year == 1989)

    # Methods

    def test_sync(self):

        f = FilmPath(SRC / ALITA) / Path(f'{ALITA}.mkv')
        Make.mock_file(f)

        assert(not 'filmrel' in f.__dict__)
        assert(not 'filmroot' in f.__dict__)
        assert(not 'is_filmroot' in f.__dict__)
        assert(not 'maybe_film' in f.__dict__)

        FilmPath.sync(f, ['filmrel',
                          'filmroot',
                          'is_filmroot',
                          'maybe_film'])

        assert('filmrel' in f.__dict__)
        assert('filmroot' in f.__dict__)
        assert('is_filmroot' in f.__dict__)
        assert('maybe_film' in f.__dict__)


class TestInfo(object):

    def test_exists_case_sensitive(self):
        name = SRC / 'test-1080p.mkv'
        funkyname = SRC / 'tEsT-fUnKy-1080p.MKV'

        Make.mock_files(name, funkyname)

        assert(name.exists())
        assert(funkyname.exists())
        assert(FilmPath.Info.exists_case_sensitive(name))
        assert(FilmPath.Info.exists_case_sensitive(funkyname))
        assert(not FilmPath.Info.exists_case_sensitive(str(name).upper()))
        assert(not FilmPath.Info.exists_case_sensitive(str(funkyname).lower()))

    def test_is_acceptable_size(self):

        files = [
            'Test.File.1080p.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo',
            'Test.File.mkv',
            'TestDir/File.avi'
        ]

        Make.mock_file(SRC / files[0], 300 * MB)  # OK
        Make.mock_file(SRC / files[1],   1 * MB)  # Not OK
        Make.mock_file(SRC / files[2],   4 * KB)  # OK (not a video)
        Make.mock_file(SRC / files[3],  54 * MB)  # OK
        Make.mock_file(SRC / files[4],   4 * KB)  # OK (not a video)
        Make.mock_file(SRC / files[5],  18 * MB)  # Not OK
        Make.mock_file(SRC / files[6],  18 * MB)  # Dir - Not OK

        assert(Film.Info.is_acceptable_size(Film(SRC / files[0]).main_file))
        assert(not Film.Info.is_acceptable_size(
            Film(SRC / files[1]).main_file))
        assert(Film.Info.is_acceptable_size(Film(SRC / files[2]).main_file))
        assert(Film.Info.is_acceptable_size(Film(SRC / files[3]).main_file))
        assert(Film.Info.is_acceptable_size(Film(SRC / files[4]).main_file))
        assert(not Film.Info.is_acceptable_size(
            Film(SRC / files[5]).main_file))
        assert(not Film.Info.is_acceptable_size(Film(SRC / files[5])))

    def test_is_same_partition(self):
        assert(FilmPath.Info.is_same_partition(Path().home(), Path().home().parent))
        # Cannot reliably test if this function fails, we'll just have to trust
        # that when it's not on the same partition, it returns false.

    def test_is_video_file(self):
        mkv = 'test-1080p.mkv'
        bad = 'test.txt'

        assert(FilmPath.Info.is_video_file(mkv))
        assert(FilmPath.Info.is_video_file(Path(mkv)))
        assert(FilmPath.Info.is_video_file(FilmPath(mkv)))

        assert(not FilmPath.Info.is_video_file(bad))
        assert(not FilmPath.Info.is_video_file(Path(bad)))
        assert(not FilmPath.Info.is_video_file(FilmPath(bad)))

        Make.mock_file(SRC / mkv)

        assert(FilmPath.Info.is_video_file(os.path.normpath(str(SRC) + '/' + mkv)))
        assert(FilmPath.Info.is_video_file(SRC / Path(mkv)))
        assert(FilmPath.Info.is_video_file(SRC / FilmPath(mkv)))

        conftest.cleanup_all()
        Make.empty_dirs()

        funkyname = 'tEsT-1080p.MKV'

        assert(FilmPath.Info.is_video_file(funkyname))
        assert(FilmPath.Info.is_video_file(Path(funkyname)))
        assert(FilmPath.Info.is_video_file(FilmPath(funkyname)))

        # Test relpath
        assert(FilmPath.Info.is_video_file(STARLORD))

    def test_has_ignored_string(self):
        config.ignore_strings.extend(['sample', '@eaDir', '_UNPACK_'])
        assert(not FilmPath.Info.has_ignored_string('dir/A.File.1080p.bluray.x264-scene.mkv'))
        assert(FilmPath.Info.has_ignored_string('sample'))
        assert(FilmPath.Info.has_ignored_string('A.File.1080p.bluray.x264-scene.sample.mkv'))
        assert(FilmPath.Info.has_ignored_string('SaMpLe'))
        assert(FilmPath.Info.has_ignored_string('@eaDir'))
        assert(FilmPath.Info.has_ignored_string('@EAdir'))
        assert(FilmPath.Info.has_ignored_string(Path('_UNPACK_a.file.named.something')))
        assert(FilmPath.Info.has_ignored_string(Path('_unpack_a.file.named.something')))

    def test_has_valid_ext(self):

        files = [
            'Test.File.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo',
            'Test.File.jpg',
        ]

        for f in files:
            Make.mock_file(SRC / f)

        assert(FilmPath.Info.has_valid_ext(SRC / files[0]))
        assert(FilmPath.Info.has_valid_ext(SRC / files[1]))
        assert(FilmPath.Info.has_valid_ext(SRC / files[2]))
        assert(FilmPath.Info.has_valid_ext(SRC / files[3]))
        assert(not FilmPath.Info.has_valid_ext(SRC / files[4]))
        assert(not FilmPath.Info.has_valid_ext(SRC / files[5]))

    def test_min_filesize(self):

        files = [
            Film('Test.File.1080p.mkv'),
            Film('Test.File.2160p.mp4'),
            Film('Test.File.1080p.srt'),
            Film('Test.File.720p.mkv'),
            Film('Test.File.mkv'),
            Film('Test.File.nfo'),
            Film('Test.File.avi')
        ]

        assert(Film.Info.min_filesize(files[0]) == 100 * MB)
        assert(Film.Info.min_filesize(files[1]) == 200 * MB)
        assert(Film.Info.min_filesize(files[2]) == 0 * MB)
        assert(Film.Info.min_filesize(files[3]) == 50 * MB)
        assert(Film.Info.min_filesize(files[4]) == 20 * MB)
        assert(Film.Info.min_filesize(files[5]) == 0 * MB)
        assert(Film.Info.min_filesize(files[6]) == 20 * MB)

    def test_paths_exist(self):
        # 2/2 valid paths
        assert(FilmPath.Info.paths_exist([((Path('.').resolve()).anchor),
                                 Path('.').resolve()]))
        # 1/2 valid paths
        assert(not FilmPath.Info.paths_exist([Path('/__THERE_IS_NO_SPOON__'),
                                     Path('.').resolve()]))
        # 0/1 valid paths
        assert(not FilmPath.Info.paths_exist([Path('/__THERE_IS_NO_SPOON__')]))
