"""
models/user.py
--------------
Helper functions and the flask-login User class for the 'users' collection.

MongoDB does NOT enforce a schema, so we define what a user document looks
like here as a plain Python dict template — this is our "schema by convention".
"""

from datetime import datetime, timezone
from bson import ObjectId
from flask_login import UserMixin


# ---------------------------------------------------------------------------
# The User class
# ---------------------------------------------------------------------------
# Flask-Login requires a User class with these four properties:
#   is_authenticated, is_active, is_anonymous, get_id()
# We get them for free by inheriting from UserMixin.
# ---------------------------------------------------------------------------

class User(UserMixin):
    """Wraps a MongoDB user document so flask-login can work with it."""

    def __init__(self, user_doc):
        """
        user_doc: the raw dict returned by MongoDB (has _id, username, etc.)
        """
        self.id = str(user_doc["_id"])        # flask-login needs a string id
        self.username = user_doc["username"]
        self.email = user_doc["email"]
        self.password_hash = user_doc["password_hash"]

    def get_id(self):
        """Return the string id (flask-login calls this internally)."""
        return self.id


# ---------------------------------------------------------------------------
# Helper functions for the users collection
# ---------------------------------------------------------------------------

def create_user(db, username, email, password_hash):
    """
    Insert a new user document into the 'users' collection.
    Returns the inserted document's id as a string.
    """
    user_doc = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "created_at": datetime.now(timezone.utc),
    }
    result = db.users.insert_one(user_doc)
    return str(result.inserted_id)


def find_user_by_email(db, email):
    """Return the raw user document for a given email, or None."""
    return db.users.find_one({"email": email})


def find_user_by_username(db, username):
    """Return the raw user document for a given username, or None."""
    return db.users.find_one({"username": username})


def ensure_indexes(db):
    """
    Create unique indexes on email and username so the database itself
    enforces uniqueness even if our Python code forgets to check.
    Call this once at startup.
    """
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)
