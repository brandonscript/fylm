# -*- coding: utf-8 -*-
# Copyright 2018 Brandon Shelley. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Interactive input handler for Fylm.

This module handles all user input during interactive mode.
Credit: https://github.com/jreyesr/better-input

    ask: the main class exported by this module.
"""

from __future__ import unicode_literals, print_function
from builtins import *
import readline

from colors import color, bold

from fylmlib.parser import parser
from fylmlib.console import console
from fylmlib.ansi import ansi

INPUT_PROMPT = '»'
MESSAGE_PREFIX = '      '

class interactive:

    @classmethod
    def verify_film(cls, film):
        """Prompt the user to verify whether the best match is correct.

        Ask the user to verify that the currently detected TMDb match 
        is correct, and offer choices that let the user search or look
        up a different title.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """
        console.ask('Is this correct? [Y]')
        choice = cls._choice_input(
            prompt='', 
            choices=[
                ('Y', 'Yes'), 
                ('N', 'No, search by name'),
                ('I', 'No, lookup by ID'),
                ('S', '[ Skip ]')],
            default='Y')

        film.tmdb_verified = (choice == 0)
        if choice == 1:
            return cls.search_by_name(film)
        elif choice == 2:
            return cls.lookup_by_id(film)
        elif choice == 3:
            film.ignore_reason = 'Skipped'
            console.dim("Skipped")
            return False
        else:
            return film.tmdb_verified              

    @classmethod
    def lookup_by_id(cls, film):
        """Perform an interactive lookup of a film by ID.

        Ask the user for a TMDb ID, then perform a search for that ID.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """
        while True:
            film.tmdb_id = None
            search = cls._simple_input('TMDb ID ')
            try:
                film.tmdb_id = int(search)
                try:
                    film.search_tmdb()
                    console.search_result(film)
                    return cls.verify_film(film)
                except Exception:
                    console.colored("%sHrm, that ID doesn't exist" % MESSAGE_PREFIX, ansi.pink)
            except Exception:
                console.colored("%sA TMDb ID must be a number" % MESSAGE_PREFIX, ansi.pink) 

    @classmethod
    def search_by_name(cls, film):
        """Perform an interactive name search.

        Ask the user for a search query, then perform a search for title, and, 
        if detected, year.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True or False, passing the return value from choose_from_matches
        """
        film.tmdb_id = None
        search = cls._simple_input('Search TMDb ', '%s %s' % (film.title, film.year))
        film.title = parser.get_title(search)
        film.year = parser.get_year(search)
        film.search_tmdb()
        return cls.choose_from_matches(film)


    @classmethod
    def choose_from_matches(cls, film):
        """Choose the correct film from a set of matches.

        Ask the user for input, then map the selected film to the
        current film object.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """
        while len(film.matches) == 0:
            console.colored("%sNo matches found" % MESSAGE_PREFIX, ansi.pink)
            return cls.search_by_name(film)
        if len(film.matches) > 1:
            console.white(bold('%sSearch results:' % console.INDENT_PREFIX))
            choice = cls._choice_input(
                prompt="Select ", 
                choices=['%s (%s) [%s]' % (
                    m.proposed_title, 
                    m.proposed_year, 
                    m.tmdb_id) for m in film.matches] + 
                ['[ Edit search ]', '[ Search by ID ]', '[ Skip ]'],
                enumeration='number')
            if choice == len(film.matches):
                return cls.search_by_name(film)
            elif choice == len(film.matches) + 1:
                return cls.lookup_by_id(film)
            elif choice == len(film.matches) + 2:
                film.tmdb_id = None
                film.ignore_reason = 'Skipped'
                console.dim("Skipped")
                return False
        film.update_with_match(film.matches[choice])
        console.search_result(film)
        return cls.verify_film(film)

    @classmethod
    def _simple_input(cls, prompt, prefill=''):
        """Simple prompt for input

        Ask the user for input. Extremely thin wrapper around the common input() function
        
        Args:
            prompt: (str) Text printed to standard output before reading input
            prefill: (str) Prefilled text
        Returns:
            The user's input
        """
        readline.set_startup_hook(lambda: readline.insert_text(prefill))
        try:
            return input('%s%s ' % (color(console.INDENT_PREFIX + prompt, fg=ansi.pink), INPUT_PROMPT))
        finally:
            readline.set_startup_hook()

    @classmethod
    def _condition_input(cls, prompt, default, prefill='', return_type=str, condition=None, error_message=None):
        """Conditional prompt for input using lambda to verify condition.

        Ask the user for input, checking if it meets a condition function.

        Args:
            prompt: (str) The question the user will be asked
            return_type: (type) The type the user's input will be casted to
            condition: (optional lambda function) An optional check, done AFTER the type cast
            error_message: (str) An optional error message to be shown when an input does not meet the condition
        Returns:
            The user's input, casted to return_type and complying with condition
        """
        while True:
            try:
                answer = return_type(cls._simple_input(prompt, prefill))
            except ValueError:
                print(error_message)
                continue

            if answer == '' and default is not None:
                answer = default
            if condition is not None:
                if condition(answer):
                    return answer
            else:
                return answer
            if error_message is not None:
                print(error_message)

    @classmethod
    def _choice_input(cls, prompt, choices, default=None, prefill='', enumeration='char', error_message=None):
        """Choice-based prompt for input.

        Ask the user for input from a set of choices.

        Args:
            prompt: (str) The question the user will be asked
            choices: (list(str)) A list of choices the user has to select from
            enumeration: (str) Can be 'number' or 'char'. 'char' should only be used when len(choices)<27
            error_message: (str) An optional error message to be shown when an input is not a valid choice
        Returns:
            The index of the selected choice
        """
        if enumeration == 'number':
            chars = [str(x + 1) for x in range(len(choices))]
        elif enumeration == 'char':
            assert len(choices) < 27, "Choices can't be represented by single chars"
            chars = [x[0].title() if isinstance(choices[0], tuple) else x[:1].title() for x in choices]
        else:
            raise ValueError("enumeration is not 'number' or 'char'")

        for c, choice in zip(chars, choices):
            console.choice("{}) {}".format(c, choice[1] if isinstance(choice, tuple) else choice))
        answer = cls._condition_input(prompt, condition=lambda x: x.upper() in chars, default=default, prefill=prefill, error_message=error_message)
        return chars.index(answer.upper())