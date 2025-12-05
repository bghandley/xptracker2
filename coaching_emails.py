"""
OpenAI Coaching Email Generator
Generates personalized, encouraging coaching emails using GPT.
"""

import os
import json
import streamlit as st
from typing import Optional
from datetime import datetime

# Try to import OpenAI
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def get_openai_client() -> Optional[OpenAI]:
    """Get OpenAI client if API key is available."""
    if not HAS_OPENAI:
        return None
    
    api_key = None
    
    # Try st.secrets first
    if hasattr(st, 'secrets') and st.secrets.get('openai_api_key'):
        api_key = st.secrets.get('openai_api_key')
    
    # Fall back to environment variable
    if not api_key:
        api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        return None
    
    return OpenAI(api_key=api_key)


def generate_streak_celebration(user_id: str, habit_name: str, streak: int, xp_earned: int) -> Optional[str]:
    """
    Generate encouraging coaching message for streak milestone.
    
    Args:
        user_id: Username
        habit_name: Name of habit (e.g., "Morning Meditation")
        streak: Current streak count
        xp_earned: XP earned from this completion
    
    Returns:
        Coaching message string, or None if OpenAI not available
    """
    client = get_openai_client()
    if not client:
        return None
    
    prompt = f"""
You are a motivational personal coaching AI. Write a SHORT, ENTHUSIASTIC email celebrating a user's habit streak.

User: {user_id}
Habit: {habit_name}
Streak: {streak} days
XP Earned: {xp_earned}

Write a 2-3 sentence message that:
1. Celebrates their {streak}-day streak
2. References the specific habit
3. Encourages them to keep going
4. Is warm, personal, and genuine (not corporate)

Keep it under 100 words. No salutations or signatures needed.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def generate_missed_day_encouragement(user_id: str, habit_name: str, days_missed: int, last_streak: int) -> Optional[str]:
    """
    Generate encouraging message when user misses a day.
    
    Args:
        user_id: Username
        habit_name: Name of habit
        days_missed: How many days missed
        last_streak: Previous streak before missing
    
    Returns:
        Coaching message string, or None if OpenAI not available
    """
    client = get_openai_client()
    if not client:
        return None
    
    prompt = f"""
You are a compassionate personal coaching AI. Write a SHORT, SUPPORTIVE email to encourage someone who missed their habit.

User: {user_id}
Habit: {habit_name}
Days Missed: {days_missed}
Previous Streak: {last_streak} days

Write a 2-3 sentence message that:
1. Acknowledges they missed {days_missed} day(s) (normalize it, don't shame them)
2. Reminds them of their {last_streak}-day streak achievement
3. Encourages them to get back on track TODAY
4. Is warm, understanding, and motivating

Keep it under 100 words. No salutations or signatures needed.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def generate_weekly_summary(user_id: str, completed_count: int, total_habits: int, xp_earned: int, top_habit: str = None) -> Optional[str]:
    """
    Generate weekly coaching summary email.
    
    Args:
        user_id: Username
        completed_count: Number of habits completed this week
        total_habits: Total habits user has
        xp_earned: Total XP earned this week
        top_habit: Best performing habit name
    
    Returns:
        Coaching message string, or None if OpenAI not available
    """
    client = get_openai_client()
    if not client:
        return None
    
    top_habit_text = f"Your star habit was '{top_habit}'" if top_habit else "You had strong consistency"
    
    prompt = f"""
You are an encouraging personal coach. Write a SHORT weekly coaching summary email.

User: {user_id}
Habits Completed This Week: {completed_count}/{total_habits}
Total XP Earned: {xp_earned}
Top Habit: {top_habit_text}

Write a 3-4 sentence weekly summary that:
1. Celebrates their week (they completed {completed_count} habits!)
2. Highlights their XP progress
3. Mentions their top habit if available
4. Motivates them for the upcoming week

Keep it under 150 words. Be uplifting and specific. No salutations or signatures needed.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def generate_personalized_coaching(user_id: str, context: dict) -> Optional[str]:
    """
    Generate fully personalized coaching message based on user's current state.
    
    Args:
        user_id: Username
        context: Dict with keys like 'habits_completed', 'level', 'total_xp', 'current_streaks', etc.
    
    Returns:
        Coaching message string, or None if OpenAI not available
    """
    client = get_openai_client()
    if not client:
        return None
    
    context_str = json.dumps(context, indent=2)
    
    prompt = f"""
You are a wise, encouraging personal coach. Write SHORT personalized coaching advice.

User: {user_id}
Current Status:
{context_str}

Write 3-4 sentences of personalized coaching that:
1. Acknowledges their current progress
2. Identifies one area to focus on (based on their data)
3. Provides specific, actionable advice
4. Is warm, genuine, and motivating

Keep it under 120 words. No salutations or signatures needed.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=120
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def test_openai_connection() -> bool:
    """Test if OpenAI connection is available."""
    if not HAS_OPENAI:
        return False
    
    client = get_openai_client()
    if not client:
        return False
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'OpenAI connection successful' in one sentence."}
            ],
            max_tokens=20
        )
        return True
    except Exception as e:
        print(f"OpenAI test failed: {e}")
        return False
