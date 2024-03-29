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
import os
import sys
import shutil
import itertools
import logging
from pathlib import Path
from datetime import timedelta

# Add the cwd to the path so we can load fylmlib modules and fylm app.
sys.path.append(str(Path().cwd().parent / 'fylm'))
sys.path.append(str(Path().cwd() / 'fylm'))
sys.path.append(str(Path().cwd() / 'fylm' / 'fylmlib'))

import pytest
import requests_cache
from addict import Dict

import fylmlib.config as config

from fylmlib import Find, Parser
from make import Make, MakeFilmsResult

# Silence urllib3
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").propagate = False

if os.getenv('_PYTEST_RAISE', "0") != "0":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call):
        raise call.excinfo.value

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo):
        raise excinfo.value

if config.cache:
    requests_cache.install_cache(str(Path('.').resolve(
    ) / '.cache.fylm.test.sqlite'), expire_after=timedelta(hours=120))
    requests_cache.remove_expired_responses()

files_root = Path(__file__).parent

# Configure source and destination paths for test files.
src_path = files_root / 'files/#new'
src_path2 = files_root / 'files/#two'

# Film destination map
dst_paths = {
    '2160p': files_root / 'files/4K',
    '1080p': files_root / 'files/HD',
    '720p': files_root / 'files/HD',
    'SD': files_root / 'files/SD',
    'default': files_root / 'files/SD'
}

all_films = []
valid_films = []

# TODO: Make sure this is enabled when committing.
@pytest.fixture(scope="function", autouse=True)
def setup():

    config.reload()
    cleanup_all()
    Make.empty_dirs()

    from fylmlib import app
    if not app.POOL:
        app.POOL = multiprocessing.Pool(multiprocessing.cpu_count())

    # Console output
    config.no_console = config.debug
    
    # Set quiet to suppress external notifications
    config.quiet = True
    
    # Set default file sizes
    config.min_filesize = Dict({
        '720p': 50,
        '1080p': 100,
        '2160p': 200,
        'SD': 20,
        'default': 20
    })

    # Set dirs
    config.source_dirs = [src_path]
    config.destination_dirs = dst_paths

    # Set default rename mask
    config.rename_pattern.file = r'{title} {(year)} {[edition]} {quality-full} {hdr}'
    config.rename_pattern.folder = r'{title} {(year)}'

    # Load films and filter them into valid films.
    # all_films = ops.Find.new_films([src_path])
    # valid_films = list(filter(lambda film: not film.should_ignore, all_films))

    if os.environ.get('DEBUG') is not None: 
        config.debug = True if os.environ.get('DEBUG').lower() == 'true' else False
    logging.getLogger().setLevel(logging.DEBUG if config.debug else logging.CRITICAL)
    
def remake_files():
    
    cleanup_all()
    Make.all_mock_files()

def cleanup_src():
    global src_path
    global src_path2

    try:
        shutil.rmtree(src_path)
        shutil.rmtree(src_path2)
    except Exception:
        pass
    
def cleanup_dst():
    global dst_paths

    for _, dr in dst_paths.items():
        try:
            shutil.rmtree(dr)
        except Exception:
            pass

def cleanup_all():
    cleanup_src()
    cleanup_dst()
    Find.NEW = None
    Find.EXISTING = None

def desired_path(path, test_film, folders=True):
    assert(test_film.make is not None and path is not None)
    from fylmlib.film import Film
    film = Film(test_film.make[0])
    if not folders:
        path = Path(path).name
    return Path(config.destination_dirs[Parser(film.src).resolution.key] / path)

# Skip cleanup to manually inspect test results
def pytest_sessionfinish(session, exitstatus):
    # return
    cleanup_all()
