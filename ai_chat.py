"""
AI Chat Module
Handles free-form chat with the AI Coach using Gemini.
"""

import streamlit as st
from typing import List, Dict, Any
from coaching_emails import get_gemini_client

def get_ai_response(user_message: str, context: Dict[str, Any]) -> str:
    """
    Get a response from Gemini for the user's chat message.
    """
    client = get_gemini_client()
    if not client:
        return "I'm sorry, my AI brain (Gemini) is not connected right now. Please check the API key settings."

    # Construct context string
    profile = context.get('profile', {})
    stats = context.get('stats', {})

    context_str = f"""
    User Profile:
    - Life Goals: {', '.join(profile.get('life_goals', []))}
    - Main Habit: {profile.get('main_habit', 'N/A')}
    - Biggest Obstacle: {profile.get('biggest_obstacle', 'N/A')}

    Current Stats:
    - Level: {stats.get('level', 1)}
    - Total XP: {stats.get('total_xp', 0)}
    - Active Habits: {len(context.get('habits', {}))}
    """

    prompt = f"""
    You are an elite habit coach, inspired by Price Pritchett (Quantum Leap strategy) and James Clear (Atomic Habits).

    Context about the user:
    {context_str}

    User Message: "{user_message}"

    Respond directly to the user. Be encouraging but firm. Focus on action, consistency, and identity change. Keep it under 100 words unless asked for a detailed plan.
    """

    try:
        response = client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"I encountered an error thinking about that: {str(e)}"

def generate_journal_prompt(context: Dict[str, Any]) -> str:
    """
    Generate a personalized journal writing prompt.

    Args:
        context: User context (goals, stats, habits)

    Returns:
        String prompt
    """
    client = get_gemini_client()
    if not client:
        return "Write about your biggest win this week and one thing you want to improve next week."

    # Construct context string
    profile = context.get('profile', {})
    stats = context.get('stats', {})

    context_str = f"""
    Life Goals: {', '.join(profile.get('life_goals', []))}
    Main Habit: {profile.get('main_habit', 'N/A')}
    Level: {stats.get('level', 1)}
    """

    prompt = f"""
    You are a thoughtful journaling assistant. Based on the user's profile, generate a single, deep, reflective writing prompt.

    First, write 1 short sentence recognizing their effort/habit building (cheering them on).
    Then, provide the writing prompt.

    User Context:
    {context_str}

    Example output:
    "You're showing up consistently for your health, which is huge. Prompt: What does the 'Level 10' version of you do differently on a stressful day?"
    """

    try:
        response = client.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "Write about your biggest win this week and one thing you want to improve next week."
