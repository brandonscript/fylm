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
from fylmlib import FilmPath
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
        assert(Size(d).value > 1000)

        # Make sure the dir is small enough to be deleted
        for x in d.iterdir():
            x.unlink()
        assert(Size(d).value < config.min_filesize.default)
        
        Delete.dir(d)
        assert(not d.is_dir())
        
    def test_delete_dir_testmode(self):

        conftest.remake_files()
        config.test = True
        assert(config.test is True)
        
        d = first(SRC.iterdir(), where=lambda x: x.is_dir())

        assert(d.is_dir())
        assert(Size(d).value > 1000)

        for x in d.iterdir():
            x.unlink()
            
        # Make sure the dir is small enough to be deleted
        assert(Size(d).value < config.min_filesize.default)
        Delete.dir(d)
        assert(d.is_dir())
        
        assert(SRC.exists())
        Create.dirs(SRC)
        assert(SRC.exists())
        
    def test_fail_delete_non_empty_dir(self):
        
        conftest.remake_files()
        
        d = first(SRC.iterdir(), where=lambda x: x.is_dir())
        orig_size = Size(d).value
        
        assert(d.is_dir())
        assert(Size(d).value > 1000)
        Delete.dir(d)
        # Test should not raise an error, but should silently not delete
        assert(d.is_dir())
        assert(Size(d).value == orig_size)
        
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
        orig_size = Size(d).value

        assert(d.is_dir())
        assert(Size(d).value > 1000)
        Delete.dir(d, force=True)
        # Test should not raise an error, but should silently delete
        assert(not d.is_dir())
    
    @pytest.mark.xfail(raises=OSError)
    def test_fail_delete_src_dir(self):

        conftest.remake_files()

        assert(SRC.is_dir())
        assert(Size(SRC).value > 1000)
        Delete.dir(SRC)
        assert(SRC.is_dir())
        
    def test_delete_files(self):
        pass
    
    def test_delete_file(self):
        pass    

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

        files = [
            DST['2160p'] / 'Rogue.One.A.Star.Wars.Story.2016.4K.2160p.DTS.mp4',
            DST['1080p'] / 'Rogue.One.A.Star.Wars.Story.2016.1080p.BluRay.DTS.x264-group.mkv',
            DST['720p'] / 'Rogue.One.A.Star.Wars.Story.2016.720p.DTS.x264-group.mkv',
            DST['SD'] / 'Rogue.One.A.Star.Wars.Story.2016.avi'
        ]

        Make.mock_files(*files)

        assert(Find.EXISTING is None)
        assert(iterlen(Find.existing()) == 4)
        assert(Find.EXISTING and len(Find.EXISTING) == 4)
        
        # Test caching
        conftest.cleanup_dst()
        assert(iterlen(Find.existing()) == 4)
    
    def test_find_new(self):

        made = Make.all_mock_files().all_files

        start = timer()

        assert(Find.NEW is None)

        new = [x for x in Find.new(SRC) if x.is_file()]

        end = timer()

        assert(end - start < 3)
        assert(len(new) == len(made))

        # valid_films = list(filter(lambda film: not film.should_ignore, new))

        # Assert that we're getting the expected number of films.
        assert(len(Find.NEW) > 1)
        assert(len([x for x in Find.NEW if x.is_file()]) == len(made))

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
            Make.mock_file(SRC2 / Path(name) / f'{name}.mkv')

        assert(Find.NEW is None)
        
        new = [x for x in Find.new(SRC, SRC2, sort_key=lambda x: x.name.lower()) if x.is_file()]

        # Assert that we're getting the expected number of films, + 2

        assert(len(new) == len(made) + 2)

        # valid_films = list(filter(lambda film: not film.should_ignore, new))

        # Assert that we're getting the expected number of films.
        assert(len(Find.NEW) > 1)
        assert(len([x for x in Find.NEW if x.is_file()]) == len(made) + 2)

        # Assert that we're getting the expected number of valid films.
        # assert(len(valid_films) == len(conftest.made.good))

        
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
        
    def test_sync_parallel(self):
        
        Make.all_mock_files()
        found = list(Find.deep(SRC))
        
        for f in found:
            assert(not 'filmrel' in f.__dict__)
            assert(not 'filmroot' in f.__dict__)
            assert(not 'is_filmroot' in f.__dict__)
            assert(not 'maybe_film' in f.__dict__)
            
        synced = Find.sync_parallel(iter(found), attrs=['filmrel', 
                                                     'filmroot', 
                                                     'is_filmroot', 
                                                     'maybe_film'])
        
        for f in synced:
            assert('filmrel' in f.__dict__)
            assert('filmroot' in f.__dict__)
            assert('is_filmroot' in f.__dict__)
            assert('maybe_film' in f.__dict__)
            
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
        
