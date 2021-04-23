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

import pytest

import fylmlib.config as config
from fylmlib.operations import *
from fylmlib.tools import *
from fylmlib.enums import *
import conftest
import fylm
from make import Make, GB, MB, KB
from pathlib import Path

# Travis override for mini file sizes
# Multipy any size measurement by T to get an actual size
T = 1024 if os.environ.get('TRAVIS') else 1
    
def is_alphabetical_name(l: [Path]):
    return all(l[i].name.lower() <= l[i+1].name.lower()
               for i in range(len(l)-1))

SRC = conftest.src_path
SRC2 = conftest.src_path2

ALITA = 'Alita.Battle.Angel.2019.BluRay.1080p.x264-NMaRE'
ALITA_DST = f'Alita Battle Angel (2019) Bluray-1080p/'\
                f'Alita Battle Angel (2019) Bluray-1080p.mkv'
ATMITW = 'All.the.Money.in.the.World.2017.BluRay.1080p.x264-NMaRE'
AVATAR = 'Avatar.2009.BluRay.2160p.HDR.x265-xWinG'
DEEP = '#deep'
ROGUE = 'Rogue.One.2016.1080p.BluRay.DTS.x264-group'
STARLORD = 'Starlord.2022.1080p/Starlord.mkv'
TTOP = '2001.A.Space.Odyssey.1968.1080p'
ZELDA = 'Zelda.A.Link.To.The.Past.1991.1080p.Bluray.mkv'
ZORG = 'Zorg.2.1989.1080p.Bluray.mkv'

class TestCreate(object):
    
    def test_create_dirs(self):
        
        conftest.cleanup_all()
        assert(not SRC.exists())
        Create.dirs(SRC)
        assert(SRC.is_dir())
        
    def test_create_dirs_multi(self):

        conftest.cleanup_all()
        assert(not SRC.exists())
        Create.dirs(SRC / 'Curie',
                    SRC / 'Curie',
                    SRC / 'Seager')
        assert(SRC.is_dir())
        assert((SRC / 'Curie').is_dir())
        assert((SRC / 'Seager').is_dir())
        
    def test_create_dirs_testmode(self):
        
        conftest.cleanup_all()
        config.test = True
        assert(config.test is True)
        assert(not SRC.exists())
        Create.dirs(SRC)
        assert(not SRC.exists())
        
    @pytest.mark.xfail(raises=PermissionError)
    def test_create_dirs_not_writable(self):

        if sys.platform == "win32":
            Create.dirs('C:\\Windows\\System32\\ShouldNotBeWritable')
        else:
            Create.dirs('/bin/ShouldNotBeWritable')
            
