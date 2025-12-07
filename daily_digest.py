"""
Daily Digest System
Sends a single personalized daily email summarizing:
- Today's habit completions
- Current streaks
- One reflection prompt
- Adaptive coaching based on performance
Responses in style of Thug Kitchen Cookbook meets the movie Heathers, but warm underneath.


This replaces per-completion notifications for a cleaner experience.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
from storage import get_storage
from email_utils import send_email
from onboarding import get_coaching_profile, calculate_days_since_signup
from coaching_engine import get_coaching_email_for_user
from coaching_emails import get_gemini_client


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


def _tz_abbr(tz_name: str) -> str:
    """Return a short timezone label (e.g., EST/PST) from a tz database name."""
    if not tz_name:
        return "UTC"
    if ZoneInfo:
        try:
            now = datetime.now(ZoneInfo(tz_name))
            abbr = now.tzname()
            if abbr:
                return abbr
        except Exception:
            pass
    short = tz_name.split("/")[-1]
    if len(short) <= 4:
        return short.upper()
    return tz_name



def _generate_digest_content(
    user_id: str,
    profile: Dict,
    today_completions: List[str],
    habits: Dict,
    streaks: Dict,
    data: Dict
) -> tuple[str, str]:
    """Generate a single, irreverent daily digest with wins, misses, and next moves."""
    completed_count = len(today_completions)
    active_habits = {h: v for h, v in habits.items() if v.get("active", True)}
    active_habits_count = len(active_habits)
    missed = [h for h in active_habits if h not in today_completions]

    longest = max(streaks.items(), key=lambda x: x[1], default=(None, 0))
    broken = [h for h in missed if streaks.get(h, 0) == 0]

    tz_name = profile.get("timezone", "UTC") or "UTC"
    tz_label = _tz_abbr(tz_name)
    try:
        local_now = datetime.now(ZoneInfo(tz_name)) if ZoneInfo else datetime.utcnow()
    except Exception:
        local_now = datetime.utcnow()
    clock = local_now.strftime("%I:%M %p").lstrip("0")

    day_num = calculate_days_since_signup(user_id)
    if completed_count == active_habits_count and active_habits_count > 0:
        subject = f"🔥 Day {day_num}: Perfect. Don't get cute tomorrow."
    elif completed_count == 0:
        subject = f"🩸 Day {day_num}: Nothing done. Tomorrow gets no excuses."
    else:
        subject = f"⚡ Day {day_num}: {completed_count}/{active_habits_count} done. We push again."

    wins_lines = []
    for habit in today_completions:
        streak = streaks.get(habit, 0)
        tag = "🚀" if streak >= 7 else "🌶️" if streak >= 3 else "✅"
        wins_lines.append(f"- {habit} {tag} {streak}-day streak")

    miss_lines = []
    for habit in missed:
        miss_lines.append(f"- {habit} -> do the 2-minute version tomorrow, no speeches.")

    streak_callouts = []
    if longest[0]:
        streak_callouts.append(f"Longest streak: {longest[0]} at {longest[1]} days. Guard it.")
    if broken:
        streak_callouts.append(f"Streaks that died today: {', '.join(broken)}. Mourn later, restart now.")
    if not streak_callouts:
        streak_callouts.append("No streak drama. Keep stacking.")

    chrono = profile.get("chronotype", "flexible")
    anchor = "right after coffee" if "morning" in chrono else "right after work" if "even" in chrono else "before you crash"
    next_moves = []
    for habit in (missed[:2] or today_completions[:2]):
        next_moves.append(f"- {habit}: drop a 5-10m rep {anchor}. No perfectionism.")

    success_name = profile.get("success_factor") or profile.get("main_habit") or "friend"
    goals = profile.get("life_goals", [])
    goals_tag = f"Goals on deck: {', '.join(goals[:2])}" if goals else "No goals listed - pick one."

    opener = None
    client = get_gemini_client()
    if client:
        prompt = f"""
You are a blunt, dark-humor coach (Thug Kitchen vibe). Write ONE short opener line (<30 words) recapping today:
- Completed: {completed_count}/{active_habits_count}
- Wins: {today_completions}
- Misses: {missed}
- Tone: irreverent, encouraging, zero fluff, clear direction.
"""
        try:
            opener = client.generate_content(prompt).text.strip().splitlines()[0]
        except Exception:
            opener = None

    if not opener:
        opener = f"{completed_count}/{active_habits_count} done. Less talk, more reps tomorrow."

    days = calculate_days_since_signup(user_id)
    coaching_tip = ""
    if days >= 14:
        coaching_email = get_coaching_email_for_user(user_id)
        if coaching_email:
            coaching_tip = f"\n🧠 Coaching tip: {coaching_email['body'].strip()[:400]}"

    body = f"""Hey {success_name},

{opener}

⏰ Clock: {clock} {tz_label}

🏅 Wins
{os.linesep.join(wins_lines) if wins_lines else 'None. Start with one easy rep tomorrow.'}

🩸 Misses
{os.linesep.join(miss_lines) if miss_lines else 'None today. Keep it tight.'}

📊 Streak Radar
{os.linesep.join(streak_callouts)}

🎯 Next Moves
{os.linesep.join(next_moves) if next_moves else 'Pick the easiest habit and do 2 minutes right after coffee.'}

🧠 Vibe
{goals_tag}{coaching_tip}

Remember: consistency beats heroic effort. Tiny reps, ruthless follow-through, dark humor optional.

- XP Tracker (still cheering, still roasting)
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