class TestIO(object):
    
    @pytest.mark.xfail(raises=OSError)
    def test_move_not_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        assert(not src.exists())
        IO.move(src, dst)
        assert(not src.exists())
        assert(not dst.exists())
    
    def test_move_src_eq_dst(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA / f'{ALITA}.mkv')

        Make.mock_file(src)

        assert(src.exists())
        assert(dst.exists())
        IO.move(src, dst)
        assert(src.exists())
        assert(dst.exists())
    
    def test_move_test_mode(self):
        
        config.test = True
        assert(config.test)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_file(src)

        assert(src.exists())
        assert(not dst.exists())
        IO.move(src, dst)
        assert(src.exists())
        assert(not dst.exists())
    
    def test_move_exists_overwrite_arg_off(self):
        
        assert(not config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        IO.move(src, dst)
        assert(src.exists())
        assert(dst.exists())
    
    def test_move_exists_overwrite_arg_on(self):
        
        assert(not config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        IO.move(src, dst, overwrite=True)
        assert(not src.exists())
        assert(dst.exists())
    
    def test_move_exists_overwrite_force_on(self):
        
        config.duplicates.force_overwrite = True
        assert(config.duplicates.force_overwrite)

        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        IO.move(src, dst)
        assert(not src.exists())
        assert(dst.exists())
    
    @pytest.mark.skip(reason="Travis not supported")
    def test_move_check_for_partial(self):
        
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
        
        IO.move(src, dst)
        assert(event_handler.exists)
        
        assert(not src.exists())
        assert(dst.exists())
        
        observer.stop()
    
    @pytest.mark.skip(reason="Travis not supported")
    def test_move_check_for_dup(self):
        
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

        IO.move(src, dst, overwrite=True)
        assert(event_handler.exists)

        assert(not src.exists())
        assert(dst.exists())

        observer.stop()
    
    def test_move_copy(self):
        
        config.always_copy = True
        assert(config.always_copy)
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        Make.mock_file(src)

        
        assert(src.exists())
        assert(not dst.exists())
        with contextlib.redirect_stdout(None):
            IO.move(src, dst)
        assert(not src.exists())
        assert(dst.exists())
    
    def test_move(self):
        
        assert(not config.always_copy)
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)
        
        Make.mock_file(src)
        
        assert(src.exists())
        assert(not dst.exists())
        IO.move(src, dst)
        assert(not src.exists())
        assert(dst.exists())
        
    def test_rename(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = Path(FilmPath(ALITA_DST).name)
        
        Make.mock_file(src)

        assert(src.exists())
        IO.rename(src, dst.name)
        assert(not src.exists())
        assert((SRC / ALITA / dst).exists())
    
    def test_rename_abs(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC2 / ALITA_DST)
        dst_proper = FilmPath((SRC / ALITA) / dst.name)

        Make.mock_file(src)

        assert(src.exists())
        IO.rename(src, dst)
        assert(not src.exists())
        assert(not dst.exists())
        assert(dst_proper.exists())
        
    @pytest.mark.xfail(raises=OSError)
    def test_rename_not_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA_DST)

        assert(not src.exists())
        IO.rename(src, dst.name)
        assert(not src.exists())
        assert(not dst.exists())
    
    def test_rename_src_eq_dst(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath(SRC / ALITA / f'{ALITA}.mkv')

        Make.mock_file(src)

        assert(src.exists())
        assert(dst.exists())
        IO.rename(src, dst.name)
        assert(src.exists())
        assert(dst.exists())
    
    def test_rename_dst_exists(self):
        
        src = FilmPath(SRC / ALITA / f'{ALITA}.mkv')
        dst = FilmPath((SRC / ALITA) / Path(ALITA_DST).name)

        Make.mock_files(src, dst)

        assert(src.exists())
        assert(dst.exists())
        IO.rename(src, dst.name)
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
        IO.rename(src, dst.name)
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
            assert(abs(Size(f[0]).value - f[1] == 0))

        # Assert dir is at least the size of the file, probably larger
        # because the folder itself takes up some space. Diff of 1 byte.
        
        for f in files[1:]: # slice the first one, because it is not in a dir
            assert(abs(Size(f[0].parent).value - f[1] == 0))

        # Test multiple files in dir to diff of 3 bytes
        assert(abs(Size(SRC).value - sum(s for (_, s) in files) == 0))
    
    @pytest.mark.xfail(raises=AttributeError)
    def test_not_init(self):

        Size.calc(Path('.'))
        
    def test_cache_refresh(self):

        f = SRC / 'Test.Dir/Test.File.mkv'
        Make.mock_file(f, 21 * MB)
        size = Size(f)
        assert(size.value == 21 * MB)
        Delete.dir(SRC / 'Test.Dir')
        assert(size.value == 21 * MB)
        size.refresh()
        assert(not size.value)
        
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
                        
        assert(Size(files[0][0]).pretty() == '1.46 GiB')
        assert(Size(files[0][0]).pretty(units=Units.GB) == '1.57 GB')
        assert(Size(files[0][0]).pretty(precision=1) == '1.5 GiB')
        assert(Size(files[0][0]).pretty(precision=0) == '1 GiB')
        assert(Size(files[0][0]).pretty(units=Units.MiB) == '1,500.0 MiB')
        assert(Size(files[0][0]).pretty(units=Units.MB) == '1,572.9 MB')
        assert(Size(files[1][0]).pretty() == '768.0 MiB')
        assert(Size(files[2][0]).pretty() == '10.0 MiB')
        assert(Size(files[3][0]).pretty() == '100 B')
        assert(Size(files[4][0]).pretty() == '1.25 GiB')
        assert(Size(files[5][0]).pretty() == '700.0 MiB')
