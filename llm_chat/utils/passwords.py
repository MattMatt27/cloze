"""Shared password complexity policy.

Single source of truth so the rules can't drift between the admin and
provider credential flows.
"""

PASSWORD_MIN_LENGTH = 12


def validate_password(password):
    """Return an error message if the password is too weak, or None if it's
    acceptable. Policy: at least 12 characters, with uppercase, lowercase,
    and a digit."""
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return f'Password must be at least {PASSWORD_MIN_LENGTH} characters'
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_upper and has_lower and has_digit):
        return 'Password must contain uppercase, lowercase, and a number'
    return None
