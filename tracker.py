import streamlit as st
import datetime
import json
import time
import uuid
import csv
import io
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components
from storage import get_storage, validate_email
from email_utils import send_email
import notifications
from coaching_emails import get_gemini_client, get_gemini_status
import urllib.parse
import os
try:
    import firebase_admin
    from firebase_admin import auth as fb_auth, credentials as fb_credentials
except ImportError:
    firebase_admin = None
    fb_auth = None
    fb_credentials = None
from onboarding import (
    show_onboarding_modal,
    save_onboarding_profile,
    has_completed_onboarding,
    show_profile_editor,
    get_coaching_profile,
)
from goals_recommendation import generate_goal_recommendations, generate_goal_recommendations_gemini
import ai_chat
import coaching_engine

# === OPTION 3: IMPORT & INITIALIZE SCHEDULER ===
try:
    import scheduler_service
except ImportError:
    # APScheduler not installed yet - will fail gracefully
    scheduler_service = None

# --- Configuration & Constants ---
st.set_page_config(
    page_title="Heroic Everyday",
    page_icon="⚡",
    layout="wide"
)

# --- Obsidian Luxe theme ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Libre+Baskerville:wght@400;700&display=swap');
    :root {
        --bg-obsidian: #1A1A1D;
        --gold: #EDCFA9;
        --bronze: #C5A880;
        --ash: #333533;
        --copper: #AA5A25;
        --pearl: #F8F1F1;
    }
    .stApp {
        background-color: var(--bg-obsidian);
        color: var(--bronze);
    }
    .stApp, .stMarkdown, .css-18e3th9, .css-1d391kg {
        font-family: 'Libre Baskerville', serif;
        color: var(--bronze);
    }
    .stMarkdown p, .stMarkdown li, .stMarkdown div {
        color: var(--bronze);
    }
    h1, h2, h3, h4, h5, h6, .stTabs [data-baseweb="tab"] {
        font-family: 'Cinzel', serif !important;
        letter-spacing: 0.5px;
        color: var(--gold);
    }
    .stTabs [data-baseweb="tab"] {
        background: var(--ash);
        color: var(--bronze);
        border-radius: 6px;
        margin-right: 6px;
        padding: 8px 12px;
        border: 1px solid var(--bronze);
    }
    .stTabs [aria-selected="true"] {
        background: var(--gold) !important;
        color: #1A1A1D !important;
    }
    .stButton>button, .stDownloadButton>button {
        background: linear-gradient(135deg, var(--gold), var(--bronze));
        color: #1A1A1D;
        border: 0;
        border-radius: 6px;
        font-family: 'Cinzel', serif;
        font-weight: 600;
    }
    .stTextInput>div>input, .stSelectbox>div>div>select, .stTextArea>div>textarea, .stNumberInput input, .stDateInput input {
        background: var(--ash);
        color: var(--gold);
        border-radius: 6px;
        border: 1px solid var(--bronze);
    }
    .stMetric {
        background: var(--ash);
        padding: 10px;
        border-radius: 8px;
        border: 1px solid var(--bronze);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

XP_PER_LEVEL = 200

# Rank thresholds
RANKS = {
    1: "🌱 Novice",
    5: "🗡️ Squire",
    10: "🛡️ Knight",
    20: "👑 Champion",
    50: "🐉 Legend"
}

PRIORITY_MAP = {
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🔵"
}
PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
MISSION_CSV_TEMPLATE_DEFAULT = """due_date,title,description,goal,priority,xp,context,cadence
2025-12-11,Create two QR codes: Tickets + VIP add-on.,Create two QR codes: Tickets + VIP add-on.,General,Medium,50,Work,One-Off
2025-12-11,Set autoresponder email asking for guest name/email after purchase.,Set autoresponder email asking for guest name/email after purchase.,General,Medium,50,Work,One-Off
2025-12-11,Load your 40-list into tracker; segment A(10)/B(20)/C(10).,Load your 40-list into tracker; segment A(10)/B(20)/C(10).,General,Medium,50,Work,One-Off
"""


def get_mission_csv_template() -> str:
    """Return the mission CSV template, reading from file if available."""
    try:
        with open("missions_template.csv", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return MISSION_CSV_TEMPLATE_DEFAULT

def get_active_goals(data: Dict[str, Any]) -> List[str]:
    """Return non-archived goals in stored order."""
    archived = set(data.get("archived_goals", []))
    return [g for g in data.get("goals", []) if g and g not in archived]


def _get_app_url() -> str:
    app_url = None
    if hasattr(st, 'secrets') and st.secrets.get('app'):
        app_url = st.secrets.get('app', {}).get('url')
    app_url = app_url or os.environ.get('APP_URL') or 'http://localhost:8501'
    return app_url.rstrip('/')


def send_verification_email(user_id: str, email: str, storage) -> bool:
    token = storage.create_email_verification_token(user_id)
    if not token:
        return False
    app_url = _get_app_url()
    params = {'verify_user': user_id, 'verify_token': token}
    link = app_url + '/?' + urllib.parse.urlencode(params)
    subject = 'XP Tracker: Verify your email'
    body = f'Hello {user_id},\n\nPlease verify your email to activate your account:\n{link}\n\nThis link expires in 24 hours.'
    return send_email(email, subject, body)


def email_in_use(storage, email: str) -> bool:
    """Check if any existing user has this email."""
    try:
        for u in storage.list_users():
            if storage.get_user_email(u) == email:
                return True
    except Exception:
        pass
    return False

# --- Data Management Wrappers ---

def get_user_id():
    """Retrieve the current user ID from session state or default."""
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = "default"
    return st.session_state['user_id']

def load_data() -> Dict[str, Any]:
    return get_storage().load_data(get_user_id())

def save_data(data: Dict[str, Any]) -> None:
    get_storage().save_data(get_user_id(), data)

# --- Core Logic ---

BADGES_DEF = {
    "week_streak": {"name": "🔥 On Fire", "desc": "7 Day Streak on any habit", "icon": "🔥"},
    "month_streak": {"name": "⚡ Unstoppable", "desc": "30 Day Streak on any habit", "icon": "⚡"},
    "habit_master": {"name": "🧘 Grandmaster", "desc": "Reach Level 3 on a habit", "icon": "🧘"},
    "perfect_week": {"name": "🌟 Perfectionist", "desc": "7 Perfect Days", "icon": "🌟"},
    "task_force": {"name": "📋 Task Force", "desc": "Complete 10 Missions", "icon": "📋"},
    "veteran": {"name": "⚔️ Veteran", "desc": "Reach Level 10 Profile", "icon": "⚔️"}
}

def get_date_str(offset: int = 0) -> str:
    d = datetime.date.today() + datetime.timedelta(days=offset)
    return d.isoformat()

def get_week_range(week_offset: int = 0):
    """Get start and end dates for a week (Monday to Sunday)"""
    today = datetime.date.today()
    # Calculate the start of the current week (Monday)
    start_of_week = today - datetime.timedelta(days=today.weekday())
    # Apply week offset
    start_of_week += datetime.timedelta(weeks=week_offset)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return start_of_week, end_of_week

def calculate_stats(data: Dict[str, Any]):
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    tasks = data.get("tasks", [])
    
    habit_stats = {h: {'streak': 0, 'total_xp': 0, 'completions': 0, 'level': 1} for h in habits}
    global_xp = 0
    perfect_days_count = 0
    
    # Active habits count (approximation for perfect day logic)
    active_habits = [h for h, d in habits.items() if d.get("active", True)]
    active_count = len(active_habits)

    # 1. Historical XP Calculation (Habits)
    all_dates = sorted(list(completions.keys()))
    temp_streaks = {h: 0 for h in habits}
    
    if all_dates:
        start_date = datetime.date.fromisoformat(all_dates[0])
        end_date = datetime.date.today()
        delta = datetime.timedelta(days=1)
        
        current_d = start_date
        while current_d <= end_date:
            d_str = current_d.isoformat()
            days_completed = completions.get(d_str, [])
            
            # Count daily completions
            daily_habits_done = 0

            for habit, details in habits.items():
                base_xp = details['xp']
                
                if habit in days_completed:
                    daily_habits_done += 1
                    temp_streaks[habit] += 1
                    current_streak = temp_streaks[habit]
                    
                    # Track total completions
                    habit_stats[habit]['completions'] += 1

                    # Bonus: 10% per extra streak day
                    bonus_multiplier = 0.1 * (current_streak - 1)
                    if bonus_multiplier < 0: bonus_multiplier = 0
                    
                    earned_xp = int(base_xp * (1 + bonus_multiplier))
                    
                    habit_stats[habit]['total_xp'] += earned_xp
                    global_xp += earned_xp
                else:
                    temp_streaks[habit] = 0
            
            # Perfect Day Bonus (All active habits completed)
            # Logic: Ensure ALL active habits are in the completion list for this day
            if active_count > 0:
                # Get set of active habit names
                active_habit_names = {h for h, d in habits.items() if d.get("active", True)}
                # Get set of completed habits for this day
                completed_today = set(days_completed)

                # Check if all active habits are completed
                if active_habit_names.issubset(completed_today):
                    global_xp += 50 # Bonus XP for perfect day
                    perfect_days_count += 1

            current_d += delta

    # 2. Display Streak Calculation (Backward check)
    today_str = get_date_str(0)
    for habit in habits:
        streak = 0
        check_date = datetime.date.today()
        while True:
            d_str = check_date.isoformat()
            completed_on_date = habit in completions.get(d_str, [])
            
            if completed_on_date:
                streak += 1
                check_date -= datetime.timedelta(days=1)
            else:
                if d_str == today_str:
                    check_date -= datetime.timedelta(days=1)
                    continue
                else:
                    break
        habit_stats[habit]['streak'] = streak

        # Calculate Level (Simple: Level up every 30 completions)
        habit_stats[habit]['level'] = 1 + (habit_stats[habit]['completions'] // 30)

    # 3. Task XP Calculation
    completed_tasks_count = 0
    for task in tasks:
        if task.get("status") == "Done":
            global_xp += task.get("xp", 0)
            completed_tasks_count += 1

    # 4. Badges Calculation
    earned_badges = []

    # Streak Badges
    max_streak = 0
    for h in habits:
        s = habit_stats[h]['streak']
        if s > max_streak: max_streak = s
        if habit_stats[h]['level'] >= 3:
            earned_badges.append("habit_master")

    if max_streak >= 7: earned_badges.append("week_streak")
    if max_streak >= 30: earned_badges.append("month_streak")

    if perfect_days_count >= 7: earned_badges.append("perfect_week")
    if completed_tasks_count >= 10: earned_badges.append("task_force")

    # Profile Level Badge (calculated outside, but we can check xp)
    # We'll handle veteran in the main loop or pass level in

    return global_xp, habit_stats, list(set(earned_badges))

def calculate_level(total_xp: int):
    level = 1 + (total_xp // XP_PER_LEVEL)
    xp_in_level = total_xp % XP_PER_LEVEL
    progress = xp_in_level / XP_PER_LEVEL
    return level, xp_in_level, progress

def get_rank(level: int) -> str:
    current_rank = "🌱 Novice"
    for threshold, title in sorted(RANKS.items()):
        if level >= threshold:
            current_rank = title
    return current_rank

def get_weekly_stats(data: Dict[str, Any], week_offset: int = 0):
    """Calculate stats for a specific week"""
    start_date, end_date = get_week_range(week_offset)
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    
    weekly_data = {}
    total_weekly_xp = 0
    
    # Initialize daily data
    daily_stats = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        day_name = current_date.strftime("%a")
        daily_stats[date_str] = {"day_name": day_name, "xp": 0, "habits_completed": 0}
        current_date += datetime.timedelta(days=1)
    
    # Calculate daily XP from habits
    for habit, details in habits.items():
        if not details.get("active", True):
            continue
        base_xp = details['xp']
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            if habit in completions.get(date_str, []):
                daily_stats[date_str]["xp"] += base_xp
                daily_stats[date_str]["habits_completed"] += 1
                total_weekly_xp += base_xp
            current_date += datetime.timedelta(days=1)
    
    # Calculate daily XP from tasks (completed during that week)
    tasks = data.get("tasks", [])
    for task in tasks:
        if task.get("status") == "Done" and task.get("completed_at"):
            completed_date = task["completed_at"][:10]
            if start_date.isoformat() <= completed_date <= end_date.isoformat():
                daily_stats[completed_date]["xp"] += task.get("xp", 0)
                total_weekly_xp += task.get("xp", 0)
    
    return daily_stats, total_weekly_xp, start_date, end_date

def get_leaderboard_stats(time_period: str = "all_time") -> List[tuple]:
    """Calculate XP for all users for a given time period.
    Returns list of (user_id, total_xp) sorted by XP descending.
    time_period: "all_time", "week", "month", "year"
    """
    users = get_existing_users()
    leaderboard = []
    
    now = datetime.date.today()
    if time_period == "week":
        start_date = now - datetime.timedelta(days=now.weekday())
    elif time_period == "month":
        start_date = now.replace(day=1)
    elif time_period == "year":
        start_date = now.replace(month=1, day=1)
    else:  # all_time
        start_date = None
    
    for user_id in users:
        storage = get_storage()
        user_data = storage.load_data(user_id)
        prefs = user_data.get("preferences", {})
        if prefs.get("private_mode"):
            continue
        global_xp, _, _ = calculate_stats(user_data)
        
        # If filtering by time period, recalculate XP for that period only
        if start_date:
            habits = user_data.get("habits", {})
            completions = user_data.get("completions", {})
            tasks = user_data.get("tasks", [])
            period_xp = 0
            
            # Calculate habit XP for period
            for date_str in completions.keys():
                date_obj = datetime.date.fromisoformat(date_str)
                if date_obj >= start_date:
                    for habit_name in completions[date_str]:
                        if habit_name in habits:
                            period_xp += habits[habit_name].get("xp", 0)
            
            # Calculate task XP for period
            for task in tasks:
                if task.get("status") == "Done" and task.get("completed_at"):
                    completed_date = datetime.date.fromisoformat(task["completed_at"][:10])
                    if completed_date >= start_date:
                        period_xp += task.get("xp", 0)
            
            global_xp = period_xp
        
        leaderboard.append((user_id, global_xp))
    
    # Sort by XP descending
    leaderboard.sort(key=lambda x: x[1], reverse=True)
    return leaderboard


def _obstacle_hint(obstacle: str) -> str:
    obstacle = obstacle.lower()
    if "time" in obstacle:
        return "keeps it short so it fits busy days"
    if "motivation" in obstacle or "discipline" in obstacle:
        return "is tiny enough to keep your streak alive"
    if "forget" in obstacle:
        return "ties to an existing trigger so you remember"
    if "perfect" in obstacle:
        return "defaults to a small win to avoid all-or-nothing thinking"
    return "is small and repeatable to build momentum"


def _chronotype_anchor(chronotype: str) -> str:
    if "evening" in chronotype:
        return "evening wind-down"
    if "morning" in chronotype:
        return "morning start"
    return "midday anchor"


def _clean_json_block(text: str) -> str:
    """Strip fences/markdown from model responses to get JSON."""
    cleaned = text.strip()
    if "```" in cleaned:
        # Prefer explicit json fences
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[-1]
        else:
            cleaned = cleaned.split("```", 1)[-1]
        cleaned = cleaned.split("```", 1)[0]
    return cleaned


def _parse_gemini_habit_recs(raw: str, default_goal: str, default_xp: int) -> List[Dict[str, Any]]:
    """Parse Gemini JSON payload into habit rec format."""
    try:
        payload = json.loads(raw)
    except Exception:
        return []

    recs: List[Dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        goal = str(item.get("goal", default_goal)).strip() or default_goal
        reason = str(item.get("reason", "")).strip() or "Fits your focus."
        xp_val = item.get("xp", default_xp)
        try:
            xp_val = int(xp_val)
        except Exception:
            xp_val = default_xp
        xp_val = max(5, min(200, xp_val))
        recs.append({"name": name, "goal": goal, "xp": xp_val, "reason": reason})
        if len(recs) >= 5:
            break
    return recs


def generate_habit_recommendations_gemini(
    profile: Dict[str, Any],
    focus_goals: List[str],
    effort_minutes: int,
    cadence: str,
    extra_context: Dict[str, Any],
    existing_habits: List[str],
) -> List[Dict[str, Any]]:
    """Use Gemini for varied, hyper-personalized habit ideas."""
    client = get_gemini_client()
    if not client:
        return []

    goals = focus_goals or profile.get("life_goals", []) or ["General"]
    default_goal = goals[0]
    chronotype = profile.get("chronotype", "flexible")
    anchor = _chronotype_anchor(chronotype)
    obstacle = profile.get("biggest_obstacle", "")
    why_now = profile.get("why_now", "")
    success_factor = profile.get("success_factor", "")

    prompt = f"""
You are an elite habit coach. Propose 4–5 creative, specific habit ideas that feel varied (mix anchor ritual, prep, social/accountability, and micro-moves). Hyper-personalize to the inputs. Stay realistic and keep XP aligned to effort.

Return ONLY JSON (no markdown, no prose) in this exact shape:
[{{"name": "Do it", "goal": "Health", "xp": 15, "reason": "Why this works"}}]

Goals to support: {', '.join(goals)}
Cadence style: {cadence}
Effort budget per habit: {effort_minutes} minutes
Chronotype anchor: {anchor}
Main habit: {profile.get("main_habit", "") or "n/a"}
Biggest obstacle: {obstacle or "n/a"}
Why now: {extra_context.get("why_this_week") or why_now or "n/a"}
Success factor: {success_factor or "n/a"}
Preferred vibe: {extra_context.get("vibe", "balanced")}
Challenge level: {extra_context.get("challenge", "standard")}
Energy/where: {extra_context.get("energy", "variable")} / {extra_context.get("environment", "flexible")}
Anchor/trigger hint: {extra_context.get("anchor_hint", "fit to daily flow")}
Avoid duplicating existing habits: {', '.join(existing_habits) or "none"}

Rules:
- Make each idea concrete with the cadence and anchor; avoid generic advice.
- Vary formats (prep ritual, execution block, reflection, social check-in).
- Keep xp close to effort_minutes unless a shorter micro-move is justified.
"""

    try:
        response = client.generate_content(prompt)
        cleaned = _clean_json_block(response.text)
        recs = _parse_gemini_habit_recs(cleaned, default_goal, max(8, min(40, effort_minutes)))
        return recs
    except Exception as e:
        print(f"Gemini habit rec error: {e}")
        return []


def generate_habit_recommendations(profile: Dict[str, Any], focus_goals: List[str], effort_minutes: int, cadence: str) -> List[Dict[str, Any]]:
    """Deterministic 'GPT-like' habit ideas tailored to onboarding answers."""
    goals = focus_goals or profile.get("life_goals", []) or ["General"]
    obstacle = profile.get("biggest_obstacle", "")
    chronotype = profile.get("chronotype", "flexible")
    main_habit = profile.get("main_habit", "")
    anchor = _chronotype_anchor(chronotype)
    reason_tail = _obstacle_hint(obstacle)
    xp = max(8, min(40, effort_minutes))  # keep XP aligned with effort

    ideas = []

    def add_idea(name: str, goal: str, why: str):
        if len(ideas) >= 4:
            return
        if any(i["name"].lower() == name.lower() for i in ideas):
            return
        ideas.append({"name": name, "goal": goal, "xp": xp, "reason": why})

    # Reinforce the main habit if provided
    if main_habit:
        add_idea(
            f"{main_habit} ({cadence})",
            goals[0],
            f"Directly supports your main habit with a {anchor} slot and {reason_tail}.",
        )

    for goal in goals:
        gl = goal.lower()
        if "health" in gl or "fit" in gl:
            add_idea(
                f"{effort_minutes}m mobility {anchor}",
                goal,
                f"Quick body prep in your {anchor}; {reason_tail}.",
            )
            add_idea(
                "Prep tomorrow's meal/snacks",
                goal,
                f"Evening 5–10m batch prep reduces friction for your health goal.",
            )
        elif "career" in gl or "learn" in gl:
            add_idea(
                f"{effort_minutes}m deep work warm-up",
                goal,
                f"{anchor.title()} sprint on your top task; finishes with writing tomorrow's first step.",
            )
            add_idea(
                "Capture one insight and share it",
                goal,
                "Write one takeaway daily; ships a tiny artifact to build credibility.",
            )
        elif "mental" in gl or "mind" in gl:
            add_idea(
                "5m box-breathing before first screen",
                goal,
                f"{anchor.title()} nervous-system reset; {reason_tail}.",
            )
        elif "relationship" in gl or "community" in gl:
            add_idea(
                "Send one thoughtful check-in",
                goal,
                "One message or voice note daily; easy to sustain and compounds connection.",
            )
        elif "financial" in gl or "money" in gl:
            add_idea(
                "3m spend review + next-day plan",
                goal,
                "Micro review right after dinner; links to an existing routine to avoid forgetting.",
            )
        elif "creativity" in gl or "creative" in gl:
            add_idea(
                f"{effort_minutes}m create-before-consume",
                goal,
                f"{anchor.title()} make a small thing before scrolling; protects creative time.",
            )
        elif "spiritual" in gl:
            add_idea(
                "5m reflection with one line of gratitude",
                goal,
                f"Tuck it into your {anchor} to make it automatic.",
            )
        else:
            add_idea(
                f"{effort_minutes}m focused block ({goal})",
                goal,
                f"{anchor.title()} anchor to move {goal} forward; {reason_tail}.",
            )

    # If we still have space, add one friction-buster for obstacle
    if len(ideas) < 4:
        if "time" in obstacle.lower():
            add_idea("3m daily plan (one big, one tiny)", goals[0], "Keeps scope realistic so you win the day.")
        elif "forget" in obstacle.lower():
            add_idea("Place visual cue in your trigger spot", goals[0], "Creates a physical reminder so you never miss it.")
        elif "motivation" in obstacle.lower():
            add_idea("Default to 1-minute version", goals[0], "Automatic fallback prevents zero days.")

    return ideas[:4]


def _parse_gemini_task_recs(raw: str, default_goal: str, default_xp: int) -> List[Dict[str, Any]]:
    """Parse Gemini JSON payload into mission format."""
    try:
        payload = json.loads(raw)
    except Exception:
        return []

    recs: List[Dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        title = str(item.get("title") or item.get("name") or "").strip()
        if not title:
            continue
        description = str(item.get("description", "")).strip() or "Clear, time-boxed mission."
        goal = str(item.get("goal", default_goal)).strip() or default_goal
        priority = str(item.get("priority", "Medium")).title()
        if priority not in ["High", "Medium", "Low"]:
            priority = "Medium"
        xp_val = item.get("xp", default_xp)
        try:
            xp_val = int(xp_val)
        except Exception:
            xp_val = default_xp
        xp_val = max(5, min(200, xp_val))
        due_days = item.get("due_in_days") or item.get("due_days")
        try:
            due_days = int(due_days)
        except Exception:
            due_days = None
        recs.append({
            "title": title,
            "description": description,
            "goal": goal,
            "xp": xp_val,
            "priority": priority,
            "due_in_days": due_days,
        })
        if len(recs) >= 5:
            break
    return recs


def generate_task_recommendations_gemini(
    profile: Dict[str, Any],
    goal: str,
    context: str,
    effort_minutes: int,
    urgency: str,
) -> List[Dict[str, Any]]:
    """Use Gemini to suggest missions for the chosen goal."""
    client = get_gemini_client()
    if not client:
        return []

    default_goal = goal or "General"
    why_now = profile.get("why_now", "")
    obstacle = profile.get("biggest_obstacle", "")
    success_factor = profile.get("success_factor", "")
    due_hint = {"Today": 1, "This week": 3, "This month": 7}.get(urgency, 3)

    prompt = f"""
You are an execution-focused coach. Propose 3-4 concrete missions to advance the goal below.

Goal: {default_goal}
Context: {context or "n/a"}
Why Now: {why_now}
Obstacle: {obstacle or "n/a"}
Success Factor: {success_factor or "n/a"}
Effort budget: {effort_minutes} minutes
Target timeframe: {urgency} (about {due_hint} day(s))

Return ONLY JSON (no markdown) in this shape:
[
  {{
    "title": "Deliver sprint outline",
    "description": "Draft a 3-bullet outline and share it with your team.",
    "goal": "{default_goal}",
    "priority": "High",
    "xp": 60,
    "due_in_days": {due_hint}
  }}
]

Rules:
- Make missions shippable and time-boxed.
- Keep XP roughly proportional to effort (around effort_minutes * 2, clamp 10-150).
- Use priority High/Medium/Low only.
- If no due date needed, omit due_in_days.
"""

    try:
        response = client.generate_content(prompt)
        cleaned = _clean_json_block(response.text)
        recs = _parse_gemini_task_recs(cleaned, default_goal, max(10, min(150, effort_minutes * 2)))
        return recs
    except Exception as e:
        print(f"Gemini task rec error: {e}")
        return []


def generate_task_recommendations(goal: str, context: str, effort_minutes: int, urgency: str) -> List[Dict[str, Any]]:
    """Deterministic fallback for mission ideas."""
    xp = max(10, min(150, effort_minutes * 2))
    due_hint = {"Today": 1, "This week": 3, "This month": 7}.get(urgency, 3)
    base = context.strip() if context else f"Move {goal} forward."
    missions = [
        {
            "title": f"{goal}: focused {effort_minutes}m push",
            "description": f"Time-box {effort_minutes} minutes to knock out the next concrete step. {base}",
            "goal": goal,
            "priority": "High",
            "xp": xp,
            "due_in_days": due_hint,
        },
        {
            "title": f"Unblock {goal}",
            "description": "List top 3 blockers, remove one immediately, and schedule the next step.",
            "goal": goal,
            "priority": "Medium",
            "xp": max(10, xp - 10),
            "due_in_days": due_hint,
        },
        {
            "title": f"Share progress on {goal}",
            "description": "Draft a quick update and send it for accountability. Include what you finished and the next move.",
            "goal": goal,
            "priority": "Low",
            "xp": max(10, xp - 20),
            "due_in_days": None,
        },
    ]
    return missions[:3]


def render_guided_setup():
    """Guide new users to create a goal and a habit from onboarding answers."""
    if not st.session_state.get("authenticated_user"):
        return

    data = load_data()
    active_goals = get_active_goals(data) or ["General"]
    archived_goals = data.get("archived_goals", [])
    profile = get_coaching_profile(get_user_id())

    has_habits = bool(data.get("habits"))
    needs_guided = st.session_state.get("guided_setup", False) or not has_habits
    if not needs_guided:
        return

    st.divider()
    st.subheader("Guided Setup: create your first goal and habit")
    st.caption("We pre-filled suggestions from your onboarding so you can start tracking right away.")
    # Starter sprint note
    st.info("Starter Sprint: nail one micro-upgrade + one mission for 7 days. Keep it tiny, keep it moving.")

    suggested_goal = (profile.get("life_goals") or [""])[0] or "First Goal"
    suggested_habit = profile.get("main_habit", "")
    goal_options = get_active_goals(data) or ["General"]
    # Micro-habit nudges
    st.info("Keep it atomic: 2-10 minutes, verb-first, so even a chaotic day can't kill it.")
    contexts = ["Work", "Personal", "Health", "Creativity", "Admin"]

    # --- STEP 1: GOAL DISCOVERY ---
    with st.expander("Step 1: Discover High-Impact Goals", expanded=True):
        st.markdown("**Need goal ideas?** AI can analyze your profile to suggest high-impact goals.")
        if st.button("✨ Generate Goal Ideas"):
            with st.spinner("Analyzing profile..."):
                goal_recs, error_msg = generate_goal_recommendations_gemini(profile)
                if not goal_recs:
                    goal_recs = generate_goal_recommendations(profile)
                    if error_msg:
                        if "API key" in error_msg or "not found" in error_msg:
                            st.warning(f"Gemini unavailable ({error_msg}). Please add `gemini_api_key` to your Streamlit Secrets (Settings > Secrets) to enable AI features.")
                        else:
                            st.warning(f"Gemini error: {error_msg}. Using standard recommendations.")
                    else:
                        st.warning("Gemini returned no results; using standard recommendations.")

                st.session_state["goal_recs"] = goal_recs

        goal_recs = st.session_state.get("goal_recs", [])
        if goal_recs:
            st.write("Select a goal to add:")
            cols = st.columns(2)
            for i, rec in enumerate(goal_recs):
                with cols[i % 2]:
                    with st.container():
                        st.info(f"**{rec['name']}**\n\n_{rec['reason']}_")
                        if st.button(f"Add Goal: {rec['name']}", key=f"add_goal_rec_{i}"):
                            add_goal(rec['name'])
                            st.rerun()

    # --- STEP 2: HABIT CREATION ---
    st.markdown("### Step 2: Build Habits")

    # Habit recommender (deterministic, based on onboarding answers)
    st.markdown("**Need habit ideas?** I'll propose 3-4 habits across your goals.")
    with st.form("habit_rec_settings", clear_on_submit=False):
        focus_default = [g for g in profile.get("life_goals", []) if g in goal_options] or goal_options[:2]
        focus_goals = st.multiselect("Focus areas", options=goal_options, default=focus_default or goal_options)
        cadence = st.selectbox("Cadence style", ["Daily micro", "3x/week", "Weekly anchor"])
        effort_minutes = st.slider("Minutes per habit", min_value=5, max_value=45, value=15, step=5)
        with st.expander("Tell me more so the AI can tailor ideas"):
            why_this_week = st.text_input("What's the push right now?", value=profile.get("why_now", ""))
            anchor_hint = st.text_input("Where should this fit?", placeholder="After coffee, before first meeting, after gym...")
            chrono = profile.get("chronotype", "flexible")
            energy_default = 0 if "morning" in chrono else 2 if "evening" in chrono else 3
            energy = st.selectbox("Energy window", ["Morning focus", "Afternoon push", "Evening wind-down", "Mixed/variable"], index=energy_default)
            vibe = st.selectbox("Coaching vibe", ["Gentle accountability", "Athlete mode", "Builder/creative", "Supportive friend"])
            challenge = st.selectbox("Challenge level", ["Gentle start", "Standard", "Spicy"])
            environment = st.selectbox("Environment", ["Home", "Office", "On the move", "Gym/outdoors", "Flexible"])
        gen_submit = st.form_submit_button("Generate personalized habit ideas")
    if gen_submit:
        extra_context = {
            "why_this_week": why_this_week,
            "anchor_hint": anchor_hint,
            "energy": energy,
            "vibe": vibe,
            "challenge": challenge,
            "environment": environment,
        }
        st.session_state["habit_rec_params"] = {"focus": focus_goals, "cadence": cadence, "effort": effort_minutes, "extra": extra_context}
        gemini_recs = generate_habit_recommendations_gemini(
            profile,
            focus_goals,
            effort_minutes,
            cadence,
            extra_context,
            existing_habits=list(data.get("habits", {}).keys()),
        )
        if gemini_recs:
            st.session_state["habit_recs"] = gemini_recs
            st.session_state["habit_recs_source"] = "gemini"
            st.session_state["habit_recs_notice"] = ""
        else:
            st.session_state["habit_recs"] = generate_habit_recommendations(profile, focus_goals, effort_minutes, cadence)
            st.session_state["habit_recs_source"] = "deterministic"
            st.session_state["habit_recs_notice"] = "Gemini not configured or unavailable; using built-in coach ideas."

    recs = st.session_state.get("habit_recs", [])
    if recs:
        col_sel_all, col_sel_none, col_retry = st.columns(3)
        with col_sel_all:
            if st.button("Select all"):
                for i in range(len(recs)):
                    st.session_state[f"rec_pick_{i}"] = True
        with col_sel_none:
            if st.button("Select none"):
                for i in range(len(recs)):
                    st.session_state[f"rec_pick_{i}"] = False
        with col_retry:
            if st.button("Regenerate ideas"):
                params = st.session_state.get("habit_rec_params", {})
                fg = params.get("focus", focus_goals)
                cd = params.get("cadence", cadence)
                eff = params.get("effort", effort_minutes)
                extra = params.get("extra", {})
                gemini_recs = generate_habit_recommendations_gemini(
                    profile,
                    fg,
                    eff,
                    cd,
                    extra,
                    existing_habits=list(data.get("habits", {}).keys()),
                )
                if gemini_recs:
                    st.session_state["habit_recs"] = gemini_recs
                    st.session_state["habit_recs_source"] = "gemini"
                    st.session_state["habit_recs_notice"] = ""
                else:
                    st.session_state["habit_recs"] = generate_habit_recommendations(profile, fg, eff, cd)
                    st.session_state["habit_recs_source"] = "deterministic"
                    st.session_state["habit_recs_notice"] = "Gemini not configured or unavailable; using built-in coach ideas."
                st.rerun()

        st.write("Review, tweak, and add the habits you like:")
        st.caption("Generated with Gemini" if st.session_state.get("habit_recs_source") == "gemini" else "Generated with rules-based coach")
        notice = st.session_state.get("habit_recs_notice")
        if notice:
            st.info(notice)
        added = False
        updated_recs = []
        for i, rec in enumerate(recs):
            st.markdown(f"**Idea {i+1}:** {rec['reason']}")
            name = st.text_input("Name", value=rec["name"], key=f"rec_name_{i}")
            # Ensure goal option exists
            goal_choices = list(dict.fromkeys(goal_options + [rec["goal"]]))
            goal_choice = st.selectbox("Goal", options=goal_choices, index=goal_choices.index(rec["goal"]), key=f"rec_goal_{i}")
            xp_val = st.number_input("XP", min_value=5, max_value=200, value=int(rec["xp"]), step=5, key=f"rec_xp_{i}")
            desc_val = st.text_area("Description", value=rec.get("reason", ""), height=64, key=f"rec_desc_{i}")
            context_choice = st.selectbox("Context", options=contexts, index=contexts.index(rec.get("context", contexts[0])) if rec.get("context") in contexts else 0, key=f"rec_ctx_{i}")
            cadence_choice = st.selectbox("Cadence", options=["Daily", "3x/Week", "Weekly", "One-Off"], key=f"rec_cadence_{i}")
            pick = st.checkbox("Add this habit", value=True, key=f"rec_pick_{i}")
            add_task_flag = st.checkbox("Also add as mission", value=False, key=f"rec_task_{i}")
            if add_task_flag:
                task_priority = st.selectbox("Mission priority", ["High", "Medium", "Low"], index=1, key=f"rec_priority_{i}")
            else:
                task_priority = st.session_state.get(f"rec_priority_{i}", "Medium")
            st.divider()
            updated_recs.append({
                "name": name,
                "goal": goal_choice,
                "xp": int(xp_val),
                "description": desc_val.strip() or rec.get("reason", ""),
                "context": context_choice,
                "cadence": cadence_choice,
                "pick": pick,
                "add_task": add_task_flag,
                "task_priority": task_priority,
            })

        if st.button("Add selected habits"):
            added_count = 0
            task_added_count = 0
            for rec in updated_recs:
                if not rec["name"].strip():
                    continue

                # Ensure goal exists for both habits and missions
                if rec["goal"] not in goal_options:
                    add_goal(rec["goal"])
                    goal_options.append(rec["goal"])

                if rec["pick"]:
                    add_new_habit(rec["name"].strip(), rec["xp"], rec["goal"], rec.get("description", ""), rec.get("context", "General"), rec.get("cadence", "Daily"))
                    added_count += 1

                if rec.get("add_task"):
                    add_task(rec["name"].strip(), rec.get("description", ""), rec["xp"], rec["goal"], rec.get("task_priority", "Medium"), None, rec.get("context", "General"), rec.get("cadence", "One-Off"))
                    task_added_count += 1

            if added_count or task_added_count:
                st.session_state["guided_setup"] = False
                st.session_state["habit_recs"] = []
                st.success(f"Added {added_count} habit(s) and {task_added_count} mission(s).")
                st.rerun()
            else:
                st.info("Select at least one habit or mission to add.")

    st.markdown("**Or add your own quickly:**")
    with st.form("guided_goal_form", clear_on_submit=True):
        goal_name = st.text_input("Goal name", value=suggested_goal)
        goal_submit = st.form_submit_button("Create Goal")
    if goal_submit:
        if goal_name.strip():
            add_goal(goal_name.strip())
            st.session_state["guided_setup"] = True
            st.success(f"Goal added: {goal_name.strip()}")
            st.rerun()
        else:
            st.error("Goal name is required.")

    data = load_data()  # Refresh in case a goal was just added
    goal_options = get_active_goals(data) or ["General"]
    default_goal_index = goal_options.index(suggested_goal) if suggested_goal in goal_options else 0

    with st.form("guided_habit_form", clear_on_submit=True):
        habit_name = st.text_input("Habit name", value=suggested_habit)
        habit_desc = st.text_area("Description (optional)", height=68, placeholder="e.g. 'Read 10 pages before bed'")
        habit_goal = st.selectbox("Link to goal", options=goal_options, index=default_goal_index)
        habit_xp = st.number_input("XP reward", min_value=5, max_value=200, value=10, step=5)
        habit_context = st.selectbox("Context", options=contexts, index=0)
        habit_cadence = st.selectbox("Cadence", options=["Daily", "3x/Week", "Weekly", "One-Off"])
        habit_submit = st.form_submit_button("Create Habit")
    if habit_submit:
        if habit_name.strip():
            add_new_habit(habit_name.strip(), int(habit_xp), habit_goal, habit_desc.strip(), habit_context, habit_cadence)
            st.session_state["guided_setup"] = False
            st.success(f"Habit added: {habit_name.strip()}")
            st.rerun()
        else:
            st.error("Habit name is required.")


# --- UI Action Handlers ---

def add_goal(goal_name: str):
    data = load_data()
    goal_name = (goal_name or "").strip()
    if not goal_name:
        st.warning("Goal name is required.")
        return

    if "archived_goals" not in data:
        data["archived_goals"] = []

    if goal_name in data["archived_goals"]:
        data["archived_goals"].remove(goal_name)

    if goal_name not in data["goals"]:
        data["goals"].append(goal_name)
    save_data(data)
    st.success(f"Goal Added: {goal_name}")

def retire_goal(goal_name: str):
    data = load_data()
    goal_name = (goal_name or "").strip()
    if not goal_name:
        st.warning("No goal selected.")
        return
    if "archived_goals" not in data:
        data["archived_goals"] = []
    if goal_name in data["goals"]:
        data["goals"] = [g for g in data["goals"] if g != goal_name]
    if goal_name not in data["archived_goals"]:
        data["archived_goals"].append(goal_name)
    save_data(data)
    st.success(f"Retired goal: {goal_name}")

def restore_goal(goal_name: str):
    data = load_data()
    goal_name = (goal_name or "").strip()
    if not goal_name:
        st.warning("No goal selected.")
        return
    if "archived_goals" not in data:
        data["archived_goals"] = []
    if goal_name in data["archived_goals"]:
        data["archived_goals"] = [g for g in data["archived_goals"] if g != goal_name]
    if goal_name not in data["goals"]:
        data["goals"].append(goal_name)
    save_data(data)
    st.success(f"Restored goal: {goal_name}")

def add_new_habit(name: str, xp: int, goal: str, description: str = "", context: str = "General", cadence: str = "Daily"):
    data = load_data()
    if name and name not in data["habits"]:
        data["habits"][name] = {"xp": xp, "active": True, "goal": goal, "description": description, "context": context, "cadence": cadence}
        save_data(data)
        st.success(f"Added habit: {name}")
    elif name in data["habits"]:
        st.warning("Habit already exists.")
    else:
        st.warning("Invalid name.")

def archive_habit(name: str):
    data = load_data()
    if name in data["habits"]:
        data["habits"][name]["active"] = False
        save_data(data)
        st.success(f"Archived: {name}")

def restore_habit(name: str):
    data = load_data()
    if name in data["habits"]:
        data["habits"][name]["active"] = True
        save_data(data)
        st.success(f"Restored: {name}")

def toggle_habit(habit_name: str, date_str: str):
    data = load_data()
    if date_str not in data["completions"]:
        data["completions"][date_str] = []
    
    current_list = data["completions"][date_str]
    is_completing = habit_name not in current_list
    
    if habit_name in current_list:
        current_list.remove(habit_name)
    else:
        current_list.append(habit_name)
        
    if not current_list:
        del data["completions"][date_str]
    save_data(data)
    
    # === OPTION 2: AUTO-SEND NOTIFICATION ON HABIT COMPLETION ===
    if is_completing:  # Only send when habit is MARKED COMPLETE, not when unchecked
        try:
            # Get authenticated user
            user_id = st.session_state.get('authenticated_user')
            if not user_id:
                # Also check admin context
                user_id = st.session_state.get('user_id')
            
            if user_id:
                # Get habit details
                habit_details = data.get("habits", {}).get(habit_name, {})
                base_xp = habit_details.get("xp", 10)
                
                # Calculate current streak for this habit
                global_xp, habit_stats, earned_badges = calculate_stats(data)
                habit_stat = habit_stats.get(habit_name, {})
                current_streak = habit_stat.get('streak', 0)
                
                # Calculate XP earned (with streak bonus)
                bonus_multiplier = 0.1 * (current_streak - 1)
                if bonus_multiplier < 0:
                    bonus_multiplier = 0
                earned_xp = int(base_xp * (1 + bonus_multiplier))
                
                # Send notification (quietly - won't fail if email not set)
                notifications.notify_habit_completed(user_id, habit_name, earned_xp, current_streak)
        except Exception as e:
            # Silently fail - don't interrupt user experience
            pass

# --- Task Actions ---

def parse_task_due_date(task: Dict[str, Any]) -> Optional[datetime.date]:
    """Return a date object for the task due date, or None if unset/invalid."""
    due_str = task.get("due_date")
    if not due_str:
        return None
    try:
        return datetime.date.fromisoformat(due_str)
    except Exception:
        return None


def get_due_bucket_label(due_date: Optional[datetime.date]) -> str:
    """Human buckets for grouping tasks by due date."""
    today = datetime.date.today()
    if due_date is None:
        return "No Date"
    if due_date < today:
        return "Overdue"
    if due_date == today:
        return "Today"
    if due_date == today + datetime.timedelta(days=1):
        return "Tomorrow"
    if due_date <= today + datetime.timedelta(days=7):
        return "This Week"
    if due_date <= today + datetime.timedelta(days=14):
        return "Next Week"
    return "Later"


def task_sort_key(task: Dict[str, Any]) -> Tuple[datetime.date, int, str]:
    """Sort tasks by due date, priority, then created timestamp."""
    due_date = parse_task_due_date(task)
    priority_rank = PRIORITY_ORDER.get(task.get("priority"), len(PRIORITY_ORDER))
    created_at = task.get("created_at", "")
    return (due_date or datetime.date.max, priority_rank, created_at)


def bucket_tasks_by_due_and_goal(tasks: List[Dict[str, Any]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Group tasks by due-date bucket then goal."""
    bucketed: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for task in tasks:
        bucket = get_due_bucket_label(parse_task_due_date(task))
        goal = task.get("goal", "General")
        bucketed.setdefault(bucket, {}).setdefault(goal, []).append(task)
    for goal_map in bucketed.values():
        for goal, goal_tasks in goal_map.items():
            goal_tasks.sort(key=task_sort_key)
    return bucketed


def format_due_label(due_date: Optional[datetime.date]) -> str:
    """Short label for a task due date."""
    if not due_date:
        return "No due date"
    today = datetime.date.today()
    if due_date < today:
        return f"Overdue: {due_date.strftime('%b %d')}"
    if due_date == today:
        return "Due: Today"
    if due_date == today + datetime.timedelta(days=1):
        return "Due: Tomorrow"
    return f"Due: {due_date.strftime('%b %d')}"

def parse_import_due_date(raw: str) -> Optional[datetime.date]:
    """Parse common date formats used in imports."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.date.fromisoformat(raw)
    except Exception:
        return None


def normalize_priority(raw: str) -> str:
    """Normalize priority to High/Medium/Low."""
    if not raw:
        return "Medium"
    val = raw.strip().lower()
    if val.startswith("h"):
        return "High"
    if val.startswith("l"):
        return "Low"
    return "Medium"


def normalize_cadence(raw: str) -> str:
    """Normalize cadence to supported values."""
    allowed = {"one-off", "daily", "3x/week", "weekly"}
    if not raw:
        return "One-Off"
    val = raw.strip().lower()
    if val not in allowed:
        return "One-Off"
    mapping = {
        "one-off": "One-Off",
        "daily": "Daily",
        "3x/week": "3x/Week",
        "weekly": "Weekly",
    }
    return mapping.get(val, "One-Off")


def normalize_context(raw: str) -> str:
    """Normalize context to supported values."""
    allowed = {"work", "personal", "health", "creativity", "admin"}
    if not raw:
        return "General"
    val = raw.strip().lower()
    if val not in allowed:
        return "General"
    return val.capitalize()


def parse_csv_missions(csv_text: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse missions from CSV text.
    Expected headers: due_date, title, description, goal, priority, xp, context, cadence
    Returns (missions, errors)
    """
    missions: List[Dict[str, Any]] = []
    errors: List[str] = []
    reader = csv.DictReader(io.StringIO(csv_text))

    expected_headers = ["due_date", "title", "description", "goal", "priority", "xp", "context", "cadence"]
    if not reader.fieldnames:
        errors.append("CSV is missing headers. Expected: " + ", ".join(expected_headers))
        return missions, errors
    missing = [h for h in ["title"] if h not in reader.fieldnames]
    if missing:
        errors.append("Missing required column(s): " + ", ".join(missing))
        return missions, errors

    for idx, row in enumerate(reader, start=2):  # start=2 to account for header row
        title = (row.get("title") or "").strip()
        if not title:
            errors.append(f"Row {idx}: title is required.")
            continue
        description = (row.get("description") or "").strip()
        goal = (row.get("goal") or "General").strip() or "General"
        priority = normalize_priority(row.get("priority", "Medium"))
        cadence = normalize_cadence(row.get("cadence", "One-Off"))
        context = normalize_context(row.get("context", "General"))
        due_date = parse_import_due_date(row.get("due_date", ""))

        xp_raw = (row.get("xp") or "").strip()
        try:
            xp_val = int(float(xp_raw)) if xp_raw else 50
        except ValueError:
            xp_val = 50
        xp_val = max(5, min(300, xp_val))

        missions.append({
            "title": title,
            "description": description,
            "goal": goal,
            "priority": priority,
            "cadence": cadence,
            "context": context,
            "xp": xp_val,
            "due_date": due_date,
        })

    return missions, errors


def add_task(title, desc, xp, goal, priority, due_date, context="General", cadence="One-Off"):
    data = load_data()
    new_task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": desc,
        "xp": xp,
        "goal": goal,
        "priority": priority,
        "due_date": due_date.isoformat() if due_date else None,
        "status": "Todo",
        "created_at": datetime.datetime.now().isoformat(),
        "context": context,
        "cadence": cadence
    }
    data["tasks"].append(new_task)
    save_data(data)

def toggle_task_status(task_id, new_status):
    data = load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = new_status
            if new_status == "Done":
                task["completed_at"] = datetime.datetime.now().isoformat()
            break
    save_data(data)

def delete_task(task_id):
    data = load_data()
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    save_data(data)


def update_task(task_id: str, title: str, desc: str, xp: int, goal: str, priority: str, due_date: Optional[datetime.date], context: str, cadence: str):
    """Update mission fields and persist."""
    data = load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["title"] = title
            task["description"] = desc
            task["xp"] = xp
            task["goal"] = goal
            task["priority"] = priority
            task["due_date"] = due_date.isoformat() if due_date else None
            task["context"] = context
            task["cadence"] = cadence
            break
    save_data(data)


def render_task_row(task: Dict[str, Any], key_suffix: str = "", goals: Optional[List[str]] = None):
    """Render a mission with actions and meta info."""
    p_icon = PRIORITY_MAP.get(task.get("priority", "Low"), "🔵")
    due_date = parse_task_due_date(task)
    due_label = format_due_label(due_date)
    with st.container():
        tc1, tc2, tc3, tc4 = st.columns([0.5, 4, 1, 1])
        with tc1:
            if st.button("Complete", key=f"btn_done_{task['id']}{key_suffix}", help="Mark Complete"):
                toggle_task_status(task['id'], "Done")
                st.rerun()
        with tc2:
            st.markdown(f"**{p_icon} {task['title']}**")
            meta_parts = [
                task.get("goal", "General"),
                task.get("context", "General"),
                task.get("cadence", "One-Off"),
                due_label,
            ]
            st.caption(" • ".join(meta_parts))
        with tc3:
            st.markdown(f"**+{task.get('xp', 0)} XP**")
        with tc4:
            if st.button("Delete", key=f"del_{task['id']}{key_suffix}"):
                delete_task(task['id'])
                st.rerun()

        if task.get("description"):
            with st.expander("Details"):
                st.write(task["description"])

        with st.expander("Edit mission"):
            form_key = f"edit_task_{task['id']}{key_suffix}"
            with st.form(form_key):
                goal_options = goals or []
                current_goal = task.get("goal", "General")
                if current_goal and current_goal not in goal_options:
                    goal_options = list(goal_options) + [current_goal]
                if not goal_options:
                    goal_options = [current_goal or "General"]
                context_options = ["General", "Work", "Personal", "Health", "Creativity", "Admin"]
                current_context = task.get("context", "General")

                title_val = st.text_input("Title", value=task.get("title", ""), key=f"title_{form_key}")
                desc_val = st.text_area("Description", value=task.get("description", ""), key=f"desc_{form_key}")
                goal_val = st.selectbox("Goal", options=goal_options, index=goal_options.index(current_goal) if current_goal in goal_options else 0, key=f"goal_{form_key}")
                ctx_default_idx = context_options.index(current_context) if current_context in context_options else 0
                ctx_val = st.selectbox("Context", options=context_options, index=ctx_default_idx, key=f"ctx_{form_key}")
                cad_val = st.selectbox("Cadence", options=["One-Off", "Daily", "3x/Week", "Weekly"], index=["One-Off", "Daily", "3x/Week", "Weekly"].index(task.get("cadence", "One-Off")) if task.get("cadence", "One-Off") in ["One-Off", "Daily", "3x/Week", "Weekly"] else 0, key=f"cad_{form_key}")
                priority_val = st.selectbox("Priority", options=["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(task.get("priority", "Medium")) if task.get("priority", "Medium") in ["High", "Medium", "Low"] else 1, key=f"priority_{form_key}")
                xp_val = st.number_input("XP", min_value=5, max_value=300, value=int(task.get("xp", 50)), step=5, key=f"xp_{form_key}")
                due_val = st.date_input("Due date (optional)", value=due_date, key=f"due_{form_key}")
                clear_due = st.checkbox("Remove due date", value=False, key=f"clear_due_{form_key}")

                if st.form_submit_button("Save changes"):
                    if not title_val.strip():
                        st.error("Title is required.")
                    else:
                        final_due = None if clear_due else due_val
                        update_task(
                            task["id"],
                            title_val.strip(),
                            desc_val.strip(),
                            int(xp_val),
                            goal_val,
                            priority_val,
                            final_due,
                            ctx_val,
                            cad_val,
                        )
                        st.success("Mission updated.")
                        st.rerun()
    st.divider()

# --- Journal Actions ---

def add_journal_section(section_name: str):
    data = load_data()
    if section_name and section_name not in data["journal_sections"]:
        data["journal_sections"].append(section_name)
        data["journal_entries"][section_name] = []
        save_data(data)
        st.success(f"Section Created: {section_name}")
    elif section_name in data["journal_sections"]:
        st.warning("Section already exists.")

def delete_journal_section(section_name: str):
    data = load_data()
    if section_name in data["journal_sections"]:
        data["journal_sections"].remove(section_name)
        del data["journal_entries"][section_name]
        save_data(data)
        st.success(f"Section Deleted: {section_name}")

def add_journal_entry(section_name: str, entry_text: str):
    data = load_data()
    if section_name in data["journal_sections"]:
        new_entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.datetime.now().isoformat(),
            "text": entry_text
        }
        data["journal_entries"][section_name].append(new_entry)
        save_data(data)
        st.success("Entry saved!")

def delete_journal_entry(section_name: str, entry_id: str):
    data = load_data()
    if section_name in data["journal_entries"]:
        data["journal_entries"][section_name] = [
            e for e in data["journal_entries"][section_name] if e["id"] != entry_id
        ]
        save_data(data)

def export_data_to_csv(data: Dict[str, Any]):
    """Export tracking data to CSV format"""
    output = []
    
    # Habits Summary
    output.append("HABITS SUMMARY\n")
    output.append("Habit Name,XP Value,Active,Goal\n")
    for habit_name, details in data["habits"].items():
        active = "Yes" if details.get("active", True) else "No"
        goal = details.get("goal", "General")
        output.append(f"{habit_name},{details['xp']},{active},{goal}\n")
    
    output.append("\n")
    
    # Completions
    output.append("DAILY COMPLETIONS\n")
    output.append("Date,Habits Completed\n")
    for date_str in sorted(data["completions"].keys()):
        habits_list = "; ".join(data["completions"][date_str])
        output.append(f"{date_str},{habits_list}\n")
    
    output.append("\n")
    
    # Tasks
    output.append("TASKS\n")
    output.append("Title,Goal,Priority,XP,Status,Due Date,Created Date\n")
    for task in data["tasks"]:
        created = task.get("created_at", "")[:10]
        due = task.get("due_date", "")
        title = task['title'].replace(",", ";")  # Escape commas in title
        output.append(f"{title},{task.get('goal', 'General')},{task.get('priority', 'Low')},{task.get('xp', 0)},{task['status']},{due},{created}\n")
    
    return "".join(output)


def export_tasks_to_ics(data: Dict[str, Any]) -> str:
    """Export missions to ICS calendar format."""
    tasks = data.get("tasks", [])
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//HeroicEveryday//EN",
    ]
    for task in tasks:
        title = task.get("title", "Mission")
        uid = task.get("id", "")
        due = task.get("due_date")
        if not due:
            continue
        # ICS date (all-day)
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"SUMMARY:{title}",
            f"DESCRIPTION:{task.get('description', '')}",
            f"DTSTART;VALUE=DATE:{due.replace('-', '')}",
            f"DTEND;VALUE=DATE:{due.replace('-', '')}",
            f"CATEGORIES:{task.get('goal', 'General')}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)

# --- Helper: List existing users ---
def get_existing_users() -> List[str]:
    """Scan for existing user data files and return list of user IDs."""
    import glob
    users = []
    # Check for default user
    if os.path.exists("xp_data.json"):
        users.append("default")
    # Check for named users
    for file in glob.glob("xp_data_*.json"):
        # Extract user ID from filename: xp_data_alice.json -> alice
        user_id = file.replace("xp_data_", "").replace(".json", "")
        users.append(user_id)
    return sorted(users)


def ensure_firebase_initialized() -> bool:
    """Initialize firebase-admin using the [firebase] secrets block."""
    if not firebase_admin or not fb_credentials:
        st.warning("firebase-admin not installed; Google sign-in disabled.")
        return False
    if firebase_admin._apps:
        return True
    if hasattr(st, "secrets") and st.secrets.get("firebase"):
        try:
            cred = fb_credentials.Certificate(dict(st.secrets["firebase"]))
            firebase_admin.initialize_app(cred)
            return True
        except Exception as e:
            st.error(f"Failed to init Firebase for Google login: {e}")
            return False
    st.error("Add Firebase service account under [firebase] in secrets for Google login.")
    return False


def render_google_login_button(primary: bool = False):
    """Render a Google Sign-In button and return the ID token (if provided by JS)."""
    cfg = st.secrets.get("firebase_auth") if hasattr(st, "secrets") else None
    if not cfg:
        return None

    cfg_json = json.dumps(dict(cfg))
    btn_style = "padding:10px 12px;border-radius:6px;background:#fff;color:#000;border:1px solid #ddd;cursor:pointer;width:100%;"
    if primary:
        btn_style = "padding:14px 16px;border-radius:8px;background:#ffffff;color:#111;border:2px solid #222;font-weight:700;font-size:16px;cursor:pointer;width:100%;"
    html = f"""
    <div id="google-signin"></div>
    <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js"></script>
    <script>
      // Streamlit component messaging helpers (both legacy and current)
      function sendHeight(h) {{
        window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: h}}, "*");
      }}
      function sendValue(v) {{
        // legacy
        window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:setComponentValue", value: v}}, "*");
        // current
        window.parent.postMessage({{type: "streamlit:componentValue", value: v}}, "*");
      }}
      window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1}}, "*");
      sendHeight(document.documentElement.clientHeight);

      const cfg = {cfg_json};
      if (!firebase.apps.length) {{
        firebase.initializeApp(cfg);
      }}
      const auth = firebase.auth();
      const btn = document.getElementById("google-signin");
      if (btn) {{
        btn.innerHTML = '<button style="{btn_style}">Sign in with Google</button>';
        btn.onclick = () => {{
          auth.signInWithPopup(new firebase.auth.GoogleAuthProvider())
            .then(result => result.user.getIdToken())
            .then(token => {{
              sendValue(token);
            }})
            .catch(err => {{
              console.log("Google sign-in error", err);
            }});
        }};
      }}
    </script>
    """
    return components.html(html, height=90, scrolling=False)


def render_google_redirect_button():
    """Render a top-level Google Sign-In button that uses redirect (works outside iframe)."""
    cfg = st.secrets.get("firebase_auth") if hasattr(st, "secrets") else None
    if not cfg:
        return
    cfg_json = json.dumps(dict(cfg))
    html = """
    <div id="google-redirect-wrap" style="margin-top:12px;">
      <button id="google-redirect-btn" style="padding:14px 16px;border-radius:8px;background:#fff;color:#111;border:2px solid #222;font-weight:700;font-size:16px;cursor:pointer;width:100%;">Sign in with Google</button>
    </div>
    <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js"></script>
    <script>
      (function() {{
        if (window.__firebase_redirect_init) return;
        window.__firebase_redirect_init = true;
        const cfg = {cfg_json};
        if (!firebase.apps.length) firebase.initializeApp(cfg);
        const auth = firebase.auth();
        // On load, handle redirect result and bounce token back via query param
        auth.getRedirectResult().then(res => {{
          if (res && res.user) {{
            return res.user.getIdToken().then(tok => {{
              const url = new URL(window.location.href);
              url.searchParams.set('google_token', tok);
              window.location.href = url.toString();
            }});
          }}
        }}).catch(err => console.log('Redirect result error', err));
        const btn = document.getElementById("google-redirect-btn");
        if (btn) {{
          btn.onclick = () => {{
            // Use popup instead of redirect to avoid third-party cookie issues on Streamlit Cloud
            auth.signInWithPopup(new firebase.auth.GoogleAuthProvider())
              .then(res => {{
                if (res && res.user) {{
                  res.user.getIdToken().then(tok => {{
                    const url = new URL(window.location.href);
                    url.searchParams.set('google_token', tok);
                    window.location.href = url.toString();
                  }});
                }}
              }})
              .catch(err => console.log('Popup sign-in error', err));
          }};
        }}
      }})();
    </script>
    """.format(cfg_json=cfg_json)
    st.markdown(html, unsafe_allow_html=True)

# --- Main App Layout ---

def main():
    # --- Google token via redirect ---
    params = st.query_params
    # Fix for Streamlit 1.30+ where st.query_params is a dict-like object returning strings, not lists
    redirect_token = params.get('google_token')

    # Legacy fallback if it returns a list (old versions)
    if isinstance(redirect_token, list) and redirect_token:
        redirect_token = redirect_token[0]

    if redirect_token:
        st.session_state['google_id_token'] = redirect_token
        # Clean URL
        try:
            # Modern Streamlit (1.30+)
            if 'google_token' in st.query_params:
                del st.query_params['google_token']
        except Exception:
            try:
                # Legacy fallback
                clean_params = {k: v for k, v in params.items() if k != 'google_token'}
                st.experimental_set_query_params(**clean_params)
            except Exception:
                pass

    # --- Email verification via link ---
    verify_user = params.get('verify_user')
    if isinstance(verify_user, list) and verify_user:
        verify_user = verify_user[0]
    verify_token = params.get('verify_token')
    if isinstance(verify_token, list) and verify_token:
        verify_token = verify_token[0]
    if verify_user and verify_token:
        storage = get_storage()
        if storage.verify_email_token(verify_user, verify_token):
            st.success(f"Email verified for {verify_user}. You can now log in.")
        else:
            st.error("Verification link is invalid or expired.")

    # --- Password reset via link handler ---
    reset_user = params.get('reset_user')
    if isinstance(reset_user, list) and reset_user:
        reset_user = reset_user[0]

    reset_token = params.get('token')
    if isinstance(reset_token, list) and reset_token:
        reset_token = reset_token[0]
    if reset_user and reset_token:
        st.title('Password Reset')
        st.write(f"Resetting password for: **{reset_user}**")
        new_pw = st.text_input('New password', type='password')
        confirm_pw = st.text_input('Confirm new password', type='password')
        if st.button('Set New Password'):
            storage = get_storage()
            ok = storage.verify_and_consume_reset_token(reset_user, reset_token)
            if not ok:
                st.error('Invalid or expired reset token.')
            else:
                if not new_pw:
                    st.error('Password cannot be empty.')
                elif new_pw != confirm_pw:
                    st.error('Passwords do not match.')
                else:
                    storage.set_user_password(reset_user, new_pw)
                    st.success('Password updated. You can now login.')
                    st.stop()

    # --- Login / User Selection ---
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = "default"
    
    # Initialize authentication state
    if 'authenticated_user' not in st.session_state:
        st.session_state['authenticated_user'] = None
    if 'admin_authenticated' not in st.session_state:
        st.session_state['admin_authenticated'] = False
    if 'google_id_token' not in st.session_state:
        st.session_state['google_id_token'] = None
    
        # === OPTION 3: INITIALIZE BACKGROUND SCHEDULER ===
        if 'scheduler_initialized' not in st.session_state:
            if scheduler_service:
                try:
                    scheduler_service.init_scheduler()
                    st.session_state['scheduler_initialized'] = True
                except Exception as e:
                    # Scheduler failed to initialize - app continues without background jobs
                    pass
            st.session_state['scheduler_initialized'] = True

    # Handle Google token if present
    if st.session_state.get('google_id_token') and not st.session_state.get('authenticated_user'):
        if ensure_firebase_initialized() and fb_auth:
            try:
                decoded = fb_auth.verify_id_token(st.session_state['google_id_token'])
                user_id = decoded.get('uid') or decoded.get('email')
                email = decoded.get('email')
                if user_id:
                    storage = get_storage()
                    if not storage.user_exists(user_id):
                        storage.load_data(user_id)
                    if email:
                        storage.set_user_email(user_id, email)
                    st.session_state['user_id'] = user_id
                    st.session_state['authenticated_user'] = user_id
                    st.session_state['google_id_token'] = None
                    st.success(f"Signed in with Google as {email or user_id}")
                    st.rerun()
                else:
                    st.error("Google sign-in token missing email/uid.")
                    st.session_state['google_id_token'] = None
            except Exception:
                st.error("Google sign-in failed. Please try again.")
                st.session_state['google_id_token'] = None

    with st.sidebar:
        st.title("User Profile")

        authed_user = st.session_state.get('authenticated_user')
        storage = get_storage()

        if not authed_user:
            st.subheader("Login / Create")
            sb_username = st.text_input("Username", key="sb_username")
            sb_password = st.text_input("Password", type="password", key="sb_password")
            sb_email = st.text_input("Email (optional)", key="sb_email", placeholder="you@example.com")
            col_sb_a, col_sb_b = st.columns(2)
            with col_sb_a:
                if st.button("Login"):
                    if not sb_username.strip():
                        st.error("Enter a username.")
                    elif not storage.user_exists(sb_username):
                        st.error("User not found.")
                    elif not storage.verify_user_password(sb_username, sb_password):
                        st.error("Invalid password.")
                    elif not storage.is_email_verified(sb_username):
                        user_email = storage.get_user_email(sb_username)
                        if user_email and send_verification_email(sb_username, user_email, storage):
                            st.warning(f"Email not verified. Verification email re-sent to {user_email}.")
                        else:
                            st.error("Email not verified and resend failed.")
                    else:
                        st.session_state['user_id'] = sb_username
                        st.session_state['authenticated_user'] = sb_username
                        st.success(f"Logged in as {sb_username}")
                        st.rerun()
            with col_sb_b:
                if st.button("Create"):
                    if not sb_username.strip():
                        st.error("Enter a username to create.")
                    elif storage.user_exists(sb_username):
                        st.error("User already exists.")
                    elif not sb_email.strip():
                        st.error("Email is required for verification.")
                    elif email_in_use(storage, sb_email.strip()):
                        st.error("That email is already in use.")
                    else:
                        ok, msg = validate_email(sb_email.strip())
                        if not ok:
                            st.error(f"Invalid email: {msg}")
                        else:
                            storage.load_data(sb_username)
                            if sb_password:
                                storage.set_user_password(sb_username, sb_password)
                            storage.set_user_email(sb_username, sb_email.strip())
                            storage.set_email_verified(sb_username, False)
                            if send_verification_email(sb_username, sb_email.strip(), storage):
                                st.success(f"Account created. Verification email sent to {sb_email.strip()}.")
                                st.info("Please verify your email to log in.")
                            else:
                                st.error("Failed to send verification email. Please try again.")
            if st.button("Forgot Password"):
                if not sb_username.strip():
                    st.error("Enter your username first.")
                else:
                    user_email = storage.get_user_email(sb_username)
                    if not user_email:
                        st.error("No email on file for that user.")
                    else:
                        token = storage.create_password_reset_token(sb_username)
                        if token:
                            app_url = None
                            if hasattr(st, 'secrets') and st.secrets.get('app'):
                                app_url = st.secrets.get('app', {}).get('url')
                            app_url = app_url or os.environ.get('APP_URL') or 'http://localhost:8501'
                            params_reset = {'reset_user': sb_username, 'token': token}
                            reset_link = app_url + '/?' + urllib.parse.urlencode(params_reset)
                            subject = 'XP Tracker Password Reset'
                            body = f'Hello {sb_username},\\n\\nReset your password:\\n{reset_link}\\n\\nLink expires in one hour.'
                            if send_email(user_email, subject, body):
                                st.success(f"Reset link sent to {user_email}")
                            else:
                                st.error("Failed to send reset email.")
            st.caption("Leaderboard remains public; personal tabs require login.")
        else:
            st.success(f"Signed in as {authed_user}")

        st.divider()
        if authed_user:
            if st.button("Logout"):
                st.session_state['authenticated_user'] = None
                st.session_state['admin_authenticated'] = False
                st.session_state['google_id_token'] = None
                st.success("Logged out successfully.")
                st.rerun()
        st.divider()

    # Primary sign-in screen when not authenticated
    is_authed = st.session_state.get('authenticated_user') or st.session_state.get('admin_authenticated')
    if not is_authed:
        st.title("Welcome to Heroic Everyday")
        st.subheader("Sign in to start tracking")

        username = st.text_input("Username", key="main_username")
        password = st.text_input("Password", type="password", key="main_password")
        email = st.text_input("Email (required for verification)", key="main_email", placeholder="you@example.com")
        col_a, col_b = st.columns(2)
        if col_a.button("Login", key="main_login_btn"):
            if not username.strip():
                st.error("Enter a username.")
            elif not storage.user_exists(username):
                st.error("User not found.")
            elif not storage.verify_user_password(username, password):
                st.error("Invalid password.")
            elif not storage.is_email_verified(username):
                user_email = storage.get_user_email(username)
                if user_email and send_verification_email(username, user_email, storage):
                    st.warning(f"Email not verified. Verification email re-sent to {user_email}.")
                else:
                    st.error("Email not verified and resend failed.")
            else:
                st.session_state['user_id'] = username
                st.session_state['authenticated_user'] = username
                st.success(f"Logged in as {username}")
                st.rerun()
        if col_b.button("Create Account", key="main_create_btn"):
            if not username.strip():
                st.error("Enter a username to create.")
            elif storage.user_exists(username):
                st.error("User already exists.")
            elif not email.strip():
                st.error("Email is required for verification.")
            elif email_in_use(storage, email.strip()):
                st.error("That email is already in use.")
            else:
                ok, msg = validate_email(email.strip())
                if not ok:
                    st.error(f"Invalid email: {msg}")
                else:
                    storage.load_data(username)
                    if password:
                        storage.set_user_password(username, password)
                    storage.set_user_email(username, email.strip())
                    storage.set_email_verified(username, False)
                    if send_verification_email(username, email.strip(), storage):
                        st.success(f"Account created. Verification email sent to {email.strip()}.")
                        st.info("Please verify your email to log in.")
                    else:
                        st.error("Failed to send verification email. Please try again.")

        if not (hasattr(st, "secrets") and st.secrets.get("firebase_auth")):
            st.warning("Add [firebase_auth] (apiKey, authDomain, appId, projectId) to secrets.toml to enable Google sign-in.")

        st.stop()

    data = load_data()
    active_goals = get_active_goals(data) or ["General"]
    archived_goals = data.get("archived_goals", [])
    today_str = get_date_str(0)
    
    global_xp, habit_stats, earned_badges = calculate_stats(data)
    current_level, xp_in_level, level_progress = calculate_level(global_xp)
    current_rank = get_rank(current_level)
    # Milestone prompt
    rewards = data.get("rewards", {})
    milestones = sorted(rewards.get("milestones", []))
    last_prompted = rewards.get("last_prompted", 0)
    next_hits = [m for m in milestones if m > last_prompted and m <= global_xp]
    if next_hits:
        hit = max(next_hits)
        st.success(f"🎁 Milestone hit: {hit} XP. Claim your reward (you set it).")
        data.setdefault("rewards", {})["last_prompted"] = hit
        save_data(data)

    if current_level >= 10 and "veteran" not in earned_badges:
        earned_badges.append("veteran")

    # --- Celebration Logic ---
    if 'previous_level' not in st.session_state:
        st.session_state['previous_level'] = current_level
    
    if current_level > st.session_state['previous_level']:
        st.balloons()
        st.toast(f"🎉 LEVEL UP! You are now Level {current_level}!", icon="🆙")
        st.session_state['previous_level'] = current_level
        time.sleep(1)

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Guild Management")
        
        tab_goals, tab_add, tab_manage = st.tabs(["Goals", "Add Quest", "Archive"])
        
        with tab_goals:
            with st.form("add_goal_form", clear_on_submit=True):
                st.subheader("Define a New Goal")
                new_goal = st.text_input("Goal Name (e.g., Get Fit)")
                if st.form_submit_button("Add Goal"):
                    add_goal(new_goal)
                    st.rerun()
            st.divider()
            st.write("Current Goals:")
            if active_goals:
                for g in active_goals:
                    st.caption(f"• {g}")
            else:
                st.caption("None (add one above)")

            retire_choice = st.selectbox(
                "Retire a goal",
                options=active_goals,
                index=0 if active_goals else None,
                key="retire_goal_select",
                disabled=not active_goals,
            )
            if st.button("Retire selected goal", disabled=not active_goals):
                retire_goal(retire_choice)
                st.rerun()

            if archived_goals:
                st.divider()
                st.write("Retired Goals:")
                restore_choice = st.selectbox("Restore a goal", options=archived_goals, key="restore_goal_select")
                if st.button("Restore selected goal"):
                    restore_goal(restore_choice)
                    st.rerun()

        with tab_add:
            with st.form("add_habit_form", clear_on_submit=True):
                st.subheader("New Habit Quest")
                new_habit_name = st.text_input("Habit Name")
                new_habit_desc = st.text_area("Description (optional)", height=68)
                new_habit_xp = st.number_input("XP Reward", min_value=1, value=10)
                habit_goal = st.selectbox("Link to Goal", options=active_goals)
                
                submitted_add = st.form_submit_button("Create Habit")
                if submitted_add:
                    add_new_habit(new_habit_name, new_habit_xp, habit_goal, new_habit_desc)
                    st.rerun()

        with tab_manage:
            st.subheader("Habit Status")
            active_habits = [h for h, d in data["habits"].items() if d.get("active", True)]
            archived_habits = [h for h, d in data["habits"].items() if not d.get("active", True)]
            
            if active_habits:
                to_archive = st.selectbox("Archive Quest", options=active_habits)
                if st.button("Archive"):
                    archive_habit(to_archive)
                    st.rerun()
            
            st.divider()

            if archived_habits:
                to_restore = st.selectbox("Restore Quest", options=archived_habits)
                if st.button("Restore"):
                    restore_habit(to_restore)
                    st.rerun()

    # --- Header Stats ---
    st.title("🛡️ Hero Log")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Level {current_level}: {current_rank}")
        st.progress(level_progress)
        st.caption(f"XP: {xp_in_level} / {XP_PER_LEVEL} to next level (Total: {global_xp})")
    with col2:
        active_count = len([h for h, d in data["habits"].items() if d.get("active", True)])
        pending_tasks = len([t for t in data["tasks"] if t["status"] == "Todo"])
        st.metric("Active Upgrades", f"{active_count} Habits / {pending_tasks} Missions")

    st.markdown("---")

    # === ONBOARDING CHECK ===
    # If user just created account and hasn't completed onboarding, show modal
    is_authenticated = st.session_state.get('authenticated_user') is not None
    if is_authenticated:
        user_id = get_user_id()
        
        # Show onboarding if flagged or if not completed
        if st.session_state.get('show_onboarding', False) or not has_completed_onboarding(user_id):
            st.info("🚀 Let's personalize your XP Tracker experience with coaching!")
            if show_onboarding_modal():
                # User submitted onboarding
                responses = st.session_state.get('onboarding_responses', {})
                if save_onboarding_profile(user_id, responses):
                    st.session_state['show_onboarding'] = False
                    st.session_state['guided_setup'] = True
                    st.success("✅ Coaching profile created! Your personalized drip emails and daily digests are ready.")
                    st.rerun()
            st.stop()  # Stop rendering other content until onboarding complete

    # --- Guided setup for first goal/habit ---
    render_guided_setup()

    # --- Tabs ---
    tab_habits, tab_tasks, tab_journal, tab_reports, tab_ai_coach, tab_profile, tab_leaderboard, tab_admin, tab_about = st.tabs(["📅 Hero Log", "📜 Mission Deck", "📔 Journal", "📊 Signals", "🧠 AI Coach", "🏅 Profile & Badges", "🏆 Leaderboard", "⚙️ Admin", "ℹ️ About & FAQ"])

    # === TAB 1: DAILY HABITS ===
    with tab_habits:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to view your daily quests.")
            st.stop()
        
        st.header(f"Hero Log: {today_str}")
        # Filters
        filter_cols = st.columns(2)
        with filter_cols[0]:
            filter_context = st.selectbox("Filter by context", options=["All", "Work", "Personal", "Health", "Creativity", "Admin"], index=0)
        with filter_cols[1]:
            filter_cadence = st.selectbox("Filter by cadence", options=["All", "Daily", "3x/Week", "Weekly", "One-Off"], index=0)
        
        active_habits_dict = {k: v for k, v in data["habits"].items() if v.get("active", True)}

        if not active_habits_dict:
            st.info("No active quests! Check the sidebar to add new ones.")
        else:
            # Apply filters
            filtered = []
            for name, details in active_habits_dict.items():
                if filter_context != "All" and details.get("context") != filter_context:
                    continue
                if filter_cadence != "All" and details.get("cadence", "Daily") != filter_cadence:
                    continue
                filtered.append((name, details))
            sorted_habits = sorted(filtered, key=lambda x: x[1].get("goal", "General"))
            
            for habit_name, details in sorted_habits:
                is_completed = habit_name in data["completions"].get(today_str, [])
                current_streak = habit_stats[habit_name]['streak']
                total_habit_xp = habit_stats[habit_name]['total_xp']
                habit_level = habit_stats[habit_name]['level']
                habit_goal = details.get("goal", "General")
                
                c1, c2, c3, c4 = st.columns([0.5, 3, 1, 1])
                
                with c1:
                    checked = st.checkbox(
                        "Complete", 
                        value=is_completed, 
                        key=f"check_{habit_name}",
                        label_visibility="collapsed"
                    )
                    if checked != is_completed:
                        toggle_habit(habit_name, today_str)
                        st.rerun()

                with c2:
                    level_badge = f"<span style='background-color:#FFD700; color:#000; padding:1px 4px; border-radius:3px; font-weight:bold; font-size:0.75em'>Lvl {habit_level}</span>" if habit_level > 1 else ""
                    st.markdown(
                        f"**{habit_name}** {level_badge} <br> <span style='background-color:#f0f2f6; color:#31333f; padding:2px 6px; border-radius:4px; font-size:0.75em'>{habit_goal}</span> <span style='color:gray; font-size:0.8em'>({details['xp']} XP)</span>",
                        unsafe_allow_html=True
                    )
                    if details.get("description"):
                        with st.expander("ℹ️ Details"):
                            st.caption(details.get("description"))
                    
                with c3:
                    if current_streak > 0:
                        st.markdown(f"🔥 **{current_streak}**")
                    else:
                        st.markdown("❄️ 0")
                        
                with c4:
                    st.markdown(f"⭐ {total_habit_xp}")
                    
                st.divider()
        
        # Summary Table for Habits
        with st.expander("📊 Full Habit Log"):
            summary_data = []
            for h in data["habits"]:
                is_active = data["habits"][h].get("active", True)
                status = "🟢 Active" if is_active else "🗄️ Archived"
                
                summary_data.append({
                    "Habit": h,
                    "Goal": data["habits"][h].get("goal", "General"),
                    "Context": data["habits"][h].get("context", "General"),
                    "Cadence": data["habits"][h].get("cadence", "Daily"),
                    "Level": habit_stats[h]['level'],
                    "Status": status,
                    "Base XP": data["habits"][h]["xp"],
                    "Current Streak": habit_stats[h]['streak'],
                    "Total XP": habit_stats[h]['total_xp'],
                    "Total Completions": habit_stats[h]['completions']
                })
            st.dataframe(summary_data, use_container_width=True)

    # === TAB 5: PROFILE & BADGES ===
    with tab_profile:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to view your profile.")
            st.stop()
        
        st.header("🏅 Your Achievements")

        st.subheader("🏆 Badges")

        if not earned_badges:
            st.info("No badges yet. Keep training!")
        else:
            cols = st.columns(4)
            for i, badge_id in enumerate(earned_badges):
                if badge_id in BADGES_DEF:
                    badge = BADGES_DEF[badge_id]
                    with cols[i % 4]:
                        st.markdown(
                            f"""
                            <div style="text-align:center; border: 1px solid #ddd; padding: 10px; border-radius: 10px; background-color: #fafafa;">
                                <div style="font-size: 3em;">{badge['icon']}</div>
                                <div style="font-weight: bold; margin-top: 5px;">{badge['name']}</div>
                                <div style="font-size: 0.8em; color: gray;">{badge['desc']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        st.divider()
        if st.button("🔮 Generate more goal/habit ideas"):
            st.session_state["guided_setup"] = True
            st.session_state["habit_recs"] = []
            st.success("Reopening guided habit creator above.")
            st.rerun()

        st.subheader("📊 Career Stats")
        st.write(f"**Current Level:** {current_level}")
        st.write(f"**Total XP:** {global_xp}")
        st.write(f"**Rank:** {current_rank}")

        # Rewards / milestones
        st.divider()
        st.subheader("🎁 Rewards & Milestones")
        rewards = data.get("rewards", {})
        milestones = rewards.get("milestones", [500, 1000])
        last_prompted = rewards.get("last_prompted", 0)
        milestone_input = st.text_input("Milestones (comma-separated XP)", value=",".join(str(m) for m in milestones))
        if st.button("Save Milestones"):
            try:
                parsed = [int(x.strip()) for x in milestone_input.split(",") if x.strip().isdigit()]
                if parsed:
                    data["rewards"]["milestones"] = parsed
                    save_data(data)
                    st.success("Milestones updated.")
                else:
                    st.warning("Enter at least one number.")
            except Exception:
                st.error("Invalid milestones; please enter numbers separated by commas.")
        st.caption(f"Last milestone prompt at {last_prompted} XP.")

        st.divider()
        st.subheader("📧 Email Settings")
        
        current_user = st.session_state.get('user_id', 'unknown')
        storage = get_storage()
        current_email = storage.get_user_email(current_user)
        
        if current_email:
            st.write(f"**Current Email:** {current_email}")
        else:
            st.info("No email set yet")
        
        with st.expander("✏️ Add or Update Email"):
            new_email = st.text_input("New Email", placeholder="your-email@example.com", key="profile_email_input")
            if st.button("Save Email", key="save_email_btn"):
                if not new_email or new_email.strip() == "":
                    st.error("Email cannot be empty")
                else:
                    is_valid, msg = validate_email(new_email)
                    if not is_valid:
                        st.error(f"Invalid email: {msg}")
                    else:
                        storage.set_user_email(current_user, new_email.strip())
                        st.success(f"Email saved: {new_email}")
                        st.rerun()

        # === NOTIFICATION OPT-IN TOGGLE ===
        st.divider()
        st.subheader("🔔 Notification Preferences")
        
        notifications_enabled = storage.get_notifications_enabled(current_user)
        new_notifications_enabled = st.checkbox(
            "Enable email notifications",
            value=notifications_enabled,
            help="When enabled, you'll receive emails for habit completions, streaks, weekly summaries, and coaching tips. When disabled, no notification emails will be sent to you."
        )
        
        if new_notifications_enabled != notifications_enabled:
            storage.set_notifications_enabled(current_user, new_notifications_enabled)
            if new_notifications_enabled:
                st.success("✅ Notifications enabled!")
            else:
                st.info("🔇 Notifications disabled. You can re-enable them anytime.")
            st.rerun()

        # === PRIVACY TOGGLE ===
        st.divider()
        st.subheader("🛡️ Privacy")
        private_mode = data.get("preferences", {}).get("private_mode", False)
        new_private_mode = st.checkbox(
            "Private mode (hide me from Leaderboard and sharing cues)",
            value=private_mode,
            help="When on, you won't appear on the leaderboard or in shared stats. Data still tracked for you."
        )
        if new_private_mode != private_mode:
            data["preferences"]["private_mode"] = new_private_mode
            save_data(data)
            st.success("Privacy preference updated.")
            st.rerun()

        # === COACHING PROFILE EDITOR ===
        st.divider()
        show_profile_editor(current_user)        # --- Notification History ---
        st.divider()
        st.subheader("� Notification History")
        try:
            history = notifications.get_user_notification_history(current_user, limit=50)
        except Exception as e:
            st.error(f"Failed to load notification history: {e}")
            history = []

        if not history:
            st.info("No notifications have been sent to this account yet.")
        else:
            # Offer export
            if st.button("Export Notification History (JSON)"):
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(history, indent=2),
                    file_name=f"notifications_{current_user}.json",
                    mime="application/json"
                )

            for i, rec in enumerate(history):
                rec_ts = rec.get("timestamp")
                rec_type = rec.get("type")
                rec_data = rec.get("data", {})
                subj = rec_data.get("subject", "(no subject)")
                with st.expander(f"{rec_ts} — {rec_type} — {subj}", expanded=False):
                    st.write("**Subject:**", subj)
                    st.write("**Type:**", rec_type)
                    st.write("**Timestamp:**", rec_ts)
                    st.write("**Recipient:**", rec_data.get("recipient", "(unknown)"))
                    body = rec_data.get("body")
                    if body:
                        st.markdown("**Body:**")
                        st.code(body)
                    else:
                        st.info("No body stored for this notification.")

                    # Resend button
                    if st.button("Resend Notification", key=f"resend_{i}"):
                        if not storage.get_user_email(current_user):
                            st.error("No email on file to resend to.")
                        else:
                            ok = notifications.send_notification_email(current_user, subj, body or "", rec_type)
                            if ok:
                                st.success("Notification resent successfully.")
                            else:
                                st.error("Failed to resend notification.")

        st.divider()

    # === TAB 2: TASKS ===
    with tab_tasks:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to view your missions.")
            st.stop()
        
        st.header("Mission Log")
        
        # Add Task Expander
        with st.expander("➕ Add New Mission"):
            with st.form("new_task_form", clear_on_submit=True):
                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    task_title = st.text_input("Mission Title")
                    task_goal = st.selectbox("Goal", options=active_goals, key="task_goal")
                    task_context = st.selectbox("Context", options=["Work", "Personal", "Health", "Creativity", "Admin"], key="task_context")
                    task_cadence = st.selectbox("Cadence", options=["One-Off", "Daily", "3x/Week", "Weekly"], key="task_cadence")
                    task_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
                with t_col2:
                    task_xp = st.number_input("XP Reward", value=50, step=10)
                    task_due = st.date_input("Due Date", value=None)
                    
                task_desc = st.text_area("Description (Optional)")
                
                if st.form_submit_button("Add Mission"):
                    if task_title:
                        add_task(task_title, task_desc, task_xp, task_goal, task_priority, task_due, task_context, task_cadence)
                        st.success("Mission Added!")
                        st.rerun()
                    else:
                        st.error("Title is required.")

        st.divider()

        with st.expander("✨ Get AI mission ideas"):
            with st.form("ai_mission_form", clear_on_submit=False):
                ai_goal = st.selectbox("Goal to support", options=active_goals, key="ai_mission_goal")
                ai_context = st.text_area("What do you need to accomplish?", placeholder="e.g., Prepare deck for client presentation")
                ai_effort = st.slider("Time available (minutes)", min_value=15, max_value=180, value=45, step=15)
                ai_urgency = st.selectbox("Target timeframe", ["Today", "This week", "This month"], index=1)
                ai_submit = st.form_submit_button("Generate mission ideas")

            if ai_submit:
                profile = get_coaching_profile(get_user_id())
                ai_recs = generate_task_recommendations_gemini(profile, ai_goal, ai_context, ai_effort, ai_urgency)
                if not ai_recs:
                    ai_recs = generate_task_recommendations(ai_goal, ai_context, ai_effort, ai_urgency)
                    st.session_state["task_recs_notice"] = "Gemini unavailable; using deterministic mission ideas."
                else:
                    st.session_state["task_recs_notice"] = ""
                st.session_state["task_recs"] = ai_recs
                st.session_state["task_recs_params"] = {"goal": ai_goal, "urgency": ai_urgency}
                st.success("Mission ideas ready below.")

            notice = st.session_state.get("task_recs_notice")
            if notice:
                st.info(notice)

        task_recs = st.session_state.get("task_recs", [])
        if task_recs:
            st.markdown("### AI mission ideas")
            updated_tasks = []
            for i, rec in enumerate(task_recs):
                st.markdown(f"**Idea {i+1}:** {rec.get('title', 'Untitled')} ({rec.get('priority', 'Medium')})")
                st.caption(rec.get("description", ""))
                title = st.text_input("Mission title", value=rec.get("title", ""), key=f"task_rec_title_{i}")
                desc = st.text_area("Description", value=rec.get("description", ""), height=80, key=f"task_rec_desc_{i}")
                goal_choices = list(dict.fromkeys(active_goals + [rec.get("goal", "General")]))
                goal_choice = st.selectbox("Goal", options=goal_choices, index=goal_choices.index(rec.get("goal", "General")), key=f"task_rec_goal_{i}")
                ctx_choice = st.selectbox("Context", options=["Work", "Personal", "Health", "Creativity", "Admin"], index=0, key=f"task_rec_ctx_{i}")
                cad_choice = st.selectbox("Cadence", options=["One-Off", "Daily", "3x/Week", "Weekly"], index=0, key=f"task_rec_cad_{i}")
                priority_default = rec.get("priority", "Medium") if rec.get("priority", "Medium") in ["High", "Medium", "Low"] else "Medium"
                priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(priority_default), key=f"task_rec_priority_{i}")
                xp_val = st.number_input("XP Reward", min_value=5, max_value=200, value=int(rec.get("xp", 50)), step=5, key=f"task_rec_xp_{i}")
                due_default = None
                if rec.get("due_in_days") is not None:
                    try:
                        due_default = datetime.date.today() + datetime.timedelta(days=int(rec.get("due_in_days")))
                    except Exception:
                        due_default = None
                due_date = st.date_input("Due date (optional)", value=due_default, key=f"task_rec_due_{i}")
                pick = st.checkbox("Add this mission", value=True, key=f"task_rec_pick_{i}")
                st.divider()
                updated_tasks.append({
                    "title": title,
                    "description": desc,
                    "goal": goal_choice,
                    "context": ctx_choice,
                    "cadence": cad_choice,
                    "priority": priority,
                    "xp": int(xp_val),
                    "due_date": due_date,
                    "pick": pick,
                })

            if st.button("Add selected missions", key="add_ai_tasks"):
                added_count = 0
                for rec in updated_tasks:
                    if rec["pick"] and rec["title"].strip():
                        add_task(rec["title"].strip(), rec["description"], rec["xp"], rec["goal"], rec["priority"], rec["due_date"], rec.get("context", "General"), rec.get("cadence", "One-Off"))
                        added_count += 1
                if added_count:
                    st.session_state["task_recs"] = []
                    st.success(f"Added {added_count} mission(s).")
                    st.rerun()
                else:
                    st.info("Select at least one mission to add.")

        st.divider()

        # CSV Importer
        with st.expander("📥 Import missions from CSV"):
            st.markdown(
                "Upload or paste a CSV with headers: `due_date,title,description,goal,priority,xp,context,cadence` "
                "(dates accepted as YYYY-MM-DD or MM/DD/YYYY). Missing fields fall back to sensible defaults."
            )
            st.download_button(
                label="Download CSV template",
                data=get_mission_csv_template(),
                file_name="missions_template.csv",
                mime="text/csv",
                key="download_mission_template",
            )

            uploaded_csv = st.file_uploader("Upload CSV file", type=["csv"], key="task_csv_upload")
            pasted_csv = st.text_area("Or paste CSV content", height=120, key="task_csv_paste")

            if st.button("Parse CSV", key="parse_task_csv"):
                csv_text = ""
                if uploaded_csv:
                    try:
                        csv_text = uploaded_csv.getvalue().decode("utf-8")
                    except Exception:
                        st.error("Could not read the uploaded file. Please ensure it is UTF-8 encoded.")
                elif pasted_csv.strip():
                    csv_text = pasted_csv
                else:
                    st.error("Provide a CSV file or paste CSV content first.")

                if csv_text:
                    missions, errors = parse_csv_missions(csv_text)
                    st.session_state["task_import_preview"] = {"missions": missions, "errors": errors}
                    if errors:
                        st.warning("Parsed with issues. See errors below.")
                    else:
                        st.success(f"Parsed {len(missions)} mission(s). Review and import below.")

            preview_state = st.session_state.get("task_import_preview", {"missions": [], "errors": []})
            preview_missions = preview_state.get("missions", [])
            preview_errors = preview_state.get("errors", [])

            if preview_errors:
                st.error("Errors:\n- " + "\n- ".join(preview_errors))

            if preview_missions:
                preview_rows = []
                for m in preview_missions:
                    preview_rows.append({
                        "title": m["title"],
                        "due_date": m["due_date"].isoformat() if m["due_date"] else "",
                        "goal": m["goal"],
                        "priority": m["priority"],
                        "xp": m["xp"],
                        "context": m["context"],
                        "cadence": m["cadence"],
                    })
                st.dataframe(pd.DataFrame(preview_rows))

                if not preview_errors:
                    if st.button(f"Import {len(preview_missions)} missions", key="import_task_csv"):
                        for m in preview_missions:
                            add_task(m["title"], m["description"], m["xp"], m["goal"], m["priority"], m["due_date"], m.get("context", "General"), m.get("cadence", "One-Off"))
                        st.session_state.pop("task_import_preview", None)
                        st.success(f"Imported {len(preview_missions)} mission(s).")
                        st.rerun()

        # Filters and Tabs for Tasks
        filter_tasks_context = st.selectbox("Filter missions by context", options=["All", "Work", "Personal", "Health", "Creativity", "Admin"], index=0)
        filter_tasks_cadence = st.selectbox("Filter missions by cadence", options=["All", "One-Off", "Daily", "3x/Week", "Weekly"], index=0)
        task_view_mode = st.radio(
            "Organize missions",
            ["Group by due date & goal", "Flat priority list"],
            index=0,
            horizontal=True,
        )

        t_tab_active, t_tab_done = st.tabs(["Active Missions", "Completed Missions"])
        
        # ACTIVE TASKS
        with t_tab_active:
            active_tasks = [t for t in data["tasks"] if t["status"] == "Todo"]
            if filter_tasks_context != "All":
                active_tasks = [t for t in active_tasks if t.get("context", "General") == filter_tasks_context]
            if filter_tasks_cadence != "All":
                active_tasks = [t for t in active_tasks if t.get("cadence", "One-Off") == filter_tasks_cadence]
            if not active_tasks:
                st.info("No active missions. Good job... or get to work!")
            else:
                if task_view_mode == "Group by due date & goal":
                    bucket_order = ["Overdue", "Today", "Tomorrow", "This Week", "Next Week", "Later", "No Date"]
                    grouped = bucket_tasks_by_due_and_goal(active_tasks)
                    for bucket in bucket_order:
                        goal_map = grouped.get(bucket, {})
                        if not goal_map:
                            continue
                        bucket_count = sum(len(tasks) for tasks in goal_map.values())
                        st.subheader(f"{bucket} ({bucket_count})")
                        for goal in sorted(goal_map.keys()):
                            st.markdown(f"**{goal}**")
                            for task in goal_map[goal]:
                                render_task_row(task, key_suffix=f"_{bucket}_{goal}", goals=active_goals)
                        st.divider()
                else:
                    active_tasks.sort(key=task_sort_key)
                    for task in active_tasks:
                        render_task_row(task, goals=active_goals)

        # COMPLETED TASKS
        with t_tab_done:
            done_tasks = [t for t in data["tasks"] if t["status"] == "Done"]
            if not done_tasks:
                st.caption("No completed missions yet.")
            else:
                # Show most recent first
                done_tasks.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
                
                for task in done_tasks:
                    with st.container():
                        st.markdown(f"~~{task['title']}~~ (+{task['xp']} XP)")
                        st.caption(f"Completed: {task.get('completed_at', '')[:10]}")
                        if st.button("Undo", key=f"undo_{task['id']}"):
                            toggle_task_status(task['id'], "Todo")
                            st.rerun()
                        st.divider()

    # === TAB 3: JOURNAL ===
    with tab_journal:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to view your journal.")
            st.stop()
        
        st.header("📔 Journal & Practice")
        
        # Create New Section
        with st.expander("➕ Create New Section"):
            with st.form("new_section_form", clear_on_submit=True):
                section_name = st.text_input("Section Name (e.g., Daily Reflections, Practice Questions)")
                if st.form_submit_button("Create Section"):
                    if section_name:
                        add_journal_section(section_name)
                        st.rerun()
                    else:
                        st.error("Section name is required.")
        
        st.divider()

        # AI Writing Prompt
        if st.button("✨ Get AI Writing Prompt"):
            with st.spinner("Consulting your AI coach..."):
                profile = get_coaching_profile(get_user_id())
                stats = {"level": current_level}
                context = {"profile": profile, "stats": stats}
                prompt = ai_chat.generate_journal_prompt(context)
                st.session_state["journal_prompt"] = prompt

        if "journal_prompt" in st.session_state:
            st.info(f"**Coach says:** {st.session_state['journal_prompt']}")
            if st.button("Dismiss Prompt"):
                del st.session_state["journal_prompt"]
                st.rerun()

        # Display Sections
        if not data["journal_sections"]:
            st.info("No sections yet. Create one to get started!")
        else:
            for section in data["journal_sections"]:
                with st.expander(f"📝 {section}", expanded=False):
                    # Add Entry Form
                    with st.form(f"entry_form_{section}", clear_on_submit=True):
                        entry_text = st.text_area(
                            "Write your entry...",
                            placeholder="Share your thoughts, practice questions, or reflections...",
                            height=150,
                            key=f"textarea_{section}"
                        )
                        if st.form_submit_button("Save Entry", key=f"save_{section}"):
                            if entry_text:
                                add_journal_entry(section, entry_text)
                                st.rerun()
                            else:
                                st.error("Entry cannot be empty.")
                    
                    st.divider()
                    
                    # Display Entries
                    entries = data["journal_entries"].get(section, [])
                    if entries:
                        st.caption(f"📚 {len(entries)} entry(ies)")
                        for entry in reversed(entries):  # Most recent first
                            entry_date = entry["date"][:10]  # Extract date part
                            entry_time = entry["date"][11:16]  # Extract time part
                            
                            with st.container():
                                col_delete, col_date = st.columns([0.1, 0.9])
                                with col_delete:
                                    if st.button("🗑️", key=f"del_entry_{entry['id']}", help="Delete entry"):
                                        delete_journal_entry(section, entry["id"])
                                        st.rerun()
                                with col_date:
                                    st.caption(f"📅 {entry_date} at {entry_time}")
                                
                                st.write(entry["text"])
                                st.divider()
                    else:
                        st.caption("No entries yet. Start writing!")
                    
                    # Delete Section Button
                    if st.button(f"🗑️ Delete '{section}' Section", key=f"del_section_{section}"):
                        delete_journal_section(section)
                        st.rerun()

    # === TAB 4: REPORTS ===
    with tab_reports:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to view your reports.")
            st.stop()
        
        st.header("📊 Weekly Reports & Analytics")
        
        # Week Navigation
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav1:
            if st.button("⬅️ Previous Week"):
                st.session_state.week_offset = st.session_state.get("week_offset", 0) - 1
                st.rerun()
        
        with col_nav2:
            week_offset = st.session_state.get("week_offset", 0)
            if st.button("📅 This Week"):
                st.session_state.week_offset = 0
                st.rerun()
            start, end = get_week_range(week_offset)
            st.markdown(f"<h3 style='text-align: center;'>Week of {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}</h3>", unsafe_allow_html=True)
        
        with col_nav3:
            if st.button("Next Week ➡️"):
                st.session_state.week_offset = st.session_state.get("week_offset", 0) + 1
                st.rerun()
        
        st.divider()
        
        # Get weekly stats
        week_offset = st.session_state.get("week_offset", 0)
        daily_stats, total_weekly_xp, week_start, week_end = get_weekly_stats(data, week_offset)
        
        # Summary Cards
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("📈 Weekly XP", total_weekly_xp)
        with summary_col2:
            days_active = len([d for d in daily_stats.values() if d["xp"] > 0])
            st.metric("🔥 Active Days", f"{days_active}/7")
        with summary_col3:
            avg_daily_xp = total_weekly_xp // 7 if total_weekly_xp > 0 else 0
            st.metric("⭐ Avg Daily XP", avg_daily_xp)
        
        st.divider()
        
        # Charts
        chart_col1, chart_col2 = st.columns(2)
        
        # Daily XP Chart
        with chart_col1:
            chart_data = []
            for date_str in sorted(daily_stats.keys()):
                day_info = daily_stats[date_str]
                chart_data.append({
                    "Day": day_info["day_name"] + " " + date_str.split("-")[2],
                    "XP": day_info["xp"]
                })
            
            df_daily = pd.DataFrame(chart_data)
            fig_daily = px.bar(
                df_daily,
                x="Day",
                y="XP",
                title="Daily XP Earned",
                color="XP",
                color_continuous_scale="Viridis"
            )
            fig_daily.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        # Habits Completion Rate
        with chart_col2:
            active_habits = [h for h, d in data["habits"].items() if d.get("active", True)]
            if active_habits:
                habit_completions = {h: 0 for h in active_habits}
                for date_str in daily_stats.keys():
                    completed_habits = []
                    # Get habits completed on this date
                    if date_str in data["completions"]:
                        for h in data["completions"][date_str]:
                            if h in habit_completions:
                                habit_completions[h] += 1
                
                habit_chart_data = [{"Habit": h, "Completions": habit_completions[h]} for h in active_habits]
                df_habits = pd.DataFrame(habit_chart_data)
                fig_habits = px.bar(
                    df_habits,
                    x="Habit",
                    y="Completions",
                    title="Habit Completion Rate (This Week)",
                    color="Completions",
                    color_continuous_scale="RdYlGn"
                )
                fig_habits.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_habits, use_container_width=True)
        
        st.divider()
        
        # Detailed Daily Breakdown
        st.subheader("📅 Daily Breakdown")
        breakdown_data = []
        for date_str in sorted(daily_stats.keys()):
            day_info = daily_stats[date_str]
            breakdown_data.append({
                "Date": date_str,
                "Day": day_info["day_name"],
                "XP": day_info["xp"],
                "Habits Completed": day_info["habits_completed"]
            })
        
        df_breakdown = pd.DataFrame(breakdown_data)
        st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Data Export
        st.subheader("📥 Export Data")
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            csv_data = export_data_to_csv(data)
            st.download_button(
                label="📊 Download as CSV",
                data=csv_data,
                file_name=f"xp_tracker_export_{datetime.date.today().isoformat()}.csv",
                mime="text/csv"
            )
        
        with export_col2:
            json_data = json.dumps(data, indent=2)
            st.download_button(
                label="📋 Download as JSON",
                data=json_data,
                file_name=f"xp_tracker_export_{datetime.date.today().isoformat()}.json",
                mime="application/json"
            )

    # === TAB 5: AI COACH ===
    with tab_ai_coach:
        # Auth check
        is_authenticated = st.session_state.get('authenticated_user') is not None
        is_admin = st.session_state.get('admin_authenticated', False)
        if not is_authenticated and not is_admin:
            st.warning("⚠️ Please log in to talk to your AI Coach.")
            st.stop()

        st.header("🧠 AI Coach")

        col_chat, col_insights = st.columns([2, 1])

        with col_chat:
            st.subheader("💬 Chat with Coach")
            st.info("Ask for advice, motivation, or help breaking down a goal.")

            # Chat history
            if "chat_history" not in st.session_state:
                st.session_state["chat_history"] = []

            for msg in st.session_state["chat_history"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if prompt := st.chat_input("How can I help you level up today?"):
                # Add user message
                st.session_state["chat_history"].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                # Get AI response
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        # Build context
                        profile = get_coaching_profile(get_user_id())
                        context = {
                            "profile": profile,
                            "stats": {"level": current_level, "total_xp": global_xp},
                            "habits": data.get("habits", {})
                        }
                        response = ai_chat.get_ai_response(prompt, context)
                        st.write(response)
                        st.session_state["chat_history"].append({"role": "assistant", "content": response})

        with col_insights:
            st.subheader("📈 Pattern Analysis")
            user_id = get_user_id()
            insights = coaching_engine.analyze_user_patterns(user_id)

            if not insights.get("ready"):
                st.info(f"Analysis pending: {insights.get('reason')}")
                st.caption("We need about 14 days of data to spot meaningful patterns.")
            else:
                st.success("Analysis Ready!")
                st.markdown("### Top Recommendations")
                for rec in insights.get("recommendations", [])[:3]:
                    st.write(f"• {rec}")

                st.markdown("### Strengths")
                for s in insights.get("strengths", []):
                    st.write(f"✅ {s}")

                st.markdown("### Challenges")
                for c in insights.get("challenges", []):
                    st.write(f"⚠️ {c}")

    # === TAB 6: LEADERBOARD ===
    with tab_leaderboard:
        st.header("🏆 Leaderboard")
        
        # Time period filter
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("📊 All-Time", key="lb_all_time"):
                st.session_state['lb_period'] = "all_time"
        with col2:
            if st.button("📅 This Week", key="lb_this_week"):
                st.session_state['lb_period'] = "week"
        with col3:
            if st.button("📆 This Month", key="lb_this_month"):
                st.session_state['lb_period'] = "month"
        with col4:
            if st.button("📋 This Year", key="lb_this_year"):
                st.session_state['lb_period'] = "year"
        with col5:
            period_select = st.selectbox("Or select:", ["all_time", "week", "month", "year"], key="lb_period_select")
            st.session_state['lb_period'] = period_select
        
        period = st.session_state.get('lb_period', 'all_time')
        
        # Get leaderboard
        leaderboard = get_leaderboard_stats(period)
        
        if not leaderboard:
            st.info("No users or XP data yet.")
        else:
            # Display leaderboard
            st.subheader(f"Top Players ({period.replace('_', ' ').title()})")
            
            # Create leaderboard display
            medals = ["🥇", "🥈", "🥉"]
            
            for rank, (user_id, xp) in enumerate(leaderboard, 1):
                medal = medals[rank - 1] if rank <= 3 else f"{rank}️⃣"
                
                # Get user level
                user_storage = get_storage()
                user_data = user_storage.load_data(user_id)
                _, _, level_progress = calculate_level(xp)
                user_level, _, _ = calculate_level(xp)
                
                # Display rank
                with st.container():
                    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                    with col1:
                        st.markdown(f"# {medal}")
                    with col2:
                        st.write(f"**{user_id}**")
                    with col3:
                        st.metric("Level", user_level)
                    with col4:
                        st.metric("XP", f"{xp:,}")
                    
                    # Progress bar
                    st.progress(level_progress)
            
            # Detailed table
            st.divider()
            st.subheader("Detailed Standings")
            
            table_data = []
            for rank, (user_id, xp) in enumerate(leaderboard, 1):
                user_storage = get_storage()
                user_data = user_storage.load_data(user_id)
                user_level, _, _ = calculate_level(xp)
                user_email = user_storage.get_user_email(user_id)
                
                table_data.append({
                    "Rank": rank,
                    "Player": user_id,
                    "Email": user_email or "-",
                    "Level": user_level,
                    "Total XP": f"{xp:,}"
                })
            
            df_leaderboard = pd.DataFrame(table_data)
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
            
            # Stats summary
            st.divider()
            st.subheader("📊 Leaderboard Stats")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Players", len(leaderboard))
            with col2:
                top_xp = leaderboard[0][1] if leaderboard else 0
                st.metric("Top Player XP", f"{top_xp:,}")
            with col3:
                avg_xp = sum([xp for _, xp in leaderboard]) // len(leaderboard) if leaderboard else 0
                st.metric("Average XP", f"{avg_xp:,}")

    # === TAB 9: ABOUT & FAQ ===
    with tab_about:
        st.header("\u2139\ufe0f About Heroic Everyday")
        st.markdown("""
Welcome to Heroic Everyday — a clean, business-friendly tracker with playful edge. Think **professional playfulness**: punchy, smart, zero B.S., and rooting for you.

**What this is:** A daily operating system to log your wins (Hero Log), ship missions (Mission Deck), and keep momentum.
**How it talks:** Encouraging with a wink, dark-humor edge (Thug Kitchen meets Heathers), never mean, always moving you forward.
""")

        st.subheader("FAQ")
        st.markdown("""
**How do I log progress?**  
- Check off Upgrades in the **Hero Log**. Streaks fuel your Momentum Meter.
- Add one-off work to the **Mission Deck**; hit Done for XP.
- Filter by context/cadence to focus (Work/Personal/Health/Creativity/Admin + Daily/3x/Weekly/One-Off).

**How are emails/AI responses written?**  
- Playfully direct, smart humor, warm underneath. No fluff, no lecture.

**How many habits should I start with?**  
- Start with one. Win for 10–14 days, then add another. Bricks → fortress.

**How long does it take to build a habit?**  
- 21–66 days; ~28 feels right. Reps beat time: 5 days done > 15 days planned.

**What if I miss a day?**  
- Nothing explodes. Just don’t miss two. Streak resets; progress doesn’t. Return = resilience.

**How do I pick the right habit?**  
- Small on your worst day, meaningful enough to care, crystal-clear “done.”  
- “Read 5 minutes after coffee” beats “read more.”

**How much time should it take?**  
- Start under 2 minutes. Low friction = high consistency. Expand later.

**How do I stack habits so they stick?**  
- Anchor a new Upgrade to an existing routine: “after coffee, 5 pushups” or “after shutdown, write tomorrow’s plan.” Keep it tiny.

**What’s the deal with XP and streaks?**  
- XP = dopamine so your brain roots for future-you. Streaks create momentum. Break one? Restart. Heroes return.

**How do I use missions to support goals?**  
- Translate goals into specific missions (proposals, outreach, prep). Tie each mission to a goal; finish it for XP and real movement.
- Use context tags to batch similar work; export missions to calendar (.ics) if you want them on your schedule.

**What if I’m not motivated?**  
- Motivation is optional. Systems win. Do the tiny version anyway; XP keeps you invested.

**Best time of day?**  
- Whenever you’re consistent. Morning = clarity, afternoon = production, evening = grounding. Fit real life, not an ideal calendar.

**Make it stick long-term?**  
- Cue → Action → Reward (XP/streak). Repeat your identity: “I honor my commitments.” Identity beats willpower.

**Can I change or remove habits later?**  
- Absolutely. Evolve the system. You’re not in a monastery; you’re running a life OS.

**How do I deal with resistance/chaos?**  
- Name it. Shrink it. Do 10%. Chaos? Do the smallest version, protect the streak if you can, and let XP be your compass back.

**How do I avoid burnout?**  
- Start small. Stay playful. Celebrate progress. If it feels heavy, shrink it and add a wink.

**What about privacy and rewards?**  
- Private mode hides you from Leaderboard and shared stats.  
- Set XP milestones as personal rewards; you’ll get a prompt when you hit them.

**Where's my data stored?**  
- Firebase (per your credentials).""")

        st.subheader("Usage Guide")
        st.markdown("""
1) **Set Your Direction**: Add 1-3 goals; keep it lean.  
2) **Build Upgrades**: Small daily habits tied to those goals.  
3) **Ship Missions**: Create focused tasks; mark them Done for XP.  
4) **Check the Signals**: Momentum comes from streaks; guard them.  
5) **Ask the Coach**: Use AI Coach for quick tactics; expect witty, actionable replies.

Taglines to remember:
- "Consistency beats intensity—ask literally any superhero."
- "Every tap here is future-you whispering: nice move."
- "You did the thing. Most don't."
- "Micro-wins are still wins. Ask compounding interest."
- "Welcome back, Hero. Ready for today's nonsense?"
- "Look at you—stacking XP like it's your part-time job."
""")

    # === TAB 7: ADMIN ===
    with tab_admin:
        st.header("⚙️ Admin Management")
        
        # Admin authentication
        admin_passphrase = os.environ.get("ADMIN_PASSPHRASE") or (st.secrets.get("admin_passphrase") if hasattr(st, 'secrets') else None)
        
        if not admin_passphrase:
            st.warning("⚠️ Admin panel disabled: ADMIN_PASSPHRASE not set. Set environment variable or st.secrets['admin_passphrase'].")
            st.stop()
        
        # Authenticate admin
        if 'admin_authenticated' not in st.session_state:
            st.session_state['admin_authenticated'] = False
        
        if not st.session_state['admin_authenticated']:
            st.subheader("🔐 Admin Authentication")
            admin_pass = st.text_input("Admin Passphrase", type="password")
            if st.button("Unlock Admin Panel"):
                if admin_pass == admin_passphrase:
                    st.session_state['admin_authenticated'] = True
                    st.success("Admin panel unlocked!")
                    st.rerun()
                else:
                    st.error("Incorrect passphrase.")
            st.stop()
        
        # Admin panel unlocked
        st.success("✅ Admin panel unlocked")
        
        if st.button("🔒 Lock Admin Panel"):
            st.session_state['admin_authenticated'] = False
            st.rerun()
        
        st.divider()
        
        # User management
        st.subheader("👥 User Management")
        all_users = get_existing_users()
        st.write(f"Total users: **{len(all_users)}**")
        
        # Display users
        if all_users:
            st.write("Existing users:")
            for user in all_users:
                user_email = storage.get_user_email(user)
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.write(f"👤 {user}")
                with col2:
                    st.caption(f"📧 {user_email or '(no email)'}")
                with col3:
                    if st.button("✏️ Edit", key=f"edit_{user}"):
                        st.session_state['admin_edit_user'] = user
                with col4:
                        if st.session_state.get(f"deleting_{user}", False):
                            col4a, col4b = st.columns([1, 1])
                            with col4a:
                                if st.button("✅ Confirm", key=f"confirm_delete_{user}"):
                                    import glob
                                    files_to_delete = glob.glob(f"xp_data_{user}.json")
                                    if user == "default":
                                        files_to_delete += glob.glob("xp_data.json")
                                    for file in files_to_delete:
                                        try:
                                            os.remove(file)
                                            st.success(f"✅ Deleted user: {user}")
                                            st.session_state[f"deleting_{user}"] = False
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Failed to delete: {e}")
                            with col4b:
                                if st.button("❌ Cancel", key=f"cancel_delete_{user}"):
                                    st.session_state[f"deleting_{user}"] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete", key=f"delete_{user}"):
                                st.session_state[f"deleting_{user}"] = True
                                st.rerun()
                st.divider()
        else:
            st.info("No users found.")
        
        # --- Notification Triggers (Admin) ---
        st.divider()
        st.subheader("📣 Notification Triggers (Admin)")
        if all_users:
            target_user = st.selectbox("Select user to notify", options=all_users, key="admin_notify_user")
            notif_type = st.selectbox("Notification type", options=["streak_milestone", "missed_day", "level_up", "badge_earned", "weekly_summary", "personalized_coaching"], key="admin_notif_type")

            # Dynamic fields
            if notif_type == "streak_milestone":
                habit_name = st.text_input("Habit Name", value="Daily Practice")
                streak_val = st.number_input("Streak (days)", min_value=1, value=5)
                xp_val = st.number_input("XP Earned", min_value=0, value=50)
                if st.button("Send Streak Milestone"):
                    ok = notifications.notify_streak_milestone(target_user, habit_name, int(streak_val), int(xp_val))
                    if ok:
                        st.success("Streak milestone notification sent")
                    else:
                        st.error("Failed to send streak notification (check email or history)")

            elif notif_type == "missed_day":
                habit_name = st.text_input("Habit Name", value="Daily Practice")
                days_missed = st.number_input("Days Missed", min_value=1, value=1)
                last_streak = st.number_input("Previous Streak", min_value=0, value=7)
                if st.button("Send Missed Day Encouragement"):
                    ok = notifications.notify_missed_day(target_user, habit_name, int(days_missed), int(last_streak))
                    if ok:
                        st.success("Missed day encouragement sent")
                    else:
                        st.error("Failed to send missed-day notification")

            elif notif_type == "level_up":
                new_level = st.number_input("New Level", min_value=1, value=2)
                total_xp = st.number_input("Total XP", min_value=0, value=500)
                if st.button("Send Level Up Notification"):
                    ok = notifications.notify_level_up(target_user, int(new_level), int(total_xp))
                    if ok:
                        st.success("Level up notification sent")
                    else:
                        st.error("Failed to send level-up notification")

            elif notif_type == "badge_earned":
                badge_name = st.text_input("Badge Name", value="Consistency")
                badge_desc = st.text_area("Badge Description", value="Completed 30 days in a row")
                if st.button("Send Badge Notification"):
                    ok = notifications.notify_badge_earned(target_user, badge_name, badge_desc)
                    if ok:
                        st.success("Badge notification sent")
                    else:
                        st.error("Failed to send badge notification")

            elif notif_type == "weekly_summary":
                completed_count = st.number_input("Completed This Week", min_value=0, value=5)
                total_habits = st.number_input("Total Habits", min_value=1, value=7)
                xp_earned = st.number_input("XP Earned This Week", min_value=0, value=350)
                top_habit = st.text_input("Top Habit (optional)", value="")
                if st.button("Send Weekly Summary"):
                    ok = notifications.notify_weekly_summary(target_user, int(completed_count), int(total_habits), int(xp_earned), top_habit or None)
                    if ok:
                        st.success("Weekly summary sent")
                    else:
                        st.error("Failed to send weekly summary")

            elif notif_type == "personalized_coaching":
                st.write("Provide a small JSON context object for the user (e.g., levels, streaks, top habits)")
                context_raw = st.text_area("Context JSON", value='{"level": 3, "total_xp": 650, "top_habit": "Meditation", "streaks": {"Meditation": 5}}')
                if st.button("Send Personalized Coaching"):
                    try:
                        ctx = json.loads(context_raw)
                    except Exception as e:
                        st.error(f"Invalid JSON: {e}")
                        ctx = None
                    if ctx is not None:
                        ok = notifications.notify_personalized_coaching(target_user, ctx)
                        if ok:
                            st.success("Personalized coaching sent")
                        else:
                            st.error("Failed to send personalized coaching")

        # === SCHEDULER STATUS UI ===
        st.divider()
        st.subheader("⏰ Background Scheduler Status")
        
        if scheduler_service:
            try:
                status = scheduler_service.get_scheduler_status()
                scheduler_running = "🟢 Running" in status.get("status", "")
                st.write(f"**Scheduler Status:** {status.get('status', 'Unknown')}")
                
                jobs = status.get("jobs", [])
                if jobs:
                    st.write(f"**Scheduled Jobs:** {len(jobs)}")
                    for job in jobs:
                        job_id = job.get("id", "unknown")
                        next_run = job.get("next_run", "unknown")
                        st.write(f"  • **{job_id}** — Next run: {next_run}")
                else:
                    st.info("No jobs scheduled")
                
                # Manual job trigger buttons (for testing)
                st.write("**Manual Job Triggers (for testing):**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔥 Run Streak Checks Now"):
                        try:
                            scheduler_service.job_streak_checks()
                            st.success("Streak checks executed")
                        except Exception as e:
                            st.error(f"Error running streak checks: {e}")
                
                with col2:
                    if st.button("📊 Run Weekly Summary Now"):
                        try:
                            scheduler_service.job_weekly_summary()
                            st.success("Weekly summary executed")
                        except Exception as e:
                            st.error(f"Error running weekly summary: {e}")
                
                with col3:
                    if st.button("⏰ Run Daily Reminder Now"):
                        try:
                            scheduler_service.job_daily_reminder()
                            st.success("Daily reminder executed")
                        except Exception as e:
                            st.error(f"Error running daily reminder: {e}")
                            
            except Exception as e:
                st.error(f"Failed to get scheduler status: {e}")
        else:
            st.warning("⚠️ Scheduler service not available (APScheduler not installed or failed to initialize)")

        st.divider()
        if 'admin_edit_user' in st.session_state:
            edit_user = st.session_state['admin_edit_user']
            st.subheader(f"Edit: {edit_user}")
            
            # Get current email
            current_email = storage.get_user_email(edit_user)
            new_email = st.text_input("Email", value=current_email or "")
            
            # Password reset
            reset_pw_opt = st.radio("Password action", ["None", "Set new password", "Clear password"])
            if reset_pw_opt == "Set new password":
                new_pw = st.text_input("New password", type="password", key="admin_new_pw")
                confirm_pw = st.text_input("Confirm password", type="password", key="admin_confirm_pw")
                if st.button(f"Set Password for {edit_user}"):
                    if new_pw != confirm_pw:
                        st.error("Passwords do not match.")
                    elif not new_pw:
                        st.error("Password cannot be empty.")
                    else:
                        storage.set_user_password(edit_user, new_pw)
                        st.success(f"Password set for {edit_user}")
            elif reset_pw_opt == "Clear password":
                if st.button(f"Clear Password for {edit_user}"):
                    storage.set_user_password(edit_user, "")
                    st.success(f"Password cleared for {edit_user} (passwordless login)")
            
            # Save email
            if st.button(f"Save Email for {edit_user}"):
                storage.set_user_email(edit_user, new_email or None)
                st.success(f"Email saved for {edit_user}")
            
            if st.button("Done editing"):
                del st.session_state['admin_edit_user']
                st.rerun()

if __name__ == "__main__":
    main()
