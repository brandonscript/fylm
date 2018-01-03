#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import re

year = re.compile(r'.+(?P<year>19[1-9]\d|20[0-9]\d|21[0-5]\d)') # Match year from 1910-2159, not at the beginning of the filename
quality = re.compile(r'(?P<quality>(?:72|108|216)0p?)', re.I) # Match 720p, 1080p, of 2160p
media = re.compile(r'(?:(?P<bluray>bluray|bdremux)|(?P<web>web-?dl|webrip))', re.I) # Match BluRay or WEB-DL
cleanTitle = re.compile(r'([\._·\-\[\]{}\(\)]|[\s\W]+$)') # Clean chars ._-{}[]() from entire title, non-word chars and whitespace from end of string
stripArticles = re.compile(r'(^(the|a)\s|, the$)', re.I) # Strip The, A from beginning, and , the from end of string
