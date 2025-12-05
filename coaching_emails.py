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
        # Return fallback message
        return f"{streak}-day streak on '{habit_name}' — that's the thinking that changes the game. Most people don't. You are."
    
    prompt = f"""
You are a Price Pritchett-style quantum coach. Write a SHORT streak celebration (2 sentences max, under 50 words).

Style: Challenging but supportive. Quantum thinking. Action-focused. No fluff.
- Don't celebrate effort; celebrate breakthrough thinking
- Reference that most people quit; they're not
- Make it about elevation, not maintenance
- Slightly provocative edge, but warm underneath

Streak: {streak} days on '{habit_name}'

Example good: "30 days of this? That's the difference-maker. But here's the real win: you've proven you can. Most people never do."
Example bad: "Great job! Keep it up!" (too generic)

Write exactly 2 sentences. No "Hi {user_id}" or signature needed.
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
        return f"{streak}-day streak on '{habit_name}' — that's the thinking that changes the game. Most people don't. You are."


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
        # Return fallback message
        return f"Missed a day? That's data, not a defeat. You had a {last_streak}-day streak — that's real. Now: what's the game to get it back?"
    
    prompt = f"""
You are a Price Pritchett-style quantum coach. Write a SHORT, supportive missed-day encouragement (2 sentences max, under 60 words).

Style: Challenging but NOT guilt-tripping. Reframe as data. Action-oriented. Quantum thinking.
- Normalize the miss (everyone has)
- Reference the {last_streak}-day streak as PROOF of capability
- Don't shame; ask "what's the move NOW?"
- Subtle dare to get back on track

Habit: '{habit_name}'
Previous Streak: {last_streak} days

Example good: "You missed one. That's noise. Your {last_streak}-day streak proves you can. So: what's the move to start again today?"
Example bad: "Don't worry, it happens! Try again tomorrow."

Write exactly 2 sentences. No "Hi" or signature needed.
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
        return f"Missed a day? That's data, not a defeat. You had a {last_streak}-day streak — that's real. Now: what's the game to get it back?"


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
        # Return fallback message
        pct = int((completed_count / total_habits) * 100) if total_habits > 0 else 0
        return f"You hit {pct}% this week. That's a pattern emerging. The question: is this the pattern you want? If not, what shifts this coming week?"
    
    prompt = f"""
You are a Price Pritchett-style quantum coach. Write a SHORT weekly summary (3 sentences max, under 80 words).

Style: Data-driven. Quantum thinking. Challenge embedded in support.
- Show the metric ({completed_count}/{total_habits} = {int((completed_count/total_habits)*100) if total_habits else 0}%)
- Ask: is this the pattern they WANT?
- Mention top habit as proof of capability
- End with a slight dare/question for next week

Completed: {completed_count}/{total_habits}
XP Earned: {xp_earned}
Top Habit: {top_habit or "mixed results"}

Example good: "You hit 5/7 this week (71%). That's a pattern. Question: is this the pattern you want? Your '{top_habit}' proves you can. So: what shifts next week?"
Example bad: "Great job this week! Keep it up!"

Write exactly 3 sentences. No "Hi" or signature needed.
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
        pct = int((completed_count / total_habits) * 100) if total_habits > 0 else 0
        return f"You hit {pct}% this week. That's a pattern emerging. The question: is this the pattern you want? If not, what shifts this coming week?"


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
        # Return fallback message
        return f"You're at a pivot point. The habits you've built are proof. Now: which one friction do you remove this week? Pick one. Remove it."
    
    prompt = f"""
You are a Price Pritchett-style quantum coach. Write SHORT personalized coaching (3 sentences max, under 70 words).

Style: Data-driven. Quantum breakthroughs. Slightly provocative but warm.
- Reference their actual data (level, streaks, top habit)
- Identify ONE edge they're not playing yet
- Give a specific micro-action (not philosophy)
- End with a slight dare

Context:
{json.dumps(context, indent=2)}

Example good: "You're Level 5 with a 12-day meditation streak. But I notice your 'Exercise' habit is stuck at 3 days. Here's the move: stack exercise right after meditation. One week. See what shifts."
Example bad: "Keep up the great work!"

Write exactly 3 sentences. No "Hi" or signature needed.
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
        return f"You're at a pivot point. The habits you've built are proof. Now: which one friction do you remove this week? Pick one. Remove it."


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
