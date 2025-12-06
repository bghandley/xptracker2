"""
Daily Digest System
Sends a single personalized daily email summarizing:
- Today's habit completions
- Current streaks
- One reflection prompt
- Adaptive coaching based on performance

This replaces per-completion notifications for a cleaner experience.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from storage import get_storage
from email_utils import send_email
from onboarding import get_coaching_profile, calculate_days_since_signup
from coaching_engine import get_coaching_email_for_user


DIGEST_HISTORY_FILE = "daily_digest_history.json"


def load_digest_history() -> Dict[str, Dict]:
    """Load daily digest history."""
    if not os.path.exists(DIGEST_HISTORY_FILE):
        return {}
    
    try:
        with open(DIGEST_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading digest history: {e}")
        return {}


def save_digest_history(history: Dict[str, Dict]) -> None:
    """Save daily digest history."""
    try:
        with open(DIGEST_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving digest history: {e}")


def get_todays_date() -> str:
    """Get today's date as ISO string."""
    return datetime.now().date().isoformat()


def has_digest_been_sent_today(user_id: str) -> bool:
    """Check if digest has already been sent today."""
    history = load_digest_history()
    today = get_todays_date()
    
    user_history = history.get(user_id, {})
    return today in user_history


def record_digest_sent(user_id: str) -> None:
    """Record that digest was sent today."""
    history = load_digest_history()
    today = get_todays_date()
    
    if user_id not in history:
        history[user_id] = {}
    
    history[user_id][today] = {
        "sent_at": datetime.now().isoformat(),
        "status": "sent"
    }
    
    save_digest_history(history)


def process_daily_digests() -> int:
    """
    Main entry point for daily digest job.
    Sends digest to all users who:
    1. Have notifications enabled
    2. Have a valid email
    3. Haven't received digest today
    4. Have completed onboarding
    
    Returns: Number of digests sent
    """
    try:
        storage = get_storage()
        users = storage.list_users()
        sent_count = 0
        
        for user_id in users:
            if should_send_digest(user_id):
                if send_digest_to_user(user_id):
                    sent_count += 1
                    record_digest_sent(user_id)
        
        print(f"📧 Daily digest job complete. Sent {sent_count} digest(s).")
        return sent_count
    
    except Exception as e:
        print(f"Error in daily digest job: {e}")
        return 0


def should_send_digest(user_id: str) -> bool:
    """Check if user qualifies for daily digest."""
    try:
        storage = get_storage()
        
        # Check: notifications enabled
        if not storage.get_notifications_enabled(user_id):
            return False
        
        # Check: email set
        email = storage.get_user_email(user_id)
        if not email:
            return False
        
        # Check: already sent today
        if has_digest_been_sent_today(user_id):
            return False
        
        # Check: onboarding complete
        from onboarding import has_completed_onboarding
        if not has_completed_onboarding(user_id):
            return False
        
        # Check: user is past Day 0 (has some history)
        days = calculate_days_since_signup(user_id)
        if days < 0:
            return False
        
        return True
    
    except Exception as e:
        print(f"Error checking digest eligibility for {user_id}: {e}")
        return False


def send_digest_to_user(user_id: str) -> bool:
    """Generate and send daily digest for a user."""
    try:
        storage = get_storage()
        data = storage.load_data(user_id)
        profile = get_coaching_profile(user_id)
        email = storage.get_user_email(user_id)
        
        if not email:
            return False
        
        # Get today's data
        today = get_todays_date()
        today_completions = data.get("completions", {}).get(today, [])
        habits = data.get("habits", {})
        
        # Get streaks
        streaks = _calculate_current_streaks(data)
        
        # Generate email
        subject, body = _generate_digest_content(
            user_id,
            profile,
            today_completions,
            habits,
            streaks,
            data
        )
        
        # Send email
        send_email(email, subject, body)
        return True
    
    except Exception as e:
        print(f"Error sending digest to {user_id}: {e}")
        return False


