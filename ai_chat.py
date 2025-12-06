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
