# 🚀 XP Tracker - Google Gemini AI Setup

This guide explains how to set up **Google Gemini AI** for personalized coaching emails in XP Tracker.

---

## Why Gemini?

✅ **Free** (during preview phase - no credit card needed)  
✅ **Powerful** (same quality coaching as paid alternatives)  
✅ **Simple** (easy API integration)  
✅ **Fast** (real-time responses)  

---

## 🔑 Step 1: Get Your Gemini API Key

1. Go to **https://makersuite.google.com/app/apikey**
2. Click **"Create API Key"** (Google will auto-create a project)
3. Copy your API key (looks like `AIzaSy...`)

**Note**: You need a Google account. Make sure you're in a region where Gemini is available.

---

## 🔧 Step 2: Add to Streamlit Cloud Secrets

In Streamlit Cloud:

1. Go to **Your App** → **Settings** (⚙️)
2. Click **Secrets**
3. Add this line:

```toml
gemini_api_key = "AIzaSy..."
```

4. Click **Save**
5. Your app will auto-reload

---

## 🧪 Step 3: Verify It Works

### Local Testing

```bash
# In your project directory
python -c "
import google.generativeai as genai
genai.configure(api_key='YOUR_API_KEY')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Say hello')
print(response.text)
"
```

### Streamlit Cloud Testing

1. Log into your app as admin
2. Go to **⚙️ Admin** tab
3. Enter admin passphrase
4. Check the notification panel — it will show:
   - ✅ **Gemini API Connected** (if working)
   - ❌ **Gemini API Not Available** (if not configured)

---

## 📧 Coaching Email Examples

Here's what users will receive with Gemini coaching enabled:

### Example 1: Streak Celebration

**Trigger**: User hits a 7-day streak

**Gemini Response**:
> "7 days on 'Morning Meditation'? That's not routine—that's the thinking that changes the game. Most people quit at day 3. You're already ahead."

**Fallback** (if Gemini fails):
> "7-day streak on 'Morning Meditation' — that's the thinking that changes the game. Most people don't. You are."

---

### Example 2: Missed Day Encouragement

**Trigger**: User breaks their streak

**Gemini Response**:
> "You missed one. That's data, not defeat. Your 12-day streak proves you can do this. Here's the move: one small win today. Rebuild from there."

**Fallback** (if Gemini fails):
> "Missed a day? That's data, not a defeat. You had a 12-day streak — that's real. Now: what's the game to get it back?"

---

### Example 3: Weekly Summary

**Trigger**: End of week (Sunday)

**Gemini Response**:
> "You hit 6/7 habits this week (86%). That's a pattern emerging. The real question: is this the pattern you WANT? Your 'Meditation' streak is gold. So: what shifts next week?"

**Fallback** (if Gemini fails):
> "You hit 86% this week. That's a pattern emerging. The question: is this the pattern you want? If not, what shifts this coming week?"

---

### Example 4: Personalized Coaching

**Trigger**: Manual admin trigger or scheduled check

**Gemini Response**:
> "You're Level 7 with a solid meditation habit (21 days). But I notice 'Exercise' is stuck at 2 days. Here's the edge: stack exercise right after meditation. One week. Report back."

**Fallback** (if Gemini fails):
> "You're at a pivot point. The habits you've built are proof. Now: which one friction do you remove this week? Pick one. Remove it."

---

## 🎯 Coaching Style

Gemini is configured for **Price Pritchett quantum coaching**:

- **Data-driven**: References actual metrics (streaks, levels, percentages)
- **Challenging but warm**: Slightly provocative edge, never shame-based
- **Action-oriented**: Specific micro-actions, not philosophy
- **Quantum thinking**: Breakthroughs over maintenance

---

## ❌ Troubleshooting

### "Gemini API Not Available"

**Check**:
1. Is `gemini_api_key` in your Streamlit Secrets?
2. Is the key valid? (starts with `AIzaSy...`)
3. Is Gemini available in your region? (Try: https://makersuite.google.com)

**Fix**:
- Regenerate your API key at https://makersuite.google.com/app/apikey
- Re-add to Streamlit Secrets
- Restart your app

---

### "Invalid API Key" Error

**Check**:
- Did you copy the full key?
- Did you accidentally add spaces?
- Is the key still enabled at https://makersuite.google.com?

**Fix**:
```
# Try this to test locally:
python -c "
import google.generativeai as genai
genai.configure(api_key='YOUR_KEY_HERE')
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Test')
print('✅ Success!' if response else '❌ Failed')
"
```

---

### Emails still using fallback messages

**This is OK!** It means:
1. Gemini API is not configured (intentional)
2. Gemini API failed temporarily (will retry next time)
3. Network issue (check Streamlit Cloud logs)

Fallback messages are high-quality Price Pritchett templates, so coaching still works!

**To debug**:
1. Go to **⚙️ Admin** → Notification Triggers
2. Manually send a test notification
3. Check the error message in the modal

---

## 💡 Tips

- **Gemini is free**: No need to worry about costs during setup
- **Fallback messages are good**: If Gemini isn't available, users still get great coaching
- **Customize prompts**: Edit `coaching_emails.py` to adjust coaching style
- **Monitor usage**: Gemini has rate limits (~100 requests/day on free tier)

---

## 📚 References

- **Gemini API Docs**: https://ai.google.dev
- **Streamlit Secrets**: https://docs.streamlit.io/develop/concepts/connections/secrets-management
- **Price Pritchett**: https://www.pricepritchett.com (quantum coaching philosophy)

---

**Last Updated**: December 5, 2025  
**Version**: 1.0
