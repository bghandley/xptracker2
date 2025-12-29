import sys, types, json, os

# Insert lightweight stubs for missing heavy modules
for name in ('pandas', 'plotly', 'plotly.express'):
    if name not in sys.modules:
        sys.modules[name] = types.ModuleType(name)

# Minimal stub for streamlit if not installed to avoid UI side-effects
try:
    import streamlit as st
except Exception:
    st = types.SimpleNamespace(
        set_page_config=lambda **kwargs: None,
        markdown=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        error=lambda *a, **k: None,
        info=lambda *a, **k: None,
        secrets={},
    )
    sys.modules['streamlit'] = st

# Now import tracker and run the test scenario
from tracker import get_leaderboard_stats

# Ensure there are local xp files for the test
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

with open('xp_data_alice.json', 'w') as f:
    json.dump(alice, f)
with open('xp_data_bob.json', 'w') as f:
    json.dump(bob, f)

try:
    leaderboard = get_leaderboard_stats('all_time')
    print('Leaderboard:', leaderboard)
finally:
    os.remove('xp_data_alice.json')
    os.remove('xp_data_bob.json')
