#!/usr/bin/env python

# Fylm
# Copyright 2022 github.com/brandonscript

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

"""Fylm setup module.
"""

from setuptools import setup

# TODO: Replace with Path

import os

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the relevant file.
with open(os.path.join(here, 'README.md'), encoding='markdown') as f:
    long_description = f.read()

# Get requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with open('requirements-test.txt') as f:
    requirements_test = f.read().splitlines()

setup(
    name='Fylm',

    version='0.4.1-beta',

    description='A automated command line app for organizing your film media.',
    long_description=long_description,

    # The project's main homepage
    url='https://github.com/brandonscript/fylm',

    # Author details
    author='Brandon Shelley',
    author_email='brandon@pacificaviator.co',

    # License
    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',

        # Environment
        'Environment :: Console',

        # Indicate who your project is intended for
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia :: Video',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Supported Python versions.
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    # List of runtime dependencies. These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=requirements,

    dependency_links=[
        "git+ssh://git@github.com/Thibauth/python-pushover.git@8522972#egg=python-pushover"
    ],

    # Dev dependencies
    extras_require={
        'test': requirements_test
    },

    # Entry points
    entry_points={
        'console_scripts': ['fylm = fylm:main'],
    },
)