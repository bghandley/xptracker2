import json
import os
import copy
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

class LocalStorage(StorageProvider):
    """Stores data in local JSON files."""

    def _get_filename(self, user_id: str) -> str:
        if user_id == "default":
            return DATA_FILE
        return f"xp_data_{user_id}.json"

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
        """Ensures all necessary keys exist in the loaded data."""
        dirty = False

        # Core keys
        for key, default_val in DEFAULT_DATA.items():
            if key not in data:
                data[key] = copy.deepcopy(default_val)
                dirty = True

        # Habit structure updates
        if "habits" in data:
            for habit in data["habits"]:
                habit_data = data["habits"][habit]
                if "active" not in habit_data:
                    habit_data["active"] = True
                    dirty = True
                if "goal" not in habit_data:
                    habit_data["goal"] = "General"
                    dirty = True
                # New fields for leveling
                if "level" not in habit_data:
                    habit_data["level"] = 1
                    dirty = True
                if "total_completions" not in habit_data:
                    habit_data["total_completions"] = 0
                    dirty = True

        return data

class FirebaseStorage(StorageProvider):
    """Stores data in Firebase Firestore."""

    def __init__(self):
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            # Check if already initialized
            if not firebase_admin._apps:
                # Try to find credentials
                cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase_credentials.json")
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                else:
                    # Fallback for when no creds are present (won't work but prevents import crash)
                    # Use a dummy app or raise warning
                    st.warning("Firebase credentials not found at 'firebase_credentials.json'.")
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

        doc_ref = self.db.collection("users").document(user_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            return self._ensure_schema(data)
        else:
            # Create new user doc
            new_data = copy.deepcopy(DEFAULT_DATA)
            self.save_data(user_id, new_data)
            return new_data

    def save_data(self, user_id: str, data: Dict[str, Any]) -> None:
        if not self.db:
            return

        doc_ref = self.db.collection("users").document(user_id)
        doc_ref.set(data)

    def _ensure_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Same schema validation as LocalStorage
        # In a real app, this logic might be shared in a utility or base class
        # copying from LocalStorage for now

        for key, default_val in DEFAULT_DATA.items():
            if key not in data:
                data[key] = copy.deepcopy(default_val)

        if "habits" in data:
            for habit in data["habits"]:
                habit_data = data["habits"][habit]
                if "active" not in habit_data:
                    habit_data["active"] = True
                if "goal" not in habit_data:
                    habit_data["goal"] = "General"
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
