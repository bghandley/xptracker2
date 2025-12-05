import json
import os
import copy
import re
import streamlit as st
import datetime
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
}

class StorageProvider:
    """Abstract base class for data storage."""

    def load_data(self, user_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def save_data(self, user_id: str, data: Dict[str, Any]) -> None:
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

    return data

def get_storage() -> StorageProvider:
    """Factory to get the configured storage provider."""
    # Check for Firebase config or flag
    use_firebase = os.getenv("USE_FIREBASE", "false").lower() == "true"
    if use_firebase:
        return FirebaseStorage()
    else:
        return LocalStorage()
