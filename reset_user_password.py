#!/usr/bin/env python3
"""
reset_user_password.py

Small admin utility to set or clear a user's password for the local storage backend.
Run from the repository root. Example:

# Set a new password (prompts):
python reset_user_password.py alice --set

# Clear password (make account passwordless):
python reset_user_password.py alice --clear

Note: you must run this on the machine that hosts the data files.
"""

import argparse
import getpass
import sys
from storage import get_storage


def main():
    parser = argparse.ArgumentParser(description="Set or clear a user's password for XP Tracker")
    parser.add_argument('username', help='Username to operate on')
    parser.add_argument('--set', dest='do_set', action='store_true', help='Set a new password (prompts)')
    parser.add_argument('--clear', dest='do_clear', action='store_true', help='Clear the password (make account passwordless)')
    args = parser.parse_args()

    storage = get_storage()
    user = args.username

    if args.do_clear:
        confirm = input(f"Are you sure you want to CLEAR the password for user '{user}'? Type YES to confirm: ")
        if confirm != 'YES':
            print('Aborted by user.')
            sys.exit(1)
        storage.set_user_password(user, '')
        print(f"Password cleared for user: {user}")
        sys.exit(0)

    if args.do_set:
        pw1 = getpass.getpass('New password: ')
        pw2 = getpass.getpass('Confirm password: ')
        if pw1 != pw2:
            print('Passwords do not match. Aborting.')
            sys.exit(1)
        if not pw1:
            print('Empty password is not allowed for --set. Use --clear to remove password.')
            sys.exit(1)
        storage.set_user_password(user, pw1)
        print(f"Password set for user: {user}")
        sys.exit(0)

    print('No action specified. Use --set to set a password or --clear to remove it.')
    sys.exit(2)


if __name__ == '__main__':
    main()
