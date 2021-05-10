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

"""Interactive input handler for Fylm.

This module handles all user input during interactive mode.
Credit: https://github.com/jreyesr/better-input

    ask: the main class exported by this module.
"""

import readline
import os

from colors import color

from fylmlib.enums import *
from fylmlib.tools import *
import fylmlib.config as config
from fylmlib import Parser
from fylmlib import Console
from fylmlib import Delete
from fylmlib import Duplicates
from fylmlib import Format as ƒ
from fylmlib import Film
ansi = Console.ansi

InteractiveKeyMode = Enum('InteractiveKeyMode', 'CHAR NUMBER TUPLE')

class Interactive:

    @classmethod
    def lookup(cls, film) -> bool:
        """Main router for handling a known or unknown film.

        Determines whether the user should be prompted to verify a
        matching film, or look up an unknown one.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """

        if config.interactive is False:
            return True

        # If it's ignored for an irredeemable reason, return False
        if film.should_ignore and not film.ignore_reason in [
                IgnoreReason.UNKNOWN_YEAR,
                IgnoreReason.TOO_SMALL,
                IgnoreReason.NO_TMDB_RESULTS]:
            return False
        elif film.should_ignore:
            return cls.handle_unknown_film(film)
        else:
            return cls.verify_film(film)

    @classmethod
    def handle_duplicates(cls, film) -> bool:
        """Prompt the user to handle duplicates of a film.

        Determines how to handle duplicates of the inbound film, either
        replacing, keeping both, or skipping.
        
        Args:
            film: (Film) Current film to process
        Returns:
            bool: Returns True if this file should be moved, otherwise False
        """
                
        if config.interactive is False:
            return False
        
        if film.should_ignore:
            return False

        # Return immediately if the film is not a duplicate
        if len(film.duplicates) == 0:
            return True
        
        move = []

        Reason = ComparisonReason
        Result = ComparisonResult
        # In case there are multiple video files in the original film, 
        # we need to process each separately.
        for v in film.video_files:

            mp = film.duplicates.map(v)
            Console.print_duplicates(v, mp)

            choices = []
            existing_to_delete = []

            exact = first(mp, where=lambda d: v.dst == d.duplicate.src, default=None)
            same_quality = list(filter(lambda d: d.result == Result.EQUAL, mp))
            keep_existing = [d for d in mp if d.action == Should.KEEP_EXISTING]
            keep_both = [d for d in mp if d.action == Should.KEEP_BOTH]
            upgradable = [d for d in mp if d.action == Should.UPGRADE]

            if exact:
                # TODO: support better inline styles. Should choices just take a Console?
                if exact.result == Result.HIGHER:
                    only = color('only', style='underline') if len(same_quality) > 1 else ''
                    choices.append(f"Upgrade existing (smaller) copy {only}")
                else:
                    choices.append("Replace existing copy anyway (not an upgrade)")
            if not exact and len(same_quality) > 0:
                c = Console().yellow(INDENT_WIDE, '‹!› ')
                c.add('Existing', 'files are' if len(same_quality) > 1 else 'file is')
                c.add(' not in the expected destination folder')
                c.print()
            if len(upgradable) > 0 and len(keep_existing) == 0:
                qty = len(upgradable)
                if qty > 2:
                    choices.append(
                        ('A', f"Upgrade all {ƒ.num_to_words(qty)} "\
                              f"lower quality {ƒ.pluralize('version', qty)}"))
                elif qty == 1 and not exact:
                    choices.append(('U',
                                    "Upgrade existing lower quality version"))
                
            if len(keep_both) > 0:
                choices.append(f"Keep this file (and existing {ƒ.pluralize('version', len(film.duplicates.files))})")
            elif len(keep_existing) > 0 and not exact:
                choices.append(f"Keep this file anyway")
                
            choices.extend([f"Delete this file (keep existing {ƒ.pluralize('version', len(film.duplicates.files))})",
                            ('S', '[ Skip ]')])

            (choice, letter) = cls._choice_input(
                prompt='', 
                choices=choices,
                default=None,
                mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)
            
            if choice == len(choices) - 1:
                continue
            
            if letter == 'A':
                existing_to_delete.extend(upgradable)
            elif choice == 0 and exact:
                existing_to_delete.append(exact)

            # Keep (move/copy) this file, and prep anything marked for upgrade
            if choice == 0 or (choice == 1 and letter == 'A'):
                film.ignore_reason = None # Reset ignore reason just in case this has changed
                # If there were duplicates, and this film is upgrading/replacing, remove them
                if len(existing_to_delete) > 0:
                    for mp in existing_to_delete:
                        # Mark the existing duplicate for deletion
                        mp.action = Should.DELETE_EXISTING
                        mp.reason = ComparisonReason.MANUALLY_SET
                    Duplicates.rename_unwanted(list(set(existing_to_delete)))
            
            # Delete this file (last choice is always skip, second last is delete)
            elif choice == len(choices) - 2:

                # Ask user to confirm destructive action
                Console.print_ask(
                    f"Are you sure you want to delete '{v.src}'?")
                confirm_delete = cls._choice_input(
                    prompt='',
                    choices=['Yes (delete it)', 'No (keep it)'],
                    default=None,
                    mock_input=_first(config.mock_input))

                config.mock_input = _shift(config.mock_input)

                if confirm_delete == 0:
                    if Delete.path(film.src, force=True):
                        Console().red(INDENT_WIDE, f'Deleted {FAIL}').print()
                        continue
        
            move.append(v)
            
        if len(move) == 0:
            film.ignore_reason = IgnoreReason.SKIP
            return False
        else:
            return True
            
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
        
        if len(film.tmdb_matches) == 0:
            cls.handle_unknown_film(film)
        
        else:
            Console.print_ask('Is this correct? [Y]')
            (choice, letter) = cls._choice_input(
            prompt='', 
            choices=[
                ('Y', 'Yes'), 
                ('N', 'No, search by name'),
                ('I', 'No, lookup by ID'),
                ('S', '[ Skip ]')],
            default='Y',
            mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)

            film.tmdb.ia_accepted = (choice == 0)
            if choice == 1:
                return cls.search_by_name(film)
            elif choice == 2:
                return cls.search_by_id(film)
            elif choice == 3:
                film.ignore_reason = IgnoreReason.SKIP
                return False
            else:
                # User is happy with the result, verify
                return film.tmdb.ia_accepted

    @classmethod
    def handle_unknown_film(cls, film):
        """Ask the user whether an unknown film should be manually 
        searched for or skipped.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film should be processed, else False
        """      
        Console.print_ask(f"{film.ignore_reason.display_name.capitalize()} [N]")

        # Continuously loop this if an invalid choice is entered.
        while True:
            (choice, letter) = cls._choice_input(
                prompt='', 
                choices=[
                    ('N', 'Search by name'),
                    ('I', 'Lookup by ID'),
                    ('S', '[ Skip ]')],
                default='N', 
                mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)

            if choice == 0:
                return cls.search_by_name(film)
            elif choice == 1:
                return cls.search_by_id(film)
            elif choice == 2:
                film.ignore_reason = IgnoreReason.SKIP
                return False           

    @classmethod
    def search_by_id(cls, film):
        """Perform an interactive lookup of a film by ID.

        Ask the user for a TMDb ID, then perform a search for that ID.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """
        while True:

            # Delete the existing ID in case it is a mismatch.
            film.tmdb.id = None
            search = cls._simple_input('TMDb ID: ', mock_input=_first(config.mock_input))
            config.mock_input = _shift(config.mock_input)
            try:
                # Attempt to convert the search query to an int
                film.tmdb.id = int(search)
            except ValueError:
                Console.print_interactive_error("A TMDb ID must be a number")
            
            # Search for the new film by ID.
            film.search_tmdb_sync()
            if film.tmdb.is_verified is True:
                Console.print_interactive_uncertain(film)
                return cls.verify_film(film)
            else:
                Console.print_interactive_error(f"No results found for '{film.tmdb.id}'")
            

    _last_search = None

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

        # Delete the existing ID in case it is a mismatch.
        film.tmdb.id = None
        query = cls._simple_input("Search TMDb: ", 
                                  cls._last_search or film.name, 
                                  mock_input=_first(config.mock_input))
        config.mock_input = _shift(config.mock_input)
        cls._last_search = query
        if query == '':
            return cls.handle_unknown_film(film)
        p = Parser(query)
        film.title = p.title
        film.year = p.year
        film.search_tmdb_sync()
        return cls.choose_from_matches(film, query)


    @classmethod
    def choose_from_matches(cls, film, query):
        """Choose the correct film from a set of matches.

        Ask the user for input, then map the selected film to the
        current film object.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """

        # If no matches are found, continually prompt user to find a correct match.

        while len(film.tmdb_matches) == 0:
            return cls.handle_unknown_film(film)

        Console().add(INDENT_WIDE).bold().white('Search results:').print()

        # Generate a list of choices based on search results and save the input
        # to `choice`.
        choices = [(i + 1, f"{m.new_title} ({m.new_year}) [{m.id}]") for i, m in 
                   enumerate(film.tmdb_matches)]
        (choice, letter) = cls._choice_input(
            prompt="", 
            choices=choices + [
                ('N', '[ New search ]'),
                ('I', '[ Lookup by ID ]'),
                ('S', '[ Skip ]')],
            # choices=[f"{m.new_title} ({m.new_year}) [{m.id}]" for m in film.tmdb_matches] + 
            # ['[ New search ]', '[ Search by ID ]', '[ Skip ]'],
            enumeration=InteractiveKeyMode.TUPLE,
            mock_input=_first(config.mock_input))

        config.mock_input = _shift(config.mock_input)

        # If 'Edit search' was selected, try again, then forward
        # the return value.
        if choice == len(film.tmdb_matches):
            return cls.search_by_name(film)

        # If 'Search by ID' was selected, redirect to ID lookup, then forward
        # the return value.
        elif choice == len(film.tmdb_matches) + 1:
            return cls.search_by_id(film)

        # If skipping, return False
        elif choice == len(film.tmdb_matches) + 2:
            film.id = None
            film.ignore_reason = IgnoreReason.SKIP
            Console.print_interactive_skipped()
            return False

        # If we haven't returned yet, update the film with the selected match 
        # and mark it as verified.
        
        film.tmdb_matches[choice].update(film)
        film.tmdb.ia_accepted = True

        Console.print_interactive_success(film)
        return True

    @classmethod
    # TODO: Refactor into an Input class
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
            return Console.get_input(prompt)
        finally:
            readline.set_startup_hook()

    @classmethod
    def _condition_input(cls, 
                         prompt, 
                         default, 
                         prefill='', 
                         return_type=str, 
                         condition=None, 
                         error_message=None, 
                         mock_input=None):
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
                    raise ValueError(str(mock_input) + ' is not a valid mock value')
            else:
                return answer
            if error_message is not None:
                print(error_message)

    @classmethod
    def _choice_input(cls, 
                      prompt, 
                      choices, 
                      default=None, 
                      prefill='', 
                      enumeration=InteractiveKeyMode.CHAR, 
                      error_message=None, 
                      mock_input=None) -> (int, str):
        """Choice-based prompt for input.

        Ask the user for input from a set of choices.

        Args:
            prompt: (str) The question the user will be asked
            choices: (list(str)) A list of choices the user has to select from
            enumeration: (str) Can be InteractiveKeyMode.NUMBER or .CHAR. CHAR should only be used when len(choices)<27
            error_message: (str) An optional error message to be shown when an input is not a valid choice
            mock_input: (char) A mock input response for tests
        Returns:
            Tuple representing (the index of the selected choice, 
                                the first letter (uppercase) of the choice)
        """
        if enumeration == InteractiveKeyMode.NUMBER:
            chars = [str(x + 1) for x in range(len(choices))]
        elif enumeration == InteractiveKeyMode.CHAR:
            assert len(choices) < 27, "To many choices to be represented by single letters"
            chars = [x[0].title() if isinstance(x, tuple) else x[:1].title() for x in choices]
            choices = [x[1] if isinstance(x, tuple) else x for x in choices]
        elif enumeration == InteractiveKeyMode.TUPLE:
            chars = [str(x[0]).title() for x in choices]
            choices = [x[1] for x in choices]
        else:
            raise ValueError("'enumeration' is not a valid InteractiveKeyMode value.")

        for idx, choice in zip(chars, choices):
            Console.print_choice(idx, choice)

        answer = cls._condition_input(
            prompt, 
            condition=lambda x: x.upper() in chars, 
            default=default, 
            prefill=prefill, 
            error_message=error_message, 
            mock_input=mock_input)
        return (chars.index(answer.upper()), answer.upper())

# FIXME: Move to tools
def _shift(l):
    try:
        l.pop(0)
    except Exception:
        pass
    return l

def _first(l):
    try:
        return l[0]
    except Exception:
        return l
