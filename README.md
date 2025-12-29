# XP Tracker (Streamlit)

XP Tracker is a Streamlit-based habit + mission tracker with gamification (XP, levels, streaks), multi-user auth, optional email notifications, optional AI coaching (Gemini), and a public leaderboard.

## Quick Start (Local)

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Copy example secrets and edit as needed (never commit your real secrets)
copy .streamlit\\secrets.toml.example .streamlit\\secrets.toml

streamlit run tracker.py
```

## Configuration

- Secrets live in `.streamlit/secrets.toml` (git-ignored by default).
- Example template: `.streamlit/secrets.toml.example`.

Common settings:

```toml
admin_passphrase = "<choose-a-strong-passphrase>"

[app]
url = "http://localhost:8501"

gemini_api_key = "<your-gemini-api-key>" # optional

[smtp] # optional (for email notifications)
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "<app-password>"
from = "your-email@gmail.com"
```

## Data Storage

- Default: local JSON files created at runtime (git-ignored): `xp_data.json`, `xp_data_<username>.json`, `notifications_history.json`.
- Optional: Firebase/Firestore storage (see `docs/SETUP_STREAMLIT_FIREBASE.md`).

## Docs

- Start here: `docs/DOCUMENTATION_INDEX.md`
- User guide: `docs/HOWTO_USE.md`
- Deployment: `docs/SETUP_STREAMLIT_FIREBASE.md`
- Gemini setup: `docs/GEMINI_SETUP.md`

## Repo Layout

- App: `tracker.py`
- Storage: `storage.py`
- Email: `email_utils.py`, `notifications.py`, `scheduler_service.py`
- AI coaching: `coaching_emails.py`, `ai_chat.py`, `coaching_engine.py`

## Sharing / Security Checklist

- Do not commit `.streamlit/secrets.toml` (already ignored); use Streamlit Cloud secrets UI for production.
- Do not commit runtime data files (`xp_data*.json`, `notifications_history.json`) (ignored in `.gitignore`).
- If you previously committed secrets, rotate them and consider rewriting git history (e.g. `git filter-repo`).

