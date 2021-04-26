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

from fylmlib.enums import *
import fylmlib.config as config
import fylmlib.parser as Parser
import fylmlib.console as Console
import fylmlib.duplicates as Duplicates
import fylmlib.formatter as formatter
import fylmlib.operations as ops

class Interactive:

    @classmethod
    def lookup(cls, film):
        """Main router for handling a known or unknown film.

        Determines whether the user should be prompted to verify a
        matching film, or look up an unknown one.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film passes verification, else False
        """

        if config.interactive is False:
            raise Exception('Interactive mode is not enabled')

        if film.should_ignore:
            return cls.handle_unknown_film(film)
        else:
            # Search TMDb for film details (if enabled).
            film.search_tmdb_sync()
            return cls.verify_film(film)

    @classmethod
    def handle_duplicates(cls, film):
        """Prompt the user to handle duplicates of a film.

        Determines how to handle duplicates of the inbound film, either
        replacing, keeping both, or skipping.
        
        Args:
            film: (Film) Current film to process
        Returns:
            False if deleting this or skipping this film, otherwise True
            (if True, it will be processed)
        """
        if config.interactive is False:
            raise Exception('Interactive mode is not enabled')

        # Return immediately if the film is not a duplicate
        if len(film.duplicate_files) == 0:
            return True

        console().print_duplicate_lines(film)

        choices = []

        # Get exact duplicates
        exact_duplicates = duplicates.find_exact(film)

        # Find all lower quality duplicates that are marked as upgradable (i.e., in the upgrade table)
        # TODO: This is probably very circular and could be improved a lot.
        upgradable_files = [l for l in duplicates.find_lower_quality(film) if l.duplicate_action == Should.UPGRADE]

        duplicates_to_delete = []
        
        if len(exact_duplicates) > 0:
            # If there are any exact duplicates, choose the one at the destination that would be overwritten if possible
            exact = next((d for d in exact_duplicates if d.destination_path == film.destination_path), exact_duplicates[0])
            duplicates_to_delete.append(exact)
            # If the duplicate is smaller than the current primary file, consider it an upgrade, otherwise a replace.
            (s, a) = ('Upgrade', '') if exact.size < film.primary_file.size else ('Replace', ' anyway')
            choices.append(f"{s} existing film '{exact.new_filename_and_ext}'{a} ({formatter.pretty_size(exact.size)})")
        else:
            # If there are no upgradable files, but still duplicates detected, 
            # the only choice should be keep (not upgrade or replace)
            if len(upgradable_files) == 0 and len(film.duplicate_files) > 0:
                choices.append(f"Keep this file (and existing {formatter.pluralize('film', len(film.duplicate_files))})")
            else:    
                choices.append(f"Upgrade {len(upgradable_files)} existing lower quality {formatter.pluralize('film', len(upgradable_files))}")
                duplicates_to_delete = upgradable_files

        choices.extend([f"Delete this file (keep existing {formatter.pluralize('film', len(film.duplicate_files))})",
                        ('S', '[ Skip ]')])

        choice = cls._choice_input(
            prompt='', 
            choices=choices,
            default=None,
            mock_input=_first(config.mock_input))

        config.mock_input = _shift(config.mock_input)

        # Keep (move/copy) this file
        if choice == 0:
            film.ignore_reason = None # Reset ignore reason just in case this has changed
            # If there were duplicates, and this film is upgrading/replacing, remove them
            if len(duplicates_to_delete) > 0:
                for d in duplicates_to_delete:
                    # Mark the duplicate for upgrading
                    d.duplicate_action = Should.UPGRADE
                duplicates.rename_unwanted(film, duplicates_to_delete)
            return True
        
        # Delete this file (last choice is always skip, second last is delete)
        elif choice == len(choices) - 2:

            # Ask user to confirm destructive action
            console().print_ask(
                f"Are you sure you want to delete '{film.source_path}?'")
            confirm_delete = cls._choice_input(
                prompt='',
                choices=['Yes – delete it', 'No – keep it'],
                default=None,
                mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)

            if confirm_delete == 0:
                cls.delete_and_keep_existing(film)

            return False
        
        # Skipping (or default)
        else:
            return False

    @classmethod
    def delete_and_keep_existing(cls, film):
        """Keep the current duplicate instead of the current film

        Args:
            film: (Film) Current film being processed, to be deleted
        """
        if film.is_folder:
            ops.dirops.delete_dir_and_contents(film.source_path, max_size=-1)
        else:
            ops.fileops.delete(film.source_path)

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

        # TODO: When a bad lookup is found (Mars Quest for Life 1080p (2009).mkv), if fixed by a good match, should be green in interactive rename, not red

        console().print_search_result(film)
        
        if len(film.matches) > 0:        
            console().print_ask('Is this correct? [Y]')
            choice = cls._choice_input(
            prompt='', 
            choices=[
                ('Y', 'Yes'), 
                ('N', 'No, search by name'),
                ('I', 'No, lookup by ID'),
                ('S', '[ Skip ]')],
            default='Y',
            mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)

            film.tmdb_verified = (choice == 0)

            if choice == 1:
                return cls.search_by_name(film)
            elif choice == 2:
                return cls.lookup_by_id(film)
            elif choice == 3:
                film.ignore_reason = 'Skipped'
                console().print_interactive_skipped()
                return False
            else:
                # User is happy with the result, verify
                return film.tmdb_verified  

        else:
            console().print_ask('No matches found')
            choice = cls._choice_input(
            prompt='', 
            choices=[
                ('N', 'Search by name'),
                ('I', 'Lookup by ID'),
                ('S', '[ Skip ]')],
            mock_input=_first(config.mock_input))

            config.mock_input = _shift(config.mock_input)

            if choice == 0:
                return cls.search_by_name(film)
            elif choice == 1:
                return cls.lookup_by_id(film)
            elif choice == 2:
                film.ignore_reason = 'Skipped'
                console().print_interactive_skipped()
                return False

    @classmethod
    def handle_unknown_film(cls, film):
        """Ask the user whether an unknown film should be manually 
        searched for or skipped.
        
        Args:
            film: (Film) Current film to process
        Returns:
            True if the film should be processed, else False
        """      

        console().print_ask(f"{film.ignore_reason} [N]")

        # Continuously loop this if an invalid choice is entered.
        while True:
            choice = cls._choice_input(
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
                return cls.lookup_by_id(film)
            elif choice == 2:
                film.ignore_reason = 'Skipped'
                console().print_interactive_skipped()
                return False           

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

            # Delete the existing ID in case it is a mismatch.
            film.tmdb_id = None
            search = cls._simple_input('TMDb ID: ', mock_input=_first(config.mock_input))
            config.mock_input = _shift(config.mock_input)
            try:
                # Attempt to convert the search query to an int and update
                # the film.
                film.tmdb_id = int(search)
                try:
                    # Search for the new film by ID.
                    film.search_tmdb_sync()

                    # Verify the search result.
                    return cls.verify_film(film)
                except Exception as e:
                    console().print_interactive_error("Hrm, that ID doesn't exist")
                    debug(e)
            except Exception as e:
                console().print_interactive_error("A TMDb ID must be a number")
                debug(e)

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
        film.tmdb_id = None
        query = cls._simple_input("Search TMDb: ", 
            f"{film.title or ''}{' ' if film.title else ''}{film.year or ''}", 
            mock_input=_first(config.mock_input))
        config.mock_input = _shift(config.mock_input)
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

        while len(film.matches) == 0:
            return cls.handle_unknown_film(film)

        console().indent().bold().white('Search results:').print()

        # Generate a list of choices based on search results and save the input
        # to `choice`.
        choice = cls._choice_input(
            prompt="", 
            choices=[f"{m.proposed_title} ({m.proposed_year}) [{m.tmdb_id}]" for m in film.matches] + 
            ['[ New search ]', '[ Search by ID ]', '[ Skip ]'],
            enumeration='number',
            mock_input=_first(config.mock_input))

        config.mock_input = _shift(config.mock_input)

        # If 'Edit search' was selected, try again, then forward
        # the return value.
        if choice == len(film.matches):
            return cls.search_by_name(film)

        # If 'Search by ID' was selected, redirect to ID lookup, then forward
        # the return value.
        elif choice == len(film.matches) + 1:
            return cls.lookup_by_id(film)

        # If skipping, return False
        elif choice == len(film.matches) + 2:
            film.tmdb_id = None
            film.ignore_reason = 'Skipped'
            console().print_interactive_skipped()
            return False

        # If we haven't returned yet, update the film with the selected match 
        # and mark it as verified.
        film.update_with_match(film.matches[choice])
        film.tmdb_verified = True

        console().print_search_result(film)
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
            return console.get_input(prompt)
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
                    raise ValueError(str(mock_input) + ' is not a valid mock value')
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
            assert len(choices) < 27, "To many choices to be represented by single letters"
            chars = [x[0].title() if isinstance(x, tuple) else x[:1].title() for x in choices]
            choices = [x[1] if isinstance(x, tuple) else x for x in choices]
        else:
            raise ValueError("enumeration is not 'number' or 'char'")

        for idx, choice in zip(chars, choices):
            console().print_choice(idx, choice)

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
    return l

def _first(l):
    try:
        return l[0]
    except Exception:
        return l
