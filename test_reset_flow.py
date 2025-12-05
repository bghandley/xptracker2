"""Simple smoke test for password reset token flow.
Run: python test_reset_flow.py
"""
from storage import get_storage
import os


def run():
    storage = get_storage()
    user = 'ci_test_user'

    # Ensure user exists
    storage.load_data(user)
    storage.set_user_email(user, 'ci_test_user@example.com')

    token = storage.create_password_reset_token(user, expires_in=10)
    if not token:
        print('Failed to create token')
        return
    print('Token created:', token)

    ok = storage.verify_and_consume_reset_token(user, token)
    print('First verify (should be True):', ok)

    ok2 = storage.verify_and_consume_reset_token(user, token)
    print('Second verify (should be False):', ok2)

    # Clean up test file
    filename = f"xp_data_{user}.json"
    if os.path.exists(filename):
        os.remove(filename)


if __name__ == '__main__':
    run()
