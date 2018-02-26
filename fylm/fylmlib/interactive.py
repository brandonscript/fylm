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

import fylmlib.config as config
from fylmlib.parser import parser
from fylmlib.console import console
from fylmlib.ansi import ansi

INPUT_PROMPT = '»'
MESSAGE_PREFIX = '      '

class interactive:

    @classmethod
    def process(cls, film, mock_inputs=None):
        """Main router for handling a known or unknown film.

        Determines whether the user should be prompted to verify a
        matching film, or look up an unknown one.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True if the film passes verification or interactive mode is 
            disabled, else False
        """
        if config.interactive is False:
            raise Exception('Interactive mode is not enabled')

        if film.should_ignore:
            return cls.handle_unknown_film(film, mock_inputs)
        else:
            # Search TMDb for film details (if enabled).
            film.search_tmdb()
            return cls.verify_film(film, mock_inputs)

    @classmethod
    def verify_film(cls, film, mock_inputs):
        """Prompt the user to verify whether the best match is correct.

        Ask the user to verify that the currently detected TMDb match 
        is correct, and offer choices that let the user search or look
        up a different title.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True if the film passes verification, else False
        """

        _shift(mock_inputs)

        console.search_result(film)
        console.ask('Is this correct? [Y]')
        choice = cls._choice_input(
            prompt='', 
            choices=[
                ('Y', 'Yes'), 
                ('N', 'No, search by name'),
                ('I', 'No, lookup by ID'),
                ('S', '[ Skip ]')],
            default='Y',
            mock_input=_first(mock_inputs))

        film.tmdb_verified = (choice == 0)
        if choice == 1:
            return cls.search_by_name(film, mock_inputs)
        elif choice == 2:
            return cls.lookup_by_id(film, mock_inputs)
        elif choice == 3:
            film.ignore_reason = 'Skipped'
            console.dim("Skipped")
            return False
        else:
            return film.tmdb_verified  

    @classmethod
    def handle_unknown_film(cls, film, mock_inputs):
        """Ask the user whether an unknown film should be manually 
        searched for or skipped.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True if the film should be processed, else False
        """ 
        console.ask("%s [N]" % film.ignore_reason)

        # Continuously loop this if an invalid choice is entered.
        while True:
            choice = cls._choice_input(
                prompt='', 
                choices=[
                    ('N', 'Search by name'),
                    ('I', 'Lookup by ID'),
                    ('S', '[ Skip ]')],
                default='N', 
                mock_input=_first(mock_inputs))

            if choice == 0:
                return cls.search_by_name(film, mock_inputs)
            elif choice == 1:
                return cls.lookup_by_id(film, mock_inputs)
            elif choice == 2:
                film.ignore_reason = 'Skipped'
                console.dim("Skipped")
                return False           

    @classmethod
    def lookup_by_id(cls, film, mock_inputs):
        """Perform an interactive lookup of a film by ID.

        Ask the user for a TMDb ID, then perform a search for that ID.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True if the film passes verification, else False
        """
        _shift(mock_inputs)

        while True:

            # Delete the existing ID in case it is a mismatch.
            film.tmdb_id = None
            search = cls._simple_input('TMDb ID ', mock_input=_first(mock_inputs))
            try:
                # Attempt to convert the search query to an int and update
                # the film.
                film.tmdb_id = int(search)
                try:
                    # Search for the new film by ID.
                    film.search_tmdb()

                    # Verify the search result.
                    return cls.verify_film(film, mock_inputs)
                except Exception as e:
                    console.colored("%sHrm, that ID doesn't exist" % MESSAGE_PREFIX, ansi.pink)
                    console.debug(e)
            except Exception as e:
                console.colored("%sA TMDb ID must be a number" % MESSAGE_PREFIX, ansi.pink) 
                console.debug(e)

    @classmethod
    def search_by_name(cls, film, mock_inputs):
        """Perform an interactive name search.

        Ask the user for a search query, then perform a search for title, and, 
        if detected, year.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True or False, passing the return value from choose_from_matches
        """

        _shift(mock_inputs)

        film.tmdb_id = None
        search = cls._simple_input('Search TMDb ', '%s %s' % (film.title, film.year or ''), mock_input=_first(mock_inputs))
        film.title = parser.get_title(search)
        film.year = parser.get_year(search)
        film.search_tmdb()
        return cls.choose_from_matches(film, mock_inputs)


    @classmethod
    def choose_from_matches(cls, film, mock_inputs):
        """Choose the correct film from a set of matches.

        Ask the user for input, then map the selected film to the
        current film object.
        
        Args:
            film: (Film) Current film to process
            mock_inputs: (list) A set of mock input responses for tests
        Returns:
            True if the film passes verification, else False
        """

        # If no matches are found, continually prompt user to find a correct match.

        _shift(mock_inputs)

        while len(film.matches) == 0:
            console.colored("%sNo matches found" % MESSAGE_PREFIX, ansi.pink)
            return cls.search_by_name(film, mock_inputs)

        console.white(bold('%sSearch results:' % console.INDENT_PREFIX))

        # Generate a list of choices based on search results and save the input
        # to `choice`.
        choice = cls._choice_input(
            prompt="Select ", 
            choices=['%s (%s) [%s]' % (
                m.proposed_title, 
                m.proposed_year, 
                m.tmdb_id) for m in film.matches] + 
            ['[ Edit search ]', '[ Search by ID ]', '[ Skip ]'],
            enumeration='number',
            mock_input=_first(mock_inputs))

        # If 'Edit search' was selected, try again, then forward
        # the return value.
        if choice == len(film.matches):
            return cls.search_by_name(film, mock_inputs)

        # If 'Search by ID' was selected, redirect to ID lookup, then forward
        # the return value.
        elif choice == len(film.matches) + 1:
            return cls.lookup_by_id(film, mock_inputs)

        # If skipping, return False
        elif choice == len(film.matches) + 2:
            film.tmdb_id = None
            film.ignore_reason = 'Skipped'
            console.dim("Skipped")
            return False

        # If we haven't returned yet, update the film with the selected match 
        # and mark it as verified.
        film.update_with_match(film.matches[choice])
        film.tmdb_verified = True

        console.search_result(film)
        return True

    @classmethod
    def _simple_input(cls, prompt, prefill='', mock_input=None):
        """Simple prompt for input

        Ask the user for input. Extremely thin wrapper around the common input() function
        
        Args:
            prompt: (str) Text printed to standard output before reading input
            prefill: (str) Prefilled text
            mock_input: (char) A mock input response for tests
        Returns:
            The user's input
        """
        if mock_input is not None:
            return mock_input

        readline.set_startup_hook(lambda: readline.insert_text(prefill))
        try:
            return input('%s%s ' % (color(console.INDENT_PREFIX + prompt, fg=ansi.pink), INPUT_PROMPT))
        finally:
            readline.set_startup_hook()

    @classmethod
    def _condition_input(cls, prompt, default, prefill='', return_type=str, condition=None, error_message=None, mock_input=None):
        """Conditional prompt for input using lambda to verify condition.

        Ask the user for input, checking if it meets a condition function.

        Args:
            prompt: (str) The question the user will be asked
            return_type: (type) The type the user's input will be casted to
            condition: (optional lambda function) An optional check, done AFTER the type cast
            error_message: (str) An optional error message to be shown when an input does not meet the condition
            mock_input: (char) A mock input response for tests
        Returns:
            The user's input, casted to return_type and complying with condition
        """


        while True:
            try:
                answer = return_type(cls._simple_input(prompt, prefill, mock_input=mock_input))
            except ValueError:
                print(error_message)
                continue

            if answer == '' and default is not None:
                answer = default
            
            if condition is not None:
                if condition(answer):
                    return answer
                elif mock_input is not None:
                    raise ValueError(str(mock_input) + ' is not a valid mock ValueError')
            else:
                return answer
            if error_message is not None:
                print(error_message)

    @classmethod
    def _choice_input(cls, prompt, choices, default=None, prefill='', enumeration='char', error_message=None, mock_input=None):
        """Choice-based prompt for input.

        Ask the user for input from a set of choices.

        Args:
            prompt: (str) The question the user will be asked
            choices: (list(str)) A list of choices the user has to select from
            enumeration: (str) Can be 'number' or 'char'. 'char' should only be used when len(choices)<27
            error_message: (str) An optional error message to be shown when an input is not a valid choice
            mock_input: (char) A mock input response for tests
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

        answer = cls._condition_input(
            prompt, 
            condition=lambda x: x.upper() in chars, 
            default=default, 
            prefill=prefill, 
            error_message=error_message, 
            mock_input=mock_input)
        return chars.index(answer.upper())

def _shift(l):
    try:
        l.pop(0)
    except Exception:
        pass

def _first(l):
    try:
        return l[0]
    except Exception:
        return l