# 🎯 XP Tracker - Complete Feature Summary

**Status**: ✅ Production Ready  
**Last Updated**: December 5, 2025  
**Cost**: 💰 Free (Gemini + Streamlit Cloud)  

---

## 📋 Overview

XP Tracker is a **Streamlit-based habit tracking app** with:
- 👥 Multi-user authentication (local + password reset)
- 🎮 Gamification (XP, levels, streaks, leaderboard)
- 📝 Rich features (daily quests, tasks, journal, reports)
- 🤖 AI coaching (Google Gemini)
- 📧 Email notifications
- 🔒 Security (PBKDF2 password hashing, admin panel)

---

## 🚀 Quick Start

### 1. Local Setup

```bash
# Clone repo
git clone https://github.com/bghandley/xptracker2.git
cd xptracker2

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .streamlit/secrets.toml (see GEMINI_SETUP.md)
# Run app
streamlit run tracker.py
```

### 2. Get Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIzaSy...`)

### 3. Configure Secrets

Create `.streamlit/secrets.toml`:

```toml
admin_passphrase = "your_secure_password_here"

[smtp]
host = "smtp.gmail.com"
port = 587
user = "your-email@gmail.com"
password = "your-app-specific-password"
from = "your-email@gmail.com"

[app]
url = "http://localhost:8501"

gemini_api_key = "AIzaSy..."
```

### 4. Test

```bash
streamlit run tracker.py
```

Visit http://localhost:8501

---

## 📚 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **DOCUMENTATION_INDEX.md** | Navigation guide for all docs | Everyone |
| **HOWTO_USE.md** | Complete user guide (how to use features) | End Users |
| **SETUP_STREAMLIT_FIREBASE.md** | Deployment to Streamlit Cloud + Firebase | DevOps/Deployment |
| **GEMINI_SETUP.md** | Gemini API setup & examples | Developers/Admins |
| **AUTH_IMPLEMENTATION.md** | Authentication architecture | Developers |
| **EMAIL_VALIDATION.md** | Email system implementation | Developers |
| **AUTOMATION_IMPLEMENTATION_COMPLETE.md** | Notifications & scheduler system | Developers |

---

## 🎮 Core Features

### Daily Habits (Daily Quests)
- Create habits with XP rewards
- Track streaks
- Mark complete/incomplete
- View history

### Tasks (Mission Log)
- Create one-off tasks
- Assign to goals
- Track completion

### Journal
- Create dated entries
- Organize by sections
- Rich text support

### Reports
- Weekly analytics
- Completion rates
- XP earned
- Top habits

### Leaderboard
- All-time rankings
- Weekly rankings
- Monthly rankings
- Yearly rankings

### Profile & Badges
- Career stats
- Level progression
- Badge system
- Email management
- Notification history

### Notifications
- **Streak Milestones** (5, 10, 20+ day streaks)
- **Missed Day** (encouragement when streak breaks)
- **Level Up** (celebration on level progression)
- **Badge Earned** (new badge unlocked)
- **Weekly Summary** (Sunday recap)
- **Personalized Coaching** (custom AI advice)
- **Habit Completion** (instant email on check-off)

### Automation 🤖 (NEW)
- **Auto-Send on Completion** — Email sent instantly when habit marked complete
- **Daily Reminders** (7:00 AM) — Encourage incomplete habits
- **Weekly Summary** (Sunday 9:00 AM) — Recap with coaching tips
- **Streak Milestones** (6:00 AM) — Celebrate major streaks
- **Per-User Opt-In** — Users control notifications in Profile
- **Scheduler Status UI** (Admin panel) — View & manage background jobs

### Admin Panel
- 🔐 Password-protected (ADMIN_PASSPHRASE)
- 👥 User management
- 📣 Manual notification triggers
- 📧 Test email sending

---

## 🔐 Security Features

✅ **Password Hashing**: PBKDF2-HMAC-SHA256 (200k iterations + salt)  
✅ **Session Auth**: Streamlit session state (authenticated_user)  
✅ **Access Control**: Login gates on personal tabs  
✅ **Email Validation**: RFC 5322 compliant  
✅ **Password Reset**: One-time tokens (SHA256 hashed)  
✅ **Admin Auth**: ADMIN_PASSPHRASE environment variable  

---

## 🤖 AI Coaching (Google Gemini)

**Free** AI-generated personalized coaching:

### Examples

**Streak Celebration**:
> "7 days on 'Meditation'? That's not routine—that's the thinking that changes the game. Most people quit at day 3. You're already ahead."

**Missed Day**:
> "You missed one. That's data, not defeat. Your 12-day streak proves you can do this. Here's the move: one small win today. Rebuild from there."

**Weekly Summary**:
> "You hit 6/7 habits this week (86%). That's a pattern emerging. Is this the pattern you WANT? Your 'Meditation' streak is gold. So: what shifts next week?"

