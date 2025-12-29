from tracker import get_leaderboard_stats

if __name__ == "__main__":
    lb = get_leaderboard_stats("all_time")
    print("Leaderboard:", lb)
