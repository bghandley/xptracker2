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
    with open(alice_file, "w") as f:
        json.dump(alice, f)
    with open(bob_file, "w") as f:
        json.dump(bob, f)

    try:
        leaderboard = get_leaderboard_stats("all_time")
        # Should find alice (50) then bob (10)
        assert leaderboard[0][0] == "alice" and leaderboard[0][1] == 50
        assert leaderboard[1][0] == "bob" and leaderboard[1][1] == 10
    finally:
        os.remove(alice_file)
        os.remove(bob_file)
