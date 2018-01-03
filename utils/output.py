#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import logging, datetime, sys
import config, stringutils, film
from pyfancy import *

def start():
    log('\n{}{}{}'.format(('-'*50), now, ('-'*50)))
    print("Scanning subfolders and files in " + ', '.join(config.sourceDirs))
    print("Please wait...\n")

def testMode():
    if config.testMode:
        log(' *** TEST MODE *** ')
        pyfancy().magenta('  *** TEST MODE ***\nNo changes will be made\n').output()

# Logging
logging.basicConfig(format='%(message)s', filename=config.logPath + 'history.log',level=logging.DEBUG)

@property
def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def logFilm(film):
    log("{} ({})".format(film.sourcePath, stringutils.prettySize(film.size)))
    if film.title is not None:
        debug("Init film object")
        debug("title\t{}".format(film.title))
        debug("year\t{}".format(film.year))
        debug("edition\t{}".format(film.edition))
        debug("media\t{}".format(film.media))
        debug("quality\t{}".format(film.quality))

def logDetails(text):
    log('\t→ {}'.format(text))

def log(text):
    logging.info('{} ... {}'.format(now, text))

def error(text):
    text = '{} - Error: {}'.format(now, text)
    logging.error(text)
    raise Exception(text)

def disableLogging():
    logging.disable(sys.maxint)

def enableLogging():
    logging.disable(logging.NOTSET)

# Console output

mainPrefix = ' ... '
indentPrefix = '\t→ '

def debug(str):
    if config.debugMode: print(str)

def info(str):
    pyfancy().dark_gray('{}{}'.format(indentPrefix, str)).output()
    logDetails(str)

def interesting(str, highlight):
    pyfancy().white('{}{} '.format(indentPrefix, str)).green(highlight).output()
    logDetails('{}{}'.format(str, highlight))    

def warn(str):
    pyfancy().red('{}{}'.format(indentPrefix, str)).output()
    logDetails(str)

def notice(str):
    pyfancy().dim('{}{}'.format(indentPrefix, str)).output()
    logDetails(str)

def skip(film, str):
    pyfancy().red('{}{}'.format(mainPrefix, film.originalFilename)).dark_gray(' {}'.format(str)).output()
    logDetails(str)

def filmDetails(film): 
    pyfancy().bold("{}{}{} ({})".format(mainPrefix, film.originalFilename, film.ext or '', stringutils.prettySize(film.size))).output()
    if config.TMDb['enabled']:
        if film.id is not None:
            pyfancy().white(indentPrefix).green('✓ {} ({})'.format(film.title, film.year)).dark_gray().add(" [{}]".format(film.id)).output()
            logDetails('✓ {} ({}) [{}]'.format(film.title, film.year, film.id))
        else:
            pyfancy().white(indentPrefix).red('𝗑 {} ({})'.format(film.title, film.year)).output()
            logDetails('𝗑 Not found')