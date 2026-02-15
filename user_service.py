"""
User-related functionality.

This module handles:
- password validation
- authentication
- user creation
- preference reading
"""

from werkzeug.security import generate_password_hash, check_password_hash

# ================= PASSWORD =================

def validate_password(password):
    # Validate password strength rules

    if len(password) < 6 or len(password) > 12:
        return "Password must be between 6 and 12 characters."
    if not any(c.isupper() for c in password):
        return "Password must include at least one uppercase letter."
    if not any(c.islower() for c in password):
        return "Password must include at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return "Password must include at least one number."
    if not any(not c.isalnum() for c in password):
        return "Password must include at least one special character."
    return None

# ================= AUTH =================

def authenticate_user(User, username, password):
    # Return user if credentials are valid

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return None
    return user

def create_user(db, User, Preference, username, password, api_options):
    # Create a new user with default enabled preferences

    secure_hash = generate_password_hash(password)

    new_user = User(username=username, password_hash=secure_hash)
    db.session.add(new_user)
    db.session.flush()  # get user.id before commit

    # Create default preferences
    for api_code, _ in api_options:
        pref = Preference(user_id=new_user.id, api_code=api_code, enabled=True)
        db.session.add(pref)

    db.session.commit()
    return new_user

# ================= PREFERENCES =================

def get_enabled_api_codes(Preference, user_id):
    # Return set of enabled API codes for user

    rows = Preference.query.filter_by(user_id=user_id, enabled=True).all()
    return {row.api_code for row in rows}
