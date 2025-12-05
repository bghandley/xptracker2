"""Test email validation function"""

from storage import validate_email

# Test cases
test_cases = [
    # (email, expected_valid, description)
    ("user@example.com", True, "Valid standard email"),
    ("john.doe@company.co.uk", True, "Valid with subdomain"),
    ("test+tag@gmail.com", True, "Valid with plus sign"),
    ("alice_123@test-domain.org", True, "Valid with underscore and hyphen"),
    
    # Invalid cases
    ("", False, "Empty email"),
    ("   ", False, "Whitespace only"),
    ("invalid.email", False, "Missing @ symbol"),
    ("user@", False, "Missing domain"),
    ("@example.com", False, "Missing username"),
    ("user..name@example.com", False, "Consecutive dots"),
    (".user@example.com", False, "Starts with dot"),
    ("user.@example.com", False, "Ends with dot"),
    ("user@.example.com", False, "Domain starts with dot"),
    ("user@example.com.", False, "Domain ends with dot"),
    ("user name@example.com", False, "Space in email"),
    ("user@exam ple.com", False, "Space in domain"),
    ("a" * 65 + "@example.com", False, "Local part too long"),
    ("user@" + "a" * 250 + ".com", False, "Email too long"),
]

print("=" * 70)
print("Email Validation Tests")
print("=" * 70)

passed = 0
failed = 0

for email, expected_valid, description in test_cases:
    is_valid, msg = validate_email(email)
    status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"
    
    if is_valid == expected_valid:
        passed += 1
    else:
        failed += 1
    
    print(f"{status} | {description}")
    print(f"       Email: '{email}'")
    print(f"       Expected: {expected_valid}, Got: {is_valid} ({msg})")
    print()

print("=" * 70)
print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 70)
