import os
import json
from tracker import get_leaderboard_stats


def test_leaderboard_local_files():
    """Ensure leaderboard picks up local xp_data_<user>.json files and orders by XP."""
    alice = {
        "habits": {},
        "completions": {},
        "tasks": [{"title": "task1", "status": "Done", "completed_at": "2025-12-01T00:00:00", "xp": 50}]
    }
    bob = {
        "habits": {},
        "completions": {},
        "tasks": [{"title": "task1", "status": "Done", "completed_at": "2025-12-01T00:00:00", "xp": 10}]
    }

    alice_file = "xp_data_alice.json"
    bob_file = "xp_data_bob.json"
    backup_default = None
    if os.path.exists("xp_data.json"):
        backup_default = "xp_data_backup.json"
        os.rename("xp_data.json", backup_default)
    with open(alice_file, "w") as f:
        json.dump(alice, f)
    with open(bob_file, "w") as f:
        json.dump(bob, f)

    try:
        leaderboard = get_leaderboard_stats("all_time")
        # Find alice and bob entries regardless of position
        d = {u: xp for u, xp in leaderboard}
        assert d.get("alice") == 50, f"Alice XP mismatch: {d.get('alice')}"
        assert d.get("bob") == 10, f"Bob XP mismatch: {d.get('bob')}"
    finally:
        os.remove(alice_file)
        os.remove(bob_file)
        if backup_default:
            os.rename(backup_default, "xp_data.json")


def test_leaderboard_with_storage_list_users():
    """Ensure leaderboard respects a storage provider that lists users (Firebase-style)."""
    # Create fake storage that behaves like FirebaseStorage
    class FakeStorage:
        def __init__(self):
            self._data = {
                "alice": {"habits": {}, "completions": {}, "tasks": [{"title": "t", "status": "Done", "completed_at": "2025-12-01T00:00:00", "xp": 70}]},
                "bob": {"habits": {}, "completions": {}, "tasks": [{"title": "t", "status": "Done", "completed_at": "2025-12-01T00:00:00", "xp": 20}]}
            }
        def list_users(self):
            return ["alice", "bob"]
        def load_data(self, user_id):
            return self._data.get(user_id, {})

    import tracker
    orig_get_storage = tracker.get_storage
    try:
        tracker.get_storage = lambda: FakeStorage()
        leaderboard = get_leaderboard_stats("all_time")
        # Should find alice (70) then bob (20)
        assert leaderboard[0][0] == "alice" and leaderboard[0][1] == 70
        assert leaderboard[1][0] == "bob" and leaderboard[1][1] == 20
    finally:
        tracker.get_storage = orig_get_storage

