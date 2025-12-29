from test_leaderboard import test_leaderboard_local_files

try:
    test_leaderboard_local_files()
    print("TEST PASSED")
except AssertionError as e:
    print("TEST FAILED:", e)
except Exception as ex:
    print("ERROR RUNNING TEST:", ex)