def _calculate_current_streaks(data: Dict) -> Dict[str, int]:
    """Calculate current streak for each active habit."""
    completions = data.get("completions", {})
    habits = data.get("habits", {})
    today = datetime.now().date()
    
    streaks = {}
    
    for habit_name in habits:
        if not habits[habit_name].get("active", True):
            continue
        
        streak = 0
        check_date = today
        
        while True:
            date_str = check_date.isoformat()
            if date_str in completions and habit_name in completions[date_str]:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        streaks[habit_name] = streak
    
    return streaks


def _generate_digest_content(
    user_id: str,
    profile: Dict,
    today_completions: List[str],
    habits: Dict,
    streaks: Dict,
    data: Dict
) -> tuple[str, str]:
    """Generate subject and body for daily digest email."""
    
    # Count completions
    completed_count = len(today_completions)
    active_habits_count = sum(1 for h in habits.values() if h.get("active", True))
    
    # Determine sentiment
    if completed_count == 0:
        sentiment = "Let's Get Back on Track"
        emoji = "🌱"
    elif completed_count < active_habits_count / 2:
        sentiment = "Good Start!"
        emoji = "⚡"
    elif completed_count == active_habits_count:
        sentiment = "Perfect Day! 🔥"
        emoji = "🔥"
    else:
        sentiment = "Nice Progress!"
        emoji = "⭐"
    
    subject = f"{emoji} Daily Digest: {sentiment} (Day {calculate_days_since_signup(user_id)})"
    
    # Build body
    body = f"""
Hello {profile.get('success_factor', 'champion')},

**📊 Your Day at a Glance**

✅ Completed Today: {completed_count}/{active_habits_count} habits

"""
    
    # List completed habits with streaks
    if today_completions:
        body += "**🎯 Today's Wins:**\n"
        for habit in today_completions:
            streak = streaks.get(habit, 0)
            streak_emoji = "🔥" if streak >= 7 else ("⚡" if streak >= 3 else "🌱")
            body += f"- {habit} {streak_emoji} {streak}-day streak!\n"
        body += "\n"
    
    # List missed habits
    missed = [h for h in habits if habits[h].get("active", True) and h not in today_completions]
    if missed:
        body += "**📋 Didn't Get To:**\n"
        for habit in missed[:3]:
            body += f"- {habit}\n"
        
        body += f"""

**Quick Reflection:** What got in the way today? Was it:
- Time? Try a different time slot
- Energy? Scale the habit down temporarily
- Forgot? Add a phone reminder or habit stack
- Not feeling it? Remember: even 1 minute counts

"""
    
    # Add streaks summary
    body += "**🔥 Your Streaks:**\n"
    for habit, streak in sorted(streaks.items(), key=lambda x: x[1], reverse=True):
        if habits.get(habit, {}).get("active", True):
            if streak > 0:
                body += f"- {habit}: {streak} days\n"
    
    body += "\n"
    
    # Add adaptive coaching (after Day 14)
    days = calculate_days_since_signup(user_id)
    if days >= 14:
        coaching_email = get_coaching_email_for_user(user_id)
        if coaching_email:
            body += f"""
**🎓 Today's Coaching Tip:**

{coaching_email['body'][:500]}...

"""
    
    # Add reflection prompt
    body += f"""
**💭 Reflection Prompt:**
"Today I prioritized {', '.join(today_completions[:2]) if today_completions else 'rest and recovery'}. 
Tomorrow I want to focus on..."

Keep building. You're on Day {calculate_days_since_signup(user_id)} of your journey.

Your XP Tracker
"""
    
    return subject, body


def get_user_digest_preference(user_id: str) -> Dict[str, Any]:
    """Get user's digest preferences."""
    profile = get_coaching_profile(user_id)
    
    return {
        "enabled": profile.get("notifications_enabled", True),
        "send_time": profile.get("digest_time", "20:00"),  # 8 PM default
        "timezone": profile.get("timezone", "UTC"),
        "email": None  # Caller should fetch
    }
