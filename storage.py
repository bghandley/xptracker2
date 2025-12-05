import json
import os
import copy
import re
import streamlit as st
import datetime
import hashlib
import secrets
import binascii
from typing import Dict, Any, Optional

# Constants
DATA_FILE = "xp_data.json"
DEFAULT_DATA = {
    "goals": ["General"],
    "habits": {},
    "tasks": [],
    "completions": {},
    "journal_sections": [],
    "journal_entries": {},
    "badges": [],  # New
    "auth": {},
    "email": None,
}

class StorageProvider:
    """Abstract base class for data storage."""

    def load_data(self, user_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def save_data(self, user_id: str, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    # Optional auth helpers (implemented by providers)
    def user_exists(self, user_id: str) -> bool:
        raise NotImplementedError

    def set_user_password(self, user_id: str, password: str) -> None:
        raise NotImplementedError

    def verify_user_password(self, user_id: str, password: str) -> bool:
        raise NotImplementedError

def sanitize_user_id(user_id: str) -> str:
    """Sanitize user_id to prevent path traversal or invalid keys."""
    if not user_id:
        return "default"
    # Allow alphanumeric, underscore, hyphen
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', user_id)
    return sanitized if sanitized else "default"

class LocalStorage(StorageProvider):
    """Stores data in local JSON files."""

    def _get_filename(self, user_id: str) -> str:
        safe_id = sanitize_user_id(user_id)
        if safe_id == "default":
            return DATA_FILE
        return f"xp_data_{safe_id}.json"

    def load_data(self, user_id: str = "default") -> Dict[str, Any]:
        filename = self._get_filename(user_id)

        if not os.path.exists(filename):
            # Use deepcopy to ensure fresh default data
            new_data = copy.deepcopy(DEFAULT_DATA)
            self.save_data(user_id, new_data)
            return new_data

        try:
            with open(filename, "r") as f:
                data = json.load(f)
                return self._ensure_schema(data)
        except (json.JSONDecodeError, IOError):
            st.error(f"Error reading data file {filename}. Using default.")
            return copy.deepcopy(DEFAULT_DATA)

    def save_data(self, user_id: str, data: Dict[str, Any]) -> None:
        filename = self._get_filename(user_id)
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            st.error(f"Failed to save data: {e}")

    def _ensure_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return ensure_data_schema(data)

    # Auth helpers
    def user_exists(self, user_id: str) -> bool:
        filename = self._get_filename(user_id)
        return os.path.exists(filename)

    def set_user_password(self, user_id: str, password: str) -> None:
        # Load or create data, then set salted pbkdf2 hash
        data = self.load_data(user_id)
        if not password:
            # Clear auth if empty password
            data['auth'] = {}
            self.save_data(user_id, data)
            return

        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000)
        data['auth'] = {
            'salt': binascii.hexlify(salt).decode('ascii'),
            'pw_hash': binascii.hexlify(dk).decode('ascii'),
        }
        self.save_data(user_id, data)

    def verify_user_password(self, user_id: str, password: str) -> bool:
        # If user doesn't exist, return False
        if not self.user_exists(user_id):
            return False
        data = self.load_data(user_id)
        auth = data.get('auth', {}) or {}
        pw_hash = auth.get('pw_hash')
        salt_hex = auth.get('salt')
        # If no password set, allow login
        if not pw_hash or not salt_hex:
            return True

        try:
            salt = binascii.unhexlify(salt_hex.encode('ascii'))
            expected = binascii.unhexlify(pw_hash.encode('ascii'))
            dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000)
            return secrets.compare_digest(dk, expected)
        except Exception:
            return False

    # Email helpers
    def set_user_email(self, user_id: str, email: Optional[str]) -> None:
        data = self.load_data(user_id)
        data['email'] = email
        self.save_data(user_id, data)

    def get_user_email(self, user_id: str) -> Optional[str]:
        if not self.user_exists(user_id):
            return None
        data = self.load_data(user_id)
        return data.get('email')

    # Password reset token helpers
    def create_password_reset_token(self, user_id: str, expires_in: int = 3600) -> Optional[str]:
        """Create a one-time token, store its hash and expiry, and return the token (plaintext) to be emailed.
        Returns None if user does not exist.
        """
        if not self.user_exists(user_id):
            return None
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        expiry = (datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)).isoformat() + 'Z'

        data = self.load_data(user_id)
        auth = data.get('auth', {})
        auth['reset_hash'] = token_hash
        auth['reset_expiry'] = expiry
        data['auth'] = auth
        self.save_data(user_id, data)
        return token

    def verify_and_consume_reset_token(self, user_id: str, token: str) -> bool:
        """Verify the provided token for user_id; if valid, consume it (delete) and return True.
        Otherwise return False.
        """
        if not self.user_exists(user_id):
            return False
        data = self.load_data(user_id)
        auth = data.get('auth', {}) or {}
        reset_hash = auth.get('reset_hash')
        reset_expiry = auth.get('reset_expiry')
        if not reset_hash or not reset_expiry:
            return False

        try:
            expiry_dt = datetime.datetime.fromisoformat(reset_expiry.rstrip('Z'))
        except Exception:
            return False

        if datetime.datetime.utcnow() > expiry_dt:
            return False

        compare_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        if not secrets.compare_digest(compare_hash, reset_hash):
            return False

        # Consume token
        auth.pop('reset_hash', None)
        auth.pop('reset_expiry', None)
        data['auth'] = auth
        self.save_data(user_id, data)
        return True

