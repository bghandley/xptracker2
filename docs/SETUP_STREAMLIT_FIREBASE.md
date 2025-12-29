# 🚀 XP Tracker - Streamlit Cloud + Firebase Setup Guide

This guide covers deploying XP Tracker on **Streamlit Cloud** with optional **Firebase** for remote storage and authentication.

---

## 📋 Quick Summary

- **Frontend**: Streamlit Cloud (free tier available)
- **Storage**: Firebase Firestore (optional; can also use JSON files on Streamlit Cloud)
- **Email**: SMTP via Gmail, SendGrid, or your provider
- **Auth**: Google Gemini AI (optional, for coaching)
- **Admin Access**: Password-protected via environment variable


---

## 🔧 Prerequisites

You'll need:
1. GitHub account (to host code)
2. Streamlit Cloud account (streamlit.io)
3. Gmail/SendGrid account (for SMTP email)
4. OpenAI account (optional, for AI coaching)
5. Firebase account (optional, for remote storage)

---

## 📝 Step 1: Prepare Your Repository

### 1.1 Create a GitHub Repository

```bash
# Clone/push your repo to GitHub
git init
git remote add origin https://github.com/YOUR_USERNAME/xptracker.git
git add .
git commit -m "Initial XP Tracker commit"
git push -u origin main
```

### 1.2 Create `requirements.txt`

Ensure you have a `requirements.txt` in the repo root:

```
streamlit>=1.28.0
pandas>=1.5.0
plotly>=5.0.0
google-generativeai>=0.3.0  # For AI coaching
firebase-admin>=6.0.0  # Optional, for Firebase
google-cloud-firestore>=2.11.0  # Optional
```

### 1.3 Add `.streamlit/config.toml` (Optional)

Create `.streamlit/config.toml` for local development config:

```toml
[theme]
primaryColor = "#FF6B35"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true

[logger]
level = "info"
```

---

## 🌐 Step 2: Deploy to Streamlit Cloud

### 2.1 Sign Up for Streamlit Cloud

1. Go to **https://streamlit.io/cloud**
2. Click **"Sign up"** and log in with your GitHub account
3. Authorize Streamlit to access your GitHub repos

### 2.2 Deploy Your App

1. Click **"New app"**
2. Select your repository and branch (`main`)
3. Set **Main file path** to `tracker.py`
4. Click **"Deploy"**

Your app will be live at: `https://[your-username]-xptracker.streamlit.app`

### 2.3 Add Secrets (Environment Variables)

In Streamlit Cloud dashboard:

1. Click your app → **Settings** (⚙️)
2. Go to **Secrets**
3. Add the following secrets (JSON format):

