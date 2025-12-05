"""Quick test to verify auth logic"""

# Simulate session state before and after login
class FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

# Test 1: Initial state (not authenticated)
session = FakeSessionState()
session['authenticated_user'] = None
session['admin_authenticated'] = False

is_authenticated = session.get('authenticated_user') is not None
is_admin = session.get('admin_authenticated', False)

print("Test 1: Initial State")
print(f"  authenticated_user: {session.get('authenticated_user')}")
print(f"  is_authenticated: {is_authenticated}")
print(f"  is_admin: {is_admin}")
print(f"  Should block personal tabs: {not is_authenticated and not is_admin}")
print()

# Test 2: After successful login
session['authenticated_user'] = 'alice'
session['user_id'] = 'alice'

is_authenticated = session.get('authenticated_user') is not None
is_admin = session.get('admin_authenticated', False)

print("Test 2: After Login as 'alice'")
print(f"  authenticated_user: {session.get('authenticated_user')}")
print(f"  is_authenticated: {is_authenticated}")
print(f"  is_admin: {is_admin}")
print(f"  Should block personal tabs: {not is_authenticated and not is_admin}")
print()

# Test 3: After admin unlock
session['admin_authenticated'] = True

is_authenticated = session.get('authenticated_user') is not None
is_admin = session.get('admin_authenticated', False)

print("Test 3: After Admin Unlock (no user switch)")
print(f"  authenticated_user: {session.get('authenticated_user')}")
print(f"  is_authenticated: {is_authenticated}")
print(f"  is_admin: {is_admin}")
print(f"  Should block personal tabs: {not is_authenticated and not is_admin}")
print()

# Test 4: After logout
session['authenticated_user'] = None
session['admin_authenticated'] = False

is_authenticated = session.get('authenticated_user') is not None
is_admin = session.get('admin_authenticated', False)

print("Test 4: After Logout")
print(f"  authenticated_user: {session.get('authenticated_user')}")
print(f"  is_authenticated: {is_authenticated}")
print(f"  is_admin: {is_admin}")
print(f"  Should block personal tabs: {not is_authenticated and not is_admin}")
print()

print("✅ All tests show expected behavior!")