class FirebaseStorage(StorageProvider):
    """Stores data in Firebase Firestore."""

    def __init__(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            # Check if already initialized
            if not firebase_admin._apps:
                # 1. Try Streamlit Secrets (Best for Cloud)
                if hasattr(st, "secrets") and "firebase" in st.secrets:
                    # Convert AttrDict to standard dict
                    cred_dict = dict(st.secrets["firebase"])
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)

                # 2. Try File Path (Env Var or Default)
                else:
                    cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase_credentials.json")
                    if os.path.exists(cred_path):
                        cred = credentials.Certificate(cred_path)
                        firebase_admin.initialize_app(cred)
                    else:
                        st.warning("Firebase credentials not found. Set 'firebase' in st.secrets or provide 'firebase_credentials.json'.")
                        self.db = None
                        return

            self.db = firestore.client()
        except ImportError:
            st.error("firebase-admin package not installed.")
        except Exception as e:
            st.error(f"Failed to initialize Firebase: {e}")
            self.db = None

    def load_data(self, user_id: str) -> Dict[str, Any]:
        if not self.db:
            return copy.deepcopy(DEFAULT_DATA)

        safe_id = sanitize_user_id(user_id)
        doc_ref = self.db.collection("users").document(safe_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            return self._ensure_schema(data)
        else:
            # Create new user doc
            new_data = copy.deepcopy(DEFAULT_DATA)
            self.save_data(safe_id, new_data)
            return new_data

    def save_data(self, user_id: str, data: Dict[str, Any]) -> None:
        if not self.db:
            return

        safe_id = sanitize_user_id(user_id)
        doc_ref = self.db.collection("users").document(safe_id)
        doc_ref.set(data)

    def _ensure_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return ensure_data_schema(data)

def ensure_data_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures all necessary keys exist in the loaded data."""
    # Core keys
    for key, default_val in DEFAULT_DATA.items():
        if key not in data:
            data[key] = copy.deepcopy(default_val)

    # Habit structure updates
    if "habits" in data:
        for habit in data["habits"]:
            habit_data = data["habits"][habit]
            if "active" not in habit_data:
                habit_data["active"] = True
            if "goal" not in habit_data:
                habit_data["goal"] = "General"
            # New fields for leveling
            if "level" not in habit_data:
                habit_data["level"] = 1
            if "total_completions" not in habit_data:
                habit_data["total_completions"] = 0

    # Ensure email exists at top level
    if "email" not in data:
        data["email"] = None

    # Ensure auth dict exists and reset fields
    if "auth" not in data or data.get("auth") is None:
        data["auth"] = {}
    auth = data["auth"]
    if "pw_hash" not in auth:
        # leave empty if not set
        pass
    # reset token fields may or may not be present; fine if absent

    return data

def get_storage() -> StorageProvider:
    """Factory to get the configured storage provider."""
    # Check for Firebase config or flag
    use_firebase = os.getenv("USE_FIREBASE", "false").lower() == "true"
    if use_firebase:
        return FirebaseStorage()
    else:
        return LocalStorage()