```toml
# Admin passphrase (required)
admin_passphrase = "your_super_secure_passphrase_here"

# SMTP settings (required for email notifications)
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "your-app-specific-password"  # NOT your Gmail password; use App Password
from = "your-email@gmail.com"

# App URL (required for password reset links)
[app]
url = "https://your-username-xptracker.streamlit.app"

# Google Gemini API Key (optional, for AI coaching)
gemini_api_key = "AIza..."

# Firebase config (optional, for remote storage)
[firebase]
project_id = "your-firebase-project"
private_key_id = "..."
private_key = "<from your service account json (keep the \\n escapes)>"
client_email = "firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

---

## 📧 Step 3: Set Up SMTP Email

### Option A: Gmail (Recommended)

1. Enable 2-Factor Authentication on your Google account
2. Go to **https://myaccount.google.com/apppasswords**
3. Generate an **App Password** for "Mail"
4. Copy the 16-character password
5. Add to Streamlit Secrets:

```toml
[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "xxxx xxxx xxxx xxxx"  # 16-character app password (without spaces when pasting)
from = "your-email@gmail.com"
```

### Option B: SendGrid

1. Sign up at **https://sendgrid.com**
2. Get your API key
3. Add to Streamlit Secrets:

```toml
[smtp]
host = "smtp.sendgrid.net"
port = 587
user = "apikey"
password = "SG.your-sendgrid-api-key"
from = "noreply@your-domain.com"
```

### Test SMTP Connection

In Streamlit Cloud, admins can test in the **⚙️ Admin** panel. Manually send a test notification to verify email works.

---

## 🔥 Step 4 (Optional): Set Up Firebase

### 4.1 Create a Firebase Project

1. Go to **https://console.firebase.google.com**
2. Click **"Create a project"**
3. Enable **Firestore Database** (select "Start in production mode")
4. Download the service account key:
   - Project Settings → Service Accounts → Generate new private key

### 4.2 Add to Streamlit Secrets

Copy the entire JSON key and add to `secrets.toml`:

```toml
[firebase]
project_id = "your-project-id"
private_key_id = "..."
# ... (paste entire JSON key)
```

### 4.3 Update `storage.py` to Use Firebase

In `storage.py`, the `get_storage()` function checks for `STORAGE_TYPE` env var:

```python
storage_type = os.environ.get("STORAGE_TYPE", "local")
if storage_type == "firebase":
    return FirebaseStorage()
else:
    return LocalStorage()
```

Add to Streamlit Secrets:

```toml
storage_type = "firebase"
```

---

## 🔑 Step 5: Configure Admin Access

### 5.1 Set Admin Passphrase

In Streamlit Cloud Secrets, add:

```toml
admin_passphrase = "pick_a_very_secure_passphrase_here"
```

### 5.2 Access Admin Panel

1. Log in as any user
2. Go to **⚙️ Admin** tab
3. Enter the passphrase
4. Unlock admin panel

---

## 🤖 Step 6 (Optional): Enable Google Gemini AI Coaching

### 6.1 Get a Google Gemini API Key

1. Go to **https://makersuite.google.com/app/apikey**
2. Click **"Create API Key"**
3. Copy your API key (starts with `AIza...`)

### 6.2 Add to Streamlit Secrets

```toml
gemini_api_key = "AIza..."
```

**Cost**: Google Gemini is **free** for now (during preview phase). No credit card required!

### 6.3 Verify Connection

In **⚙️ Admin** panel (when admin accesses), it will auto-detect if Gemini is available. If not, the system falls back to template-based coaching (still good!).


---

## 📊 Step 7: Data Storage Notes

### LocalStorage (Default)

- Data stored in JSON files on Streamlit Cloud filesystem
- **Pro**: Zero setup, works out of the box
- **Con**: Data lost if Streamlit Cloud resets (rare but possible); not shared across instances
- **Files** (generated at runtime; git-ignored): `xp_data.json` (default user), `xp_data_<username>.json` per user

### FirebaseStorage (Remote)

- Data stored in Firebase Firestore (remote cloud database)
- **Pro**: Data persists forever; accessible from any instance
- **Con**: Requires Firebase setup; small cost ($0.06 per 100k reads)
- **Schema**: Collection `users` → document `[username]` → field `data` (JSON)

**Recommendation**: Use LocalStorage for testing; upgrade to Firebase if you want data persistence across app restarts.

---

## 🔔 Step 8: Scheduled Notifications

### Problem

Streamlit Cloud doesn't support background jobs. Notifications only trigger when a user logs in.

### Solution A: External Scheduler (GitHub Actions)

Use GitHub Actions to trigger a scheduled job that sends notifications:

Create `.github/workflows/daily-notifications.yml`:

```yaml
name: Daily Notifications

on:
  schedule:
    - cron: '0 7 * * *'  # 7 AM UTC daily

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run notification scheduler
        env:
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          SMTP_FROM: ${{ secrets.SMTP_FROM }}
          # AI coaching uses Gemini; configure `gemini_api_key` in Streamlit Secrets.
        run: python scheduler.py
```

Create `scheduler.py`:

```python
import json
import os
from notifications import (
    notify_missed_day,
    notify_weekly_summary,
    get_user_notification_history
)
from storage import get_storage

# This runs daily and checks all users for notifications to send
storage = get_storage()
all_users = []  # Scan for users

for user_id in all_users:
    user_data = storage.load_data(user_id)
    
    # Check for missed habits
    for habit, details in user_data.get("habits", {}).items():
        if details.get("active", True):
            # Check if habit was missed today
            # TODO: implement miss detection logic
            pass
    
    # Send weekly summary on Sunday
    from datetime import datetime
    if datetime.now().weekday() == 6:  # Sunday
        notify_weekly_summary(user_id, 5, 7, 350)
```

### Solution B: Manual Testing

Admins can manually send notifications via **⚙️ Admin** → **📣 Notification Triggers** for testing.

---

## 🧪 Testing Locally

### 1. Set Up Local Environment

```bash
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Create `.streamlit/secrets.toml` Locally

Create `.streamlit/secrets.toml` in your repo (git-ignored):

```toml
admin_passphrase = "test_passphrase"
storage_type = "local"

[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "your-app-password"
from = "your-email@gmail.com"

[app]
url = "http://localhost:8501"

# AI coaching uses Gemini; set `gemini_api_key` instead.
```

### 3. Run Locally

```bash
streamlit run tracker.py
```

Visit **http://localhost:8501** in your browser.

### 4. Test Features

- Create an account
- Add habits and tasks
- Test email notifications (set your own email)
- Test admin panel

---

## 🐛 Troubleshooting

### App won't load

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Fix**: Check `requirements.txt` is up-to-date and Streamlit Cloud redeployed. Go to **⋯** → **Reboot app**.

### Notifications not sending

**Error**: `Failed to send email`

**Debug**:
1. Check SMTP credentials in Secrets are correct
2. Verify Gmail app password (not regular password)
3. Check firewall isn't blocking SMTP port 587
4. In Admin panel, manually trigger a test notification to see error details

### Data lost after Streamlit Cloud restart

**Fix**: Migrate to Firebase (see Step 4). Add `storage_type = "firebase"` to Secrets.

### Gemini API errors

**Error**: `Invalid API key` or `Permission denied`

**Fix**: 
1. Check API key in Secrets is correct (starts with `AIza`)
2. Verify key is enabled at https://makersuite.google.com/app/apikey
3. Note: Gemini is in preview; availability may be limited by region


---

## 📈 Next Steps

- **Monitor**: Check Streamlit Cloud logs if issues occur
- **Backup**: Periodically export user data (via **📊 Reports** → Download JSON)
- **Upgrade**: If usage grows, consider:
  - Firebase for data persistence
  - SendGrid for higher email limits
  - Dedicated server (not Streamlit Cloud)

---

## 🆘 Support

- **Streamlit Docs**: https://docs.streamlit.io
- **Firebase Docs**: https://firebase.google.com/docs
- **Gmail App Passwords**: https://support.google.com/accounts/answer/185833
- **OpenAI Docs**: https://platform.openai.com/docs

---

**Last Updated**: December 5, 2025  
**Version**: 1.0
