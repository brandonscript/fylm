![version](https://img.shields.io/badge/version-0.2.0--alpha-orange.svg) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/8fcfaf45a6494aedb4b0340461c2b79b)](https://www.codacy.com/app/brandonscript/fylm)

### Overview

Fylm is a wonderful automated command line app for organizing your film media. You can pronounce it **Film** or **File 'em**, whichever you like!

It uses (highly suspect) regular expressions to identify film files (or folders), then looks them up on [TMDb](https://www.themoviedb.org) to get all the correct details. Once that's over and done with, it'll rename them according to your OCD standards, and move them.

### Features

Fylm can:

- Look things up on TMDb so you don't have to.
- Notify your Plex when it adds something new.
- Run completely autonomously, so it can be wired up as a post-script for apps like SABnzbd.
- Automatically renames files, clean junk, and and move the important bits you care about.
- Run in test mode so you can verify search results before committing.
- Log what it does, so if (not saying they will, but if) things go sideways, you can see where things went awry.

### Installing

For now, Fylm is only guaranteed to run on Python 2.7. You can try running it on 3.X and see what happens.

Installing dependencies is simple if you use [`pip`](https://pip.pypa.io/en/stable/installing/). Depending on your OS configuration, you may need to install packages with `sudo`:

- `pip install tmdbsimple`
- `pip install plexapi`
- `pip install future`
- `pip install pyyaml`
- `pip install dotmap`

If you don't use `pip`, then you will need to install these manually, or download them and include them inside your copy of Fylm. Or shake a magic stick and hope it works (hint: it won't).

### Configuring

All of Fylm's options are configured in `config.yaml`. Options of note that you should set up:

- `source_dirs`
- `destination_dir`
- `rename_pattern`
- `tmdb.key`
- `plex.baseurl`
- `plex.token`
- `plex.sections`

### Running

If you don't want or need anything special, simply:

    python fylm

from the root project folder will run the app.

However, since we're putting a lot of faith in machines and automation, there are times when you should walk before you run, and look before you leap. For that, there are several great command line options available to you. Most of these can be configured in config.yaml, but using the command line option will override whatever is in config:

    --quiet, -q
    --test, -t
    --debug, -d
    --limit=n, -l
    --pop=n, -p
    --force-lookup, -f
    --overwrite, -o
    --source
    --no-strict
	
- `quiet` will suppress notifications or updates to services like Plex.
- `test` will run the app in sandbox mode, which means no changes will actually be performed on the filesystem. A good rule of thumb is to always test first before you run the app on a long list of files.
- `debug` will run the app with some extra details (ok, verbose word porridge) in the console.
- `limit=n` limits the number of films to process to `n`.
- `pop=n` will set the minimum acceptable TMDb 'popularity' ranking to `n`.
- `force-lookup` will look everything in your source folder(s) up on TMDb, even if something doesn't appear to be a film. Helpful for finding files with missing years, but can take a lot longer to run.
- `overwrite` will *overwrite* any duplicates at the destination. Use with caution (and run `--test` first!). Also HIGHLY recomment you keep `check_for_duplicates` enabled if you intend to overwrite duplicates, otherwise the Apache 2.0 license isn't liable for lost data.
- `source` overrides your usual `source_dir` setting with a new source folder.
- `no-strict` will dramatically reduce the criteria that is is used to validate TMDb matches. Expect red herrings. Lots. So, `--test` first.

#### Testing

Test coverage is meek. But at least there are tests for the `Film` class. These tests validate that the searching and matching algorithms are working properly.

To run tests:

    cd fylm/
    python -m unittest tests`

<sub>(Bonus points if you send in a PR that allows tests to run from the project root.)</sub>

#### Contributing

Contributions are welcome! Please send in a PR with a clear explanation of what you're adding and why, and where applicable, add tests (a new test class, even!) to validate.