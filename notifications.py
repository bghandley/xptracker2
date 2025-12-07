"""
Notifications System
Manages notification triggers, history, and sending.
Responses in style of Thug Kitchen Cookbook meets the movie Heathers, but warm underneath.

"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from storage import get_storage
from email_utils import send_email
from coaching_emails import (
    generate_streak_celebration,
    generate_missed_day_encouragement,
    generate_weekly_summary,
    generate_personalized_coaching
)


NOTIFICATIONS_FILE = "notifications_history.json"


def load_notifications_history() -> Dict[str, List[Dict]]:
    """Load notification history."""
    if not os.path.exists(NOTIFICATIONS_FILE):
        return {}
    
    try:
        with open(NOTIFICATIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading notifications: {e}")
        return {}


def save_notifications_history(history: Dict[str, List[Dict]]) -> None:
    """Save notification history."""
    try:
        with open(NOTIFICATIONS_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving notifications: {e}")


def add_notification_record(user_id: str, notification_type: str, data: Dict) -> None:
    """Record that a notification was sent."""
    history = load_notifications_history()
    
    if user_id not in history:
        history[user_id] = []
    
    record = {
        "type": notification_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    }
    
    history[user_id].append(record)
    save_notifications_history(history)


def has_recent_notification(user_id: str, notification_type: str, hours_back: int = 24) -> bool:
    """Check if a notification of this type was recently sent."""
    history = load_notifications_history()
    
    if user_id not in history:
        return False
    
    cutoff = datetime.fromisoformat(
        (datetime.now() - __import__('datetime').timedelta(hours=hours_back)).isoformat()
    )
    
    for record in history[user_id]:
        if record["type"] == notification_type:
            try:
                record_time = datetime.fromisoformat(record["timestamp"])
                if record_time > cutoff:
                    return True
            except:
                pass
    
    return False


def send_notification_email(user_id: str, subject: str, body: str, notification_type: str = None) -> bool:
    """
    Send a notification email.
    
    Args:
        user_id: Username
        subject: Email subject
        body: Email body
        notification_type: Type of notification (for history tracking)
    
    Returns:
        True if sent successfully
    """
    storage = get_storage()
    
    # Check if notifications are enabled for this user
    if not storage.get_notifications_enabled(user_id):
        print(f"Notifications disabled for {user_id}, skipping")
        return False
    
    email = storage.get_user_email(user_id)
    
    if not email:
        print(f"No email on file for {user_id}, skipping notification")
        return False
    
    success = send_email(email, subject, body)
    
    if success and notification_type:
        # Store subject, recipient and full body so history retains the coaching text
        add_notification_record(user_id, notification_type, {
            "subject": subject,
            "recipient": email,
            "body": body
        })
    
    return success


def notify_streak_milestone(user_id: str, habit_name: str, streak: int, xp_earned: int) -> bool:
    """
    Send streak milestone notification.
    
    Args:
        user_id: Username
        habit_name: Name of habit
        streak: Current streak
        xp_earned: XP earned
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, f"streak_{streak}", hours_back=72):
        return False
    
    # Generate coaching message
    coaching = generate_streak_celebration(user_id, habit_name, streak, xp_earned)
    
    subject = f"🔥 {streak}-Day Streak! Way to go on '{habit_name}'!"
    body = f"""
Hello {user_id},

You just hit a {streak}-day streak on '{habit_name}'! Amazing work! 🎉

{coaching if coaching else f"You earned {xp_earned} XP from this completion. Keep crushing it!"}

Keep up the incredible momentum!

Best regards,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, f"streak_{streak}")


def notify_missed_day(user_id: str, habit_name: str, days_missed: int, last_streak: int) -> bool:
    """
    Send encouragement after missed day.
    
    Args:
        user_id: Username
        habit_name: Name of habit
        days_missed: Days missed
        last_streak: Previous streak
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, f"missed_{habit_name}", hours_back=48):
        return False
    
    # Generate coaching message
    coaching = generate_missed_day_encouragement(user_id, habit_name, days_missed, last_streak)
    
    subject = f"You missed a day on '{habit_name}' - let's get back on track! 💪"
    body = f"""
Hello {user_id},

It looks like you missed {days_missed} day(s) on '{habit_name}'. That's totally okay!

You had an amazing {last_streak}-day streak going. Let's get you back on track today!

{coaching if coaching else "Every day is a new opportunity to build the habit. You've got this!"}

Get back in there,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, f"missed_{habit_name}")


def notify_level_up(user_id: str, new_level: int, total_xp: int) -> bool:
    """
    Send level up notification.
    
    Args:
        user_id: Username
        new_level: New level achieved
        total_xp: Total XP
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, f"level_{new_level}", hours_back=72):
        return False
    
    subject = f"⚡ Level {new_level} Unlocked! Congratulations!"
    body = f"""
Hello {user_id},

Congratulations! You just reached Level {new_level}! 🚀

Total XP: {total_xp}

You're on an incredible journey of self-improvement. Keep pushing forward!

Best regards,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, f"level_{new_level}")


def notify_badge_earned(user_id: str, badge_name: str, badge_description: str) -> bool:
    """
    Send badge earned notification.
    
    Args:
        user_id: Username
        badge_name: Name of badge
        badge_description: Description
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, f"badge_{badge_name}", hours_back=72):
        return False
    
    subject = f"🏆 Badge Unlocked: {badge_name}!"
    body = f"""
Hello {user_id},

You've earned the '{badge_name}' badge! 🏆

{badge_description}

This is a testament to your dedication. Keep up the amazing work!

Best regards,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, f"badge_{badge_name}")


def notify_weekly_summary(user_id: str, completed_count: int, total_habits: int, xp_earned: int, top_habit: str = None) -> bool:
    """
    Send weekly summary notification.
    
    Args:
        user_id: Username
        completed_count: Number completed this week
        total_habits: Total habits
        xp_earned: XP earned this week
        top_habit: Best performing habit
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, "weekly_summary", hours_back=168):  # 7 days
        return False
    
    # Generate coaching message
    coaching = generate_weekly_summary(user_id, completed_count, total_habits, xp_earned, top_habit)
    
    subject = f"📊 Your Weekly Summary: {completed_count} Habits Completed!"
    body = f"""
Hello {user_id},

Here's your weekly coaching summary:

Habits Completed: {completed_count}/{total_habits}
XP Earned This Week: {xp_earned}
{f"Top Habit: '{top_habit}'" if top_habit else ""}

{coaching if coaching else "Great work this week! Keep the momentum going into next week!"}

See you next week,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, "weekly_summary")


def notify_personalized_coaching(user_id: str, context: Dict[str, Any]) -> bool:
    """
    Send fully personalized coaching email.
    
    Args:
        user_id: Username
        context: User's current data/context
    
    Returns:
        True if sent
    """
    # Check if already sent recently
    if has_recent_notification(user_id, "personalized_coaching", hours_back=72):
        return False
    
    # Generate coaching message
    coaching = generate_personalized_coaching(user_id, context)
    
    if not coaching:
        return False
    
    subject = f"🎯 Personalized Coaching for {user_id}"
    body = f"""
