![version](https://img.shields.io/badge/version-0.3.0--beta-green.svg) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/d88f475bb75b424692f0e7201ad3e888)](https://www.codacy.com/gh/brandonscript/fylm/dashboard?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=brandonscript/fylm&amp;utm_campaign=Badge_Grade) [![Build Status](https://travis-ci.org/brandonscript/fylm.svg?branch=master)](https://travis-ci.org/brandonscript/fylm)

<img src="https://i.imgur.com/X53grFH.png" width="200">

### Overview

Fylm is a wonderful automated command line app for organizing your film media. You can pronounce it **Film** or **File 'em**, whichever you like!

It uses (highly suspect) heuristics to identify film files (or folders), then looks them up on [TMDb](https://www.themoviedb.org) to get all the correct details. Once that's over and done with, it'll rename them according to your OCD standards, and move them.

### Features

Fylm can:

- Rename messy files and folders and make them pretty, like

  `high.noon.1952.1080p.this.OTHER-JUNK` » `High Noon (1952) 1080p`
- Look film details up on TMDb so you don't have to, ensuring things are named correctly.
- Check your library for duplicates and allow films with different qualities to be upgraded or ignored.
- Notify your Plex Media Server when it adds something new.
- Be wired up as a post-script for apps like SABnzbd (you'll want to use the `--plaintext` switch).
- Delete extra files you don't want, moving only the important bits you care about.
- Run in test mode so you can verify search results before committing.
- Log what it does, so if (not saying they will, but if) things go sideways, you can see why.
- Send you informative notifications to your phone when it does things.

### Installing

Fylm is tested on 3.5, 3.6, 3.7, and 3.8 and will attempt to adapt as the Python language does.
As of Python 2.7 end of life, 2.X is no longer supported.

Installing dependencies is simple if you use [`pip`](https://pip.pypa.io/en/stable/installing/). Depending on your OS configuration, you may need to install packages with `sudo`:

    (sudo) pip install -r requirements.txt
    // or
    pip3 install -r requirements.txt

If you don't use `pip`, then you will need to install these manually, or download them and include them inside your copy of Fylm. Or shake a magic stick and hope it works (hint: it won't).

### Configuring

All of Fylm's options are configured in `config.yaml`. Options of note that you should set up:

- source_dirs
- destination_dir
- rename_pattern
- tmdb.key
- plex.baseurl
- plex.token
- plex.sections
- pushover

If you're using Pushover, you might also want to add the [Fylm logo](https://imgur.com/a/wm3LS) to your app.

### Running

If you don't want or need anything special, simply:

    python fylm

from the root project folder will run the app.

However, since we're putting a lot of faith in machines and automation, there are times when you should walk before you run, and look before you leap. For that, there are several great command line options available to you. Most of these can be configured in config.yaml, but using the command line option will override whatever is in config:

    --quiet, -q
    --test, -t
    --debug, -d
    --rename, -r
    --copy, -c
    --move, -m
    --hide-skipped
    --interactive, -i
    --limit=n, -l
    --pop=n, -p
    --force-lookup, -f
    --no-duplicates, -d
    --overwrite, -o
    --source, -s
    --no-strict
    --no-console
    --plaintext
    
- `quiet` will suppress notifications or updates to services like Plex.
- `test` will run the app in sandbox mode, which means no changes will actually be performed on the filesystem. A good rule of thumb is to always test first before you run the app on a long list of files.
- `debug` will run the app with some extra details (ok, verbose word porridge) in the console.
- `rename` will just rename files and folders and leave them in the source folder.
- `copy` will force files on the same partition to be copied and verified instead of moved.
- `move` will force the behavior of move even if source and destination are on different partitions.
- `hide-skipped` will hide files and folders that are skipped from the console output. Ignored in interactive mode.
- `interactive` prompt to confirm or correct TMDb matches.
- `limit=n` limits the number of films to process to `n`.
- `pop=n` will set the minimum acceptable TMDb 'popularity' ranking to `n`.
- `force-lookup` will look everything in your source folder(s) up on TMDb, even if something doesn't appear to be a film. Helpful for finding files with missing years, but can take a lot longer to run.
- `no-duplicates` will disable duplicate checking entirely.
- `overwrite` means thatany duplicates it finds at the destination will be *overwritten*. Use with caution (and run `--test` first!). Also HIGHLY recomment you keep `check_for_duplicates` enabled if you intend to overwrite duplicates, otherwise the Apache 2.0 license isn't liable for lost data.
- `source` overrides your usual `source_dir` setting with new source folder(s). Comma separate multiple folders.
- `no-strict` will dramatically reduce the criteria that is is used to validate TMDb matches. Expect red herrings. Lots. So, `--test` first.
- `no-console` will completely suppress console output. If you wanted that, for some reason.
- `plaintext` will output to the console without pretty formatting. You'll want to use this option with SABnzbd.

#### Testing

Tests are run using `pytest`. To install:

    (sudo) pip install -r requirements-test.txt

To run tests:

    cd fylm/
    python -m pytest -xq (--no-print-logs)

#### Contributing

Contributions are welcome! Please send in a PR with a clear explanation of what you're adding and why, and where applicable, add tests (a new test class, even!) to validate.

#### Credits

Murcury icon by [Freepik](https://www.flaticon.com/authors/freepik) from [www.flaticon.com](http://www.flaticon.com/).

Special thanks to [Pyfancy()](https://github.com/ilovecode1/Pyfancy-2) and [colors](https://github.com/jonathaneunice/colors/).