**Personalized Coaching**:
> "You're Level 7 with a solid meditation habit (21 days). But 'Exercise' is stuck at 2 days. Here's the edge: stack exercise right after meditation. One week. Report back."

---

## 📊 Architecture

```
tracker.py                 ← Main Streamlit app (1500+ lines)
├── storage.py             ← Data persistence layer
├── email_utils.py         ← SMTP email sending
├── coaching_emails.py     ← Gemini AI integration
├── notifications.py       ← Event-based notifications
├── scheduler_service.py   ← APScheduler background jobs (NEW)
├── reset_user_password.py ← CLI admin tool
└── requirements.txt       ← Dependencies

Data:
├── xp_data.json           ← Default user data
├── xp_data_[user].json    ← Per-user data files
└── notifications_history.json ← Per-user email history
```

---

## 🚀 Deployment

### Streamlit Cloud (Recommended)

1. Push to GitHub
2. Go to https://streamlit.io/cloud
3. Click "New app"
4. Select repo + `tracker.py`
5. Add Secrets (GEMINI_SETUP.md)
6. Done! 🎉

See **SETUP_STREAMLIT_FIREBASE.md** for detailed steps.

### Firebase (Optional)

For remote data persistence:
1. Create Firebase project
2. Download service account key
3. Add to Streamlit Secrets
4. Set `storage_type = "firebase"`

See **SETUP_STREAMLIT_FIREBASE.md** for details.

---

## 🔧 Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `admin_passphrase` | Yes | Admin panel access |
| `gemini_api_key` | No* | AI coaching |
| `SMTP_HOST` | Yes | Email sending |
| `SMTP_PORT` | Yes | Email sending |
| `SMTP_USER` | Yes | Email sending |
| `SMTP_PASSWORD` | Yes | Email sending |
| `SMTP_FROM` | Yes | Email from address |
| `APP_URL` | Yes | Password reset links |

*Gemini optional; system uses fallback templates if missing

---

## 📦 Dependencies

```
streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.0.0
google-generativeai>=0.3.0
apscheduler>=3.10.0
firebase-admin
```

---

## ✅ Testing

### Unit Tests

```bash
# Email validation
python -m pytest test_email_validation.py -v

# Auth flow
python -m pytest test_auth_flow.py -v

# Password reset
python -m pytest test_reset_flow.py -v
```

### Manual Testing

1. Create account → verify email validation
2. Add habit → complete it → verify XP/streak
3. Miss day → verify encouragement email
4. Check leaderboard → verify rankings
5. Admin panel → test manual notification sends

---

## 🐛 Troubleshooting

### App won't start

**Error**: `ModuleNotFoundError`  
**Fix**: `pip install -r requirements.txt`

### Gemini API errors

**Error**: `Invalid API key`  
**Fix**: See **GEMINI_SETUP.md** troubleshooting

### Email not sending

**Error**: `Failed to send email`  
**Fix**: Check SMTP config in Secrets

### Data lost on Streamlit restart

**Fix**: Use Firebase (SETUP_STREAMLIT_FIREBASE.md)

---

## 📈 Roadmap

**Completed** ✅
- Multi-user auth
- Email notifications
- AI coaching (Gemini)
- Leaderboard
- Admin panel
- Auto-send on habit completion
- APScheduler background automation
- Per-user notification opt-in

**Planned** 📋
- Email retry logic
- Mobile app
- Custom notification schedules
- API for third-party integrations
- Phase 1: Email-first interactive coaching (design ready)
- Phase 2: Chat widget (design ready)
- Phase 3: Full coaching dashboard (design ready)

---

## 💡 Philosophy

**XP Tracker** is built on **Price Pritchett quantum coaching**:
- 📊 Data-driven (specific metrics, not fluff)
- 🚀 Quantum thinking (breakthroughs, not maintenance)
- ⚡ Action-oriented (specific micro-actions)
- ❤️ Never shame-based (normalize failures)
- 🔥 Challenging but warm (supportive edge)

---

## 📞 Support

**Issue**: Feature request  
**Contact**: Open a GitHub issue

**Issue**: Bug report  
**Contact**: Open a GitHub issue with error logs

**Issue**: Deployment help  
**Docs**: See SETUP_STREAMLIT_FIREBASE.md

---

## 📄 License

(Add your license here)

---

## 🙏 Credits

- **Streamlit** (web framework)
- **Google Gemini** (AI coaching)
- **Firebase** (optional storage)
- **Price Pritchett** (quantum coaching philosophy)

---

## 🎯 Next Steps

1. **Clone the repo**: `git clone ...`
2. **Set up locally**: Follow "Quick Start" above
3. **Get Gemini key**: https://makersuite.google.com/app/apikey
4. **Deploy to Streamlit**: SETUP_STREAMLIT_FIREBASE.md
5. **Invite users**: Share the app URL

---

**Built with ❤️ for habit tracking & personal growth**

Last Updated: December 5, 2025