class TestDelete(object):
    
    def test_delete_dir(self):
        
        conftest.remake_files()
        
        d = first(SRC.iterdir(), where=lambda x: x.is_dir())

        assert(d.is_dir())
        assert(Size.calc(d) > 1000)

        # Make sure the dir is small enough to be deleted
        for x in d.iterdir():
            x.unlink()
        assert(Size.calc(d) < config.min_filesize.default)
        
        Delete.dir(d)
        assert(not d.is_dir())
        
    def test_delete_dir_testmode(self):

        conftest.remake_files()
        config.test = True
        assert(config.test is True)
        
        d = first(SRC.iterdir(), where=lambda x: x.is_dir())

        assert(d.is_dir())
        assert(Size.calc(d) > 1000)

        for x in d.iterdir():
            x.unlink()
            
        # Make sure the dir is small enough to be deleted
        assert(Size.calc(d) < config.min_filesize.default)
        Delete.dir(d)
        assert(d.is_dir())
        
        assert(SRC.exists())
        Create.dirs(SRC)
        assert(SRC.exists())
        
    def test_fail_delete_non_empty_dir(self):
        
        conftest.remake_files()
        
        d = first(SRC.iterdir(), where=lambda x: x.is_dir())
        orig_size = Size.calc(d)
        
        assert(d.is_dir())
        assert(Size.calc(d) > 1000)
        Delete.dir(d)
        # Test should not raise an error, but should silently not delete
        assert(d.is_dir())
        assert(Size.calc(d) == orig_size)
        
    def test_delete_min_filesize(self):

        conftest.cleanup_all()
        
        main = SRC / 'Yates'
        create_path = main / 'Gilbert/Holtzmann/Tolan'
        
        assert(config.min_filesize['720p'] == 50)
        assert(config.min_filesize['1080p'] == 100)
        assert(config.min_filesize['2160p'] == 200)
        assert(config.min_filesize['SD'] == 20)
        assert(config.min_filesize['default'] == 20)

        files = [
            'Yates/Abby.txt',
            'Yates/Gilbert/Erin.txt',
            'Yates/Gilbert/Holtzmann/Jillian.txt',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.txt'
        ]
        
        # Test 1: Files do not exceed max_size
        for f in files:
            Make.mock_file(SRC / f, 4 * KB)

        assert(iterlen(Find.deep_files(SRC)) == 4)

        Delete.dir(main)

        assert(iterlen(Find.deep_files(SRC)) == 0)
        assert(not main.exists())
                       
        # Test 2: Files exceed max_size
        conftest.cleanup_all()
        
        for f in files:
            Make.mock_file(SRC / f, 40 * MB)

        assert(iterlen(Find.deep_files(SRC)) == 4)

        Delete.dir(main)

        assert(iterlen(Find.deep_files(SRC)) == 4)
        assert(main.exists())
        
    def test_fail_delete_force(self):

        conftest.remake_files()

        d = first(SRC.iterdir(), where=lambda x: x.is_dir())
        orig_size = Size.calc(d)

        assert(d.is_dir())
        assert(Size.calc(d) > 1000)
        Delete.dir(d, force=True)
        # Test should not raise an error, but should silently delete
        assert(not d.is_dir())
    
    @pytest.mark.xfail(raises=OSError)
    def test_fail_delete_src_dir(self):

        conftest.remake_files()

        assert(SRC.is_dir())
        assert(Size.calc(SRC) > 1000)
        Delete.dir(SRC)
        assert(SRC.is_dir())
        
    def test_delete_files(self):
        pass
    
    def test_delete_file(self):
        pass    

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

        files = [d for d in SRC.iterdir() if d.is_file() and not is_sys_file(d)]
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
        assert(FilmPath(f'/{STARLORD}').origin == Path(f'/{STARLORD}'))
        assert(FilmPath(SRC).origin == SRC)
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        assert(alita.origin == alita)

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

    def test_files(self):
        Make.all_mock_files()

        found = list(Find.shallow(SRC))
        files = list(filter(lambda x: x.is_file() and not x == SRC, found))

        assert(FilmPath(SRC).files)
        assert(len(FilmPath(SRC).files) == len(files))

    def test_filmrel(self):
        
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        ttop = FilmPath((SRC / DEEP / TTOP / TTOP).with_suffix('.mkv'))
        zelda = FilmPath(SRC / ZELDA)
        
        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        atmitw,
                        notes,
                        starlord,
                        ttop,
                        zelda)
        
        assert(not FilmPath(SRC).filmrel)
        assert(alita.filmrel == Path(ALITA) / Path(f'{ALITA}.mkv'))
        assert(alita.parent.filmrel == Path(ALITA))
        assert(atmitw.filmrel == Path(ATMITW) / Path(ATMITW).with_suffix('.mkv'))
        assert(atmitw.parent.filmrel == Path(ATMITW))
        assert(not avatar.filmrel)
        assert(not empty.filmrel)
        assert(not notes.filmrel)
        assert(starlord.filmrel == Path(STARLORD))
        assert(ttop.filmrel == Path(TTOP) / Path(TTOP).with_suffix('.mkv'))
        assert(zelda.filmrel == Path(ZELDA))

    def test_filmroot(self):
        
        alita = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        atmitw = FilmPath((SRC / ATMITW / ATMITW).with_suffix('.mkv'))
        avatar = FilmPath(SRC / '#4K' / AVATAR)
        empty = FilmPath(SRC / '#empty' / 'empty_dir')
        notes = FilmPath(SRC / '#notes' / 'my_note.txt')
        starlord = FilmPath(SRC / DEEP / STARLORD)
        ttop = FilmPath((SRC / DEEP / TTOP / TTOP).with_suffix('.mkv'))
        zelda = FilmPath(SRC / ZELDA)

        Create.dirs(avatar, empty)
        Make.mock_files(alita,
                        atmitw,
                        notes,
                        starlord,
                        ttop,
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
        assert(not avatar.is_filmroot) # empty
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
        assert(not FilmPath('dir/A.File.1080p.bluray.x264-scene.mkv').has_ignored_string)
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
        
        assert(not FilmPath(SRC).maybe_film)
        assert(not FilmPath(SRC / '#4K').maybe_film)
        assert(not FilmPath(SRC / DEEP).maybe_film)
        assert(alita.maybe_film)
        assert(alita.parent.maybe_film)
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
        
        assert(FilmPath(ALITA).year == 2019)
        assert(FilmPath(ATMITW).year == 2017)
        assert(not FilmPath(DEEP).year)
        assert(FilmPath(STARLORD).parent.year == 2022)
        assert(FilmPath(STARLORD).filmrel.year == 2022)
        assert(FilmPath(TTOP).year == 1968)
        assert(not FilmPath('2001.A.Space.Odyssey.1080p.x264.mkv').year)
        assert(FilmPath(ZELDA).year == 1991)
        assert(FilmPath(ZORG).year == 1989)

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

class TestFind(object):
    
    def test_find_deep(self):
        
        made = Make.all_mock_files().all_files
        found = [x for x in Find.deep(SRC) if x.is_file()]
        
        assert(len(found) == len(made))
        
    def test_find_deep_files(self):
        
        made = Make.all_mock_files().all_files
        found = list(Find.deep_files(SRC))
        
        assert(len(found) == len(made))
    
    def test_find_deep_ignore_sys_files(self):

        create_path1 = SRC / 'Yates/Gilbert/Holtzmann/Tolan'
        create_path2 = SRC / 'Roman/Hamilton/Ride/Jemison'

        Create.dirs(create_path1)
        Create.dirs(create_path2)

        files = [
            'Yates/Abby.txt',
            'Yates/Gilbert/Erin.txt',
            'Yates/Gilbert/Holtzmann/Jillian.txt',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.txt',
            'Yates/Thumbs.db',
            'Roman/Nancy_Grace.txt',
            'Roman/Hamilton/Margaret.txt',
            'Roman/Hamilton/Ride/Sally.txt',
            'Roman/Hamilton/Ride/Jemison/Mae.txt',
            'Roman/.DS_Store'
        ]

        for f in files:
            Make.mock_file(SRC / f)

        found = [x for x in Find.deep(SRC) if x.is_file()]

        assert(len(found) == 8)
        assert(not str(SRC / files[4]) in found)
        assert(not str(SRC / files[9]) in found)
    
    def test_find_deep_sorted(self):
        
        made = Make.all_mock_files().all_files
        found = list(Find.deep_files(SRC))

        assert(len(found) == len(made))
        
        # Assert that the list is sorted alphabetically by name (case insensitive)
        assert(is_alphabetical_name(found))
    
    def test_find_existing(self):

        files = {
            '2160p': 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.DTS.mp4',
            '1080p': 'Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group.mkv',
            '720p': 'Rogue.One.A.Star.Wars.Story.2016.720p.DTS.x264-group.mkv',
            'SD': 'Rogue.One.A.Star.Wars.Story.2016.avi'
        }

        Make.mock_dst_files(files)

        assert(Find._EXISTING is None)
        assert(iterlen(Find.existing()) == 4)
        assert(Find._EXISTING and len(Find._EXISTING) == 4)
        
        # Test caching
        conftest.cleanup_dst()
        assert(iterlen(Find.existing()) == 4)
    
    def test_find_new(self):

        made = Make.all_mock_files().all_files

        start = timer()

        assert(Find._NEW is None)

        new = [x for x in Find.new(SRC) if x.is_file()]

        end = timer()

        assert(end - start < 3)
        assert(len(new) == len(made))

        # valid_films = list(filter(lambda film: not film.should_ignore, new))

        # Assert that we're getting the expected number of films.
        assert(len(Find._NEW) > 1)
        assert(len([x for x in Find._NEW if x.is_file()]) == len(made))

        # Assert that we're getting the expected number of valid films.
        # assert(len(valid_films) == len(conftest.made.good))
        
        # Try again after removing src, to test caching.
        conftest.cleanup_src()
        new = [x for x in Find.new(SRC) if x.is_video_file]
        assert(len(new) == len(made))

    def test_find_new_multi(self):
        
        made = Make.all_mock_files().all_files
        config.source_dirs.append(SRC2)
        files = ['Alita.Battle.Angel.2019.BluRay.1080p.x264-NMaRE',
                 'All.the.Money.in.the.World.2017.BluRay.1080p.x264-NMaRE']
        
        # Make files in alternate path
        for name in files:
            Make.mock_src_files(
                Path(name) / Path(name).with_suffix('.mkv'), 
                src_path=SRC)

        assert(Find._NEW is None)
        
        new = [x for x in Find.new(SRC, SRC2, sort_key=lambda x: x.name.lower()) if x.is_file()]

        # Assert that we're getting the expected number of films, + 2

        assert(len(new) == len(made) + 2)

        # valid_films = list(filter(lambda film: not film.should_ignore, new))

        # Assert that we're getting the expected number of films.
        assert(len(Find._NEW) > 1)
        assert(len([x for x in Find._NEW if x.is_file()]) == len(made) + 2)

        # Assert that we're getting the expected number of valid films.
        # assert(len(valid_films) == len(conftest.made.good))

        # Assert that the list is sorted alphabetically (case insensitive)
        assert(is_alphabetical_name(new))
        
    def test_find_shallow(self):
        
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
        
        found = Find.shallow(SRC)
        assert(iterlen(found) == 8)
        
    def test_sync_attrs(self):
        
        Make.all_mock_files()
        found = list(Find.deep(SRC))
        
        for f in found:
            assert(not 'filmrel' in f.__dict__)
            assert(not 'filmroot' in f.__dict__)
            assert(not 'is_filmroot' in f.__dict__)
            assert(not 'maybe_film' in f.__dict__)
            
        synced = Find.sync_attrs(iter(found), attrs=['filmrel', 
                                                     'filmroot', 
                                                     'is_filmroot', 
                                                     'maybe_film'])
        
        for f in synced:
            assert('filmrel' in f.__dict__)
            assert('filmroot' in f.__dict__)
            assert('is_filmroot' in f.__dict__)
            assert('maybe_film' in f.__dict__)

    @pytest.mark.skip()
    def test_get_valid_files(self):

        conftest._setup()

        config.min_filesize = 50 # min filesize in MB
        assert(config.min_filesize == 50)

        name = Path(ROGUE)
        files = [
            name / name.with_suffix('.mkv'), # good
            name / name.with_suffix('.sample.mkv'),
            name / 'GROUP.mkv',
            name / 'RO-ad-scene-WATCHME.mkv',
            name / 'subs-english.srt', # good
            name / name.with_suffix('.nfo'),
            name / name.with_suffix('.sfv'),
            name / 'Cover.jpg'
        ]

        conftest.cleanup_all()
        conftest.make_empty_dirs()
        
        for f in files:
            Make.mock_src_files(f)
        
        # Assert that there is only one test film identified at the source
        assert(len(Find.existing([SRC])) == 1)

        valid_files = Find.get_valid_files(SRC / name)

        # Assert that of the 8 files presented, only two are valid
        #   Main video file and .srt
        assert(len(valid_files) == 2)

        assert(os.path.join(SRC, files[0]) in valid_files) # Main video file
        assert(os.path.join(SRC, files[4]) in valid_files) # .srt

    def test_get_invaild_files(self):

        conftest._setup()

        config.min_filesize = 50 # min filesize in MB
        assert(config.min_filesize == 50)

        files = [
            f'{ROGUE}/{ROGUE}.mkv',
            f'{ROGUE}/{ROGUE}.sample.mkv',
            f'{ROGUE}/GROUP.mkv',
            f'{ROGUE}/subs-english.srt',
            f'{ROGUE}/{ROGUE}.nfo',
            f'{ROGUE}/{ROGUE}.sfv',
            f'{ROGUE}/Cover.jpg'
        ]

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        Make.mock_file(os.path.join(SRC, files[0]), 2354 * MB)
        Make.mock_file(os.path.join(SRC, files[1]),  134 * MB)
        Make.mock_file(os.path.join(SRC, files[2]),   23 * MB)
        Make.mock_file(os.path.join(SRC, files[3]),  219 * KB)
        Make.mock_file(os.path.join(SRC, files[4]),   14 * KB)
        Make.mock_file(os.path.join(SRC, files[5]),    5 * KB)
        Make.mock_file(os.path.join(SRC, files[6]),    6 * MB)
        Make.mock_file(os.path.join(SRC, files[7]),    7 * MB)
        
        # Assert that there is only one test film identified at the source
        assert(len(ops.dirops.find_new(SRC)) == 1)

        invalid_files = ops.dirops.get_invalid_files(
            os.path.join(SRC, ROGUE)
        )

        # Assert that of the 8 files presented, 6 are invalid
        assert(len(invalid_files) == 6)

        assert(os.path.join(SRC, files[0]) not in invalid_files) # Main video file
        assert(os.path.join(SRC, files[4]) not in invalid_files) # .srt


    @pytest.mark.skip()
    def test_delete_unwanted_files(self):

        conftest.cleanup_all()

        create_path = os.path.join(SRC, 'Yates/Gilbert/Holtzmann/Tolan')

        ops.dirops.create_deep(create_path)

        files_nfo = [
            'Yates/Abby.nfo',
            'Yates/Gilbert/Erin.nfo',
            'Yates/Gilbert/Holtzmann/Jillian.nfo',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.nfo'
        ]

        files_mkv = [
            'Yates/Abby.mkv',
            'Yates/Gilbert/Erin.mkv',
            'Yates/Gilbert/Holtzmann/Jillian.mkv',
            'Yates/Gilbert/Holtzmann/Tolan/Patty.mkv'
        ]

        bad_files_mkv = [
            'Yates/Oh.mkv',
            'Yates/Gilbert/Danny.mkv',
            'Yates/Gilbert/Holtzmann/Boy.mkv',
            'Yates/Gilbert/Holtzmann/Tolan/The.mkv'
        ]

        config.min_filesize = 5
        assert(config.min_filesize == 5)

        # Create files. Ensure that for this to pass, the total filesize of the test dir
        # does not exceed this method's max_size default (50KB).
        for f in files_nfo:
             Make.mock_file(os.path.join(SRC, f), 4 * KB)
        for f in files_mkv:
             Make.mock_file(os.path.join(SRC, f), 7418 * MB)
        for f in bad_files_mkv:
             Make.mock_file(os.path.join(SRC, f), 7 * KB)

        before = ops.dirops.find_deep(SRC)
        assert(len(before) == 12)

        config.test = True
        assert(config.test is True)

        ops.dirops.delete_unwanted_files(SRC)

        after_contents_t = ops.dirops.find_deep(SRC)
        assert(len(after_contents_t) == 12)

        config.test = False
        assert(config.test is False)

        ops.dirops.delete_unwanted_files(SRC)

        after = ops.dirops.find_deep(SRC)
        assert(len(after) == 4)

        config.min_filesize = 0
        assert(config.min_filesize == 0)

class TestInfo(object):
    
    def test_is_video_file(self):
        mkv = 'test-1080p.mkv'
        bad = 'test.txt'
        
        assert(Info.is_video_file(mkv))
        assert(Info.is_video_file(Path(mkv)))
        assert(Info.is_video_file(FilmPath(mkv)))
        
        assert(not Info.is_video_file(bad))
        assert(not Info.is_video_file(Path(bad)))
        assert(not Info.is_video_file(FilmPath(bad)))
        
        Make.mock_src_files(mkv)
        
        assert(Info.is_video_file(os.path.normpath(str(SRC) + '/' + mkv)))
        assert(Info.is_video_file(SRC / Path(mkv)))
        assert(Info.is_video_file(SRC / FilmPath(mkv)))
        
        conftest.cleanup_all()
        Make.empty_dirs()
        
        funkyname = 'tEsT-1080p.MKV'

        assert(Info.is_video_file(funkyname))
        assert(Info.is_video_file(Path(funkyname)))
        assert(Info.is_video_file(FilmPath(funkyname)))
        
        # Test relpath
        assert(Info.is_video_file(STARLORD))
        
    def test_has_ignored_string(self):
        assert(not Info.has_ignored_string('dir/A.File.1080p.bluray.x264-scene.mkv'))
        assert(Info.has_ignored_string('sample'))
        assert(Info.has_ignored_string('A.File.1080p.bluray.x264-scene.sample.mkv'))
        assert(Info.has_ignored_string('SaMpLe'))
        assert(Info.has_ignored_string('@eaDir'))
        assert(Info.has_ignored_string('@EAdir'))
        assert(Info.has_ignored_string(Path('_UNPACK_a.file.named.something')))
        assert(Info.has_ignored_string(Path('_unpack_a.file.named.something')))

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

        assert(Info.has_valid_ext(SRC / files[0]))
        assert(Info.has_valid_ext(SRC / files[1]))
        assert(Info.has_valid_ext(SRC / files[2]))
        assert(Info.has_valid_ext(SRC / files[3]))
        assert(not Info.has_valid_ext(SRC / files[4]))
        assert(not Info.has_valid_ext(SRC / files[5]))
    
    def test_paths_exist(self):
        # 2/2 valid paths
        assert(Info.paths_exist([((Path('.').resolve()).anchor),
                                     Path('.').resolve()]))
        # 1/2 valid paths
        assert(not Info.paths_exist([Path('/__THERE_IS_NO_SPOON__'),
                                         Path('.').resolve()]))
        # 0/1 valid paths
        assert(not Info.paths_exist([Path('/__THERE_IS_NO_SPOON__')]))

    def test_is_same_partition(self):
        assert(Info.is_same_partition(Path().home(), Path().home().parent))
        # Cannot reliably test if this function fails, we'll just have to trust 
        # that when it's not on the same partition, it returns false.
        
    def test_exists_case_sensitive(self):
        name = 'test-1080p.mkv'
        funkyname = 'tEsT-fUnKy-1080p.MKV'
        
        Make.mock_src_files(name, funkyname)
        
        assert(Path(SRC / Path(name)).exists())
        assert(Path(SRC / Path(funkyname)).exists())
        assert(Info.exists_case_sensitive(Path(SRC / Path(name))))
        assert(Info.exists_case_sensitive(Path(SRC / Path(funkyname))))
        assert(not Info.exists_case_sensitive(Path(SRC / Path(name.upper()))))
        assert(not Info.exists_case_sensitive(Path(SRC / Path(funkyname.lower()))))

class FileExistsHandler(FileSystemEventHandler):
    
    def __init__(self, path: Union[str, Path, 'FilmPath']):
        super().__init__()
        
        self.path = Path(path)
        self.exists = self.path.exists()
        
    def on_modified(self, event):
        while not self.path.exists():
            pass
        self.exists = True
        return
        
class TestMove(object):
    
    @pytest.mark.xfail(raises=OSError)
    def test_safe_not_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        assert(not src.exists())
        Move.safe(src, dst)
        assert(not src.exists())
        assert(not dst.exists())
    
    def test_safe_src_eq_dst(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA / f'{ALITA}.mkv')

        Make.mock_file(src)

        assert(src.exists())
        assert(dst.exists())
        Move.safe(src, dst)
        assert(src.exists())
        assert(dst.exists())
    
    def test_safe_test_mode(self):
        
        config.test = True
        assert(config.test)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_file(src)

        assert(src.exists())
        assert(not dst.exists())
        Move.safe(src, dst)
        assert(src.exists())
        assert(not dst.exists())
    
    def test_safe_exists_overwrite_arg_off(self):
        
        assert(not config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        Move.safe(src, dst)
        assert(src.exists())
        assert(dst.exists())
    
    def test_safe_exists_overwrite_arg_on(self):
        
        assert(not config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        Move.safe(src, dst, overwrite=True)
        assert(not src.exists())
        assert(dst.exists())
    
    def test_safe_exists_overwrite_force_on(self):
        
        config.duplicates.force_overwrite = True
        assert(config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        Move.safe(src, dst)
        assert(not src.exists())
        assert(dst.exists())
    
    def test_safe_check_for_partial(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)
        partial = Path(f'{dst}.partial~')
        
        Create.dirs(dst.parent)
        Make.mock_file(src)

        event_handler = FileExistsHandler(partial)
        observer = Observer()
        observer.schedule(event_handler, path=partial.parent, recursive=False)
        observer.start()
        
        assert(src.exists())
        assert(not dst.exists())
        
        Move.safe(src, dst)
        assert(event_handler.exists)
        
        assert(not src.exists())
        assert(dst.exists())
        
        observer.stop()
    
    def test_safe_check_for_dup(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)
        partial = Path(f'{dst}.dup~')

        Create.dirs(dst.parent)
        Make.mock_file(src)
        Make.mock_file(dst)

        event_handler = FileExistsHandler(partial)
        observer = Observer()
        observer.schedule(event_handler, path=partial.parent, recursive=False)
        observer.start()

        assert(src.exists())
        assert(dst.exists())

        Move.safe(src, dst, overwrite=True)
        assert(event_handler.exists)

        assert(not src.exists())
        assert(dst.exists())

        observer.stop()
    
    def test_safe_copy(self):
        
        config.always_copy = True
        assert(config.always_copy)
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_file(src)

        
        assert(src.exists())
        assert(not dst.exists())
        with contextlib.redirect_stdout(None):
            Move.safe(src, dst)
        assert(not src.exists())
        assert(dst.exists())
    
    def test_safe_move(self):
        
        assert(not config.always_copy)
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)
        
        Make.mock_file(src)
        
        assert(src.exists())
        assert(not dst.exists())
        Move.safe(src, dst)
        assert(not src.exists())
        assert(dst.exists())
        
    def test_rename(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = Path(FilmPath(ALITA_DST).name)
        
        Make.mock_file(src)

        assert(src.exists())
        Move.rename(src, dst.name)
        assert(not src.exists())
        assert((SRC / ALITA / dst).exists())
    
    def test_rename_abs(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC2 / ALITA_DST)
        dst_proper = FilmPath((SRC / ALITA) / dst.name)

        Make.mock_file(src)

        assert(src.exists())
        Move.rename(src, dst)
        assert(not src.exists())
        assert(not dst.exists())
        assert(dst_proper.exists())
        
    @pytest.mark.xfail(raises=OSError)
    def test_rename_not_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        assert(not src.exists())
        Move.rename(src, dst.name)
        assert(not src.exists())
        assert(not dst.exists())
    
    def test_rename_src_eq_dst(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA / f'{ALITA}.mkv')

        Make.mock_file(src)

        assert(src.exists())
        assert(dst.exists())
        Move.rename(src, dst.name)
        assert(src.exists())
        assert(dst.exists())
    
    def test_rename_dst_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath((SRC / ALITA) / Path(ALITA_DST).name)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        Move.rename(src, dst.name)
        assert(src.exists())
        assert(dst.exists())
    
    def test_rename_test_mode(self):
        
        config.test = True
        assert(config.test)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_file(src)

        assert(src.exists())
        assert(not dst.exists())
        Move.rename(src, dst.name)
        assert(src.exists())
        assert(not dst.exists())
        

class TestSize(object):
    
    def test_calc(self):

        files =[
            (SRC / 'Test.File.mkv', 10 * MB),
            (SRC / 'Test.Dir/Test.File.mkv', 21 * MB),
            (SRC / 'Test.Dir2/Test.File.mkv', 8 * MB),
            (SRC / 'Test.Dir3/Test.File.jpg', 15 * KB),
            (SRC / 'Test.Dir4/Test.File.avi', 2 * MB)
        ]
      
        for f in files:
            Make.mock_file(f[0], f[1])

        # Assert file size matches definition
        for f in files:
            assert(abs(Size.calc(f[0]) - f[1]) == 0)

        # Assert dir is at least the size of the file, probably larger
        # because the folder itself takes up some space. Diff of 1 byte.
        
        for f in files[1:]: # slice the first one, because it is not in a dir
            assert(abs(Size.calc(Path(f[0]).parent) - f[1] == 0))

        # Test multiple files in dir to diff of 3 bytes
        assert(abs(Size.calc(SRC) - sum(s for (_, s) in files) == 0))
        
    def test_pretty(self):
        
        # Multiply each of these by 1024 to bypass Travis
        files = [
            (SRC / 'Test.File1.mkv', 1500 * MB * T),
            (SRC / 'Test.File2.mkv', 0.75 * GB * T),
            (SRC / 'Test.File3.mkv', 10 * MB * T),
            (SRC / 'Test.File4.mkv', 100),
            (SRC / 'Test.File5.mkv', 1.25 * GB * T),
            (SRC / 'Test.File6.mkv', 700 * MB * T)
        ]

        for f in files:
            Make.mock_file(f[0], f[1])
                        
        assert(Size.pretty(files[0][0]) == '1.46 GiB')
        assert(Size.pretty(files[0][0], units=Units.GB) == '1.57 GB')
        assert(Size.pretty(files[0][0], precision=1) == '1.5 GiB')
        assert(Size.pretty(files[0][0], precision=0) == '1 GiB')
        assert(Size.pretty(files[0][0], units=Units.MiB) == '1,500.0 MiB')
        assert(Size.pretty(files[0][0], units=Units.MB) == '1,572.9 MB')
        assert(Size.pretty(files[1][0]) == '768.0 MiB')
        assert(Size.pretty(files[2][0]) == '10.0 MiB')
        assert(Size.pretty(files[3][0]) == '100 B')
        assert(Size.pretty(files[4][0]) == '1.25 GiB')
        assert(Size.pretty(files[5][0]) == '700.0 MiB')

@pytest.mark.skip()
class TestSizeOperations_Deprecated(object):
    
    def test_size_of_largest_video(self):

        conftest._setup()

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            'Test.File/Test.File.mkv',
            'Test.File/Test.File2.mkv',
            'Test.File/Test.File3.mkv',
            'Test.File/Test.File.avi',
            'Test.File/Test.File.srt',
            'Test.File/Test.File.mp4',
            'Test.File/Test.File.nfo'
        ]

        Make.mock_file(os.path.join(SRC, files[0]), 2354 * MB)
        Make.mock_file(os.path.join(SRC, files[1]), 1612 * MB)
        Make.mock_file(os.path.join(SRC, files[2]),  280 * MB)
        Make.mock_file(os.path.join(SRC, files[3]),   10 * MB)
        Make.mock_file(os.path.join(SRC, files[4]),    4 * KB)
        Make.mock_file(os.path.join(SRC, files[5]),  454 * MB)
        Make.mock_file(os.path.join(SRC, files[6]),    4 * KB)

        # Test multiple files to diff of 1 byte
        assert(abs(ops.size(ops.largest_video(os.path.dirname('Test.File'))) - (2354 * MB)) <= 1)

    def test_is_acceptable_size(self):

        conftest._setup()

        config.min_filesize = 5  # min filesize in MB
        assert(config.min_filesize == 5)

        conftest.cleanup_all()
        conftest.make_empty_dirs()

        files = [
            'Test.File.mkv',
            'Test.File.avi',
            'Test.File.srt',
            'Test.File.mp4',
            'Test.File.nfo'
        ]

        Make.mock_file(os.path.join(SRC, files[0]),  300 * MB)
        Make.mock_file(os.path.join(SRC, files[1]),    1 * MB)
        Make.mock_file(os.path.join(SRC, files[2]),    4 * KB)
        Make.mock_file(os.path.join(SRC, files[3]),   54 * MB)
        Make.mock_file(os.path.join(SRC, files[4]),    4 * KB)

        assert(ops.fileops.is_acceptable_size(os.path.join(SRC, files[0])))
        assert(not ops.fileops.is_acceptable_size(os.path.join(SRC, files[1])))
        assert(ops.fileops.is_acceptable_size(os.path.join(SRC, files[2])))
        assert(ops.fileops.is_acceptable_size(os.path.join(SRC, files[3])))
        assert(not ops.fileops.is_acceptable_size(os.path.join(SRC, files[4])))

        config.min_filesize = 0  # min filesize back to 0
        assert(config.min_filesize == 0)