Hello {user_id},

Here's some personalized coaching just for you:

{coaching}

You've got this!

Best regards,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, "personalized_coaching")


def notify_habit_completed(user_id: str, habit_name: str, xp_earned: int, current_streak: int) -> bool:
    """
    Send celebration email when habit is marked complete.
    
    Args:
        user_id: Username
        habit_name: Name of completed habit
        xp_earned: XP earned from this completion
        current_streak: Current streak after completion
    
    Returns:
        True if sent successfully
    """
    # Don't send more than once per day per habit per user
    if has_recent_notification(user_id, f"habit_complete_{habit_name}", hours_back=24):
        return False
    
    # Generate coaching message
    coaching = generate_personalized_coaching(user_id, {
        "context": "habit_completion",
        "habit": habit_name,
        "streak": current_streak,
        "xp": xp_earned
    })
    
    subject = f"✅ Quest Complete: {habit_name}! +{xp_earned} XP"
    body = f"""
Hello {user_id},

Amazing! You just completed '{habit_name}' today! 🎯
You earned +{xp_earned} XP and your streak is now {current_streak} day(s) long! 🔥

{coaching if coaching else f"Great job staying consistent! Keep up this momentum and watch your skills grow!"}

You're on your way to becoming legendary!

Best regards,
Your XP Tracker Coach
"""
    
    return send_notification_email(user_id, subject, body, f"habit_complete_{habit_name}")


def get_user_notification_history(user_id: str, limit: int = 10) -> List[Dict]:
    """Get recent notification history for a user."""
    history = load_notifications_history()
    
    if user_id not in history:
        return []
    
    return sorted(
        history[user_id],
        key=lambda x: x["timestamp"],
        reverse=True
    )[:limit]
