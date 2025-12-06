"""
Guided Onboarding Questionnaire
Collects coaching profile data during account creation to enable hyper-personalized coaching.
This data is adjustable later as habits evolve.
"""

import streamlit as st
from typing import Dict, Any, Optional
from storage import get_storage

# Questions for the onboarding flow
ONBOARDING_QUESTIONS = [
    {
        "id": "life_goals",
        "question": "🎯 What are your top 3 life goals? (Select or type)",
        "type": "multiselect",
        "options": ["Health & Fitness", "Career & Learning", "Mental Wellness", "Relationships", "Financial", "Personal Growth", "Creativity", "Spirituality"],
        "help": "These goals will help us personalize your coaching."
    },
    {
        "id": "main_habit",
        "question": "💪 What's the ONE habit you're most committed to starting?",
        "type": "text",
        "help": "Example: Daily meditation, morning run, learning Spanish"
    },
    {
        "id": "biggest_obstacle",
        "question": "🚧 What's your biggest obstacle to building habits?",
        "type": "select",
        "options": ["Lack of time", "Motivation/discipline", "Forgetting", "Perfectionism", "Inconsistent schedule", "Not sure yet", "Other"],
        "help": "This helps us coach you specifically."
    },
    {
        "id": "why_now",
        "question": "⏰ What triggered this change? Why now?",
        "type": "text",
        "help": "Example: New Year's resolution, health scare, career transition, etc."
    },
    {
        "id": "timezone",
        "question": "🌍 What's your timezone?",
        "type": "select",
        "options": ["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"],
        "help": "For scheduling your daily digest and drip emails."
    },
    {
        "id": "chronotype",
        "question": "🌅 Are you a morning or evening person?",
        "type": "select",
        "options": ["Morning person ☀️", "Evening person 🌙", "Both equally"],
        "help": "Affects when we send your daily digest and coaching tips."
    },
    {
        "id": "success_factor",
        "question": "🏆 What ONE thing would make you successful?",
        "type": "text",
        "help": "Example: Accountability buddy, tracking streaks, community challenge, etc."
    },
]


def show_onboarding_modal():
    """Display the onboarding questionnaire as a modal/centered form."""
    st.title("🚀 Welcome to XP Tracker Coaching!")
    st.write("Let's personalize your experience. Answer these 7 questions so we can coach you specifically.")
    
    # Create form
    with st.form("onboarding_form", clear_on_submit=False):
        responses = {}
        
        for q in ONBOARDING_QUESTIONS:
            st.markdown(f"**{q['question']}**")
            st.caption(q['help'])
            
            if q['type'] == 'text':
                responses[q['id']] = st.text_input(
                    label=q['id'],
                    label_visibility="collapsed",
                    placeholder=f"Enter {q['id']}...",
                    key=f"onboard_{q['id']}"
                )
            
            elif q['type'] == 'select':
                responses[q['id']] = st.selectbox(
                    label=q['id'],
                    label_visibility="collapsed",
                    options=q['options'],
                    key=f"onboard_{q['id']}"
                )
            
            elif q['type'] == 'multiselect':
                responses[q['id']] = st.multiselect(
                    label=q['id'],
                    label_visibility="collapsed",
                    options=q['options'],
                    max_selections=3,
                    key=f"onboard_{q['id']}"
                )
            
            st.divider()
        
        # Submit button
        submitted = st.form_submit_button("✅ Complete Setup & Start Tracking!", use_container_width=True)
        
        if submitted:
            # Basic validation
            is_valid = True
            if not all(responses.get(field, '').strip() for field in ['main_habit', 'why_now', 'success_factor']):
                st.error("Please enter your main habit.")
                is_valid = False

            if not responses.get('life_goals'):
                st.error("Please select at least one life goal.")
                is_valid = False

            if is_valid:
                # Store in session state for the caller to process
                st.session_state['onboarding_responses'] = responses
                # Set a flag to indicate successful submission
                st.session_state['onboarding_submitted'] = True
                st.rerun() # Rerun to allow the calling script to handle the submission

    return False


def save_onboarding_profile(user_id: str, responses: Dict[str, Any]) -> bool:
    """Save onboarding responses to user's coaching profile."""
    try:
        storage = get_storage()
        data = storage.load_data(user_id)
        
        # Map responses to coaching_profile
        data['coaching_profile']['life_goals'] = responses.get('life_goals', [])
        data['coaching_profile']['main_habit'] = responses.get('main_habit', '').strip()
        data['coaching_profile']['biggest_obstacle'] = responses.get('biggest_obstacle', '')
        data['coaching_profile']['why_now'] = responses.get('why_now', '').strip()
        data['coaching_profile']['timezone'] = responses.get('timezone', 'UTC')
        
        # Parse chronotype
        chronotype = responses.get('chronotype', 'morning')
        if 'Morning' in chronotype:
            data['coaching_profile']['chronotype'] = 'morning'
            data['coaching_profile']['digest_time'] = '07:00'  # 7 AM
        elif 'Evening' in chronotype:
            data['coaching_profile']['chronotype'] = 'evening'
            data['coaching_profile']['digest_time'] = '20:00'  # 8 PM
        else:
            data['coaching_profile']['chronotype'] = 'flexible'
            data['coaching_profile']['digest_time'] = '19:00'  # 7 PM compromise
        
        data['coaching_profile']['success_factor'] = responses.get('success_factor', '').strip()
        data['coaching_profile']['onboarding_complete'] = True
        
        storage.save_data(user_id, data)
        return True
    except Exception as e:
        print(f"Error saving onboarding profile: {e}")
        return False


def get_coaching_profile(user_id: str) -> Dict[str, Any]:
    """Retrieve user's coaching profile."""
    try:
        storage = get_storage()
        data = storage.load_data(user_id)
        return data.get('coaching_profile', {})
    except Exception as e:
        print(f"Error loading coaching profile: {e}")
        return {}


def has_completed_onboarding(user_id: str) -> bool:
    """Check if user has completed onboarding."""
    profile = get_coaching_profile(user_id)
    return profile.get('onboarding_complete', False)


def show_profile_editor(user_id: str) -> bool:
    """Show editable coaching profile in Profile tab. Returns True if saved."""
    profile = get_coaching_profile(user_id)
    
    if not profile.get('onboarding_complete'):
        st.warning("⚠️ Coaching profile not set up yet. Complete onboarding to enable personalized coaching.")
        if st.button("Complete Onboarding Now"):
            st.session_state['show_onboarding'] = True
            st.rerun()
        return False
    
    st.subheader("🎯 Your Coaching Profile")
    st.write("Adjust these as your habits and goals evolve:")
    
    with st.form("coaching_profile_form"):
        # Life goals
        life_goals = st.multiselect(
            "Life Goals",
            options=["Health & Fitness", "Career & Learning", "Mental Wellness", "Relationships", "Financial", "Personal Growth", "Creativity", "Spirituality"],
            default=profile.get('life_goals', []),
            max_selections=3,
            help="Your top 3 areas of focus"
        )
        
        # Main habit
        main_habit = st.text_input(
            "Primary Habit",
            value=profile.get('main_habit', ''),
            help="Your most committed habit"
        )
        
        # Biggest obstacle
        biggest_obstacle = st.selectbox(
            "Biggest Obstacle",
            options=["Lack of time", "Motivation/discipline", "Forgetting", "Perfectionism", "Inconsistent schedule", "Not sure yet", "Other"],
            index=0 if not profile.get('biggest_obstacle') else ["Lack of time", "Motivation/discipline", "Forgetting", "Perfectionism", "Inconsistent schedule", "Not sure yet", "Other"].index(profile.get('biggest_obstacle', 'Not sure yet')),
            help="What's your main challenge?"
        )
        
        # Why now
        why_now = st.text_area(
            "Why Now?",
            value=profile.get('why_now', ''),
            height=80,
            help="What triggered this change?"
        )
        
        # Timezone
        timezone = st.selectbox(
            "Timezone",
            options=["UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8", "UTC-7", "UTC-6", "UTC-5", "UTC-4", "UTC-3", "UTC-2", "UTC-1", "UTC", "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6", "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"],
            index=12 if profile.get('timezone', 'UTC') == 'UTC' else 0,
            help="For scheduling daily digest"
        )
        
        # Chronotype
        chronotype_map = {'morning': 'Morning person ☀️', 'evening': 'Evening person 🌙', 'flexible': 'Both equally'}
        current_chrono = chronotype_map.get(profile.get('chronotype', 'morning'), 'Morning person ☀️')
        chronotype = st.selectbox(
            "Chronotype",
            options=["Morning person ☀️", "Evening person 🌙", "Both equally"],
            index=["Morning person ☀️", "Evening person 🌙", "Both equally"].index(current_chrono),
            help="Affects when you receive coaching"
        )
        
        # Success factor
        success_factor = st.text_input(
            "Success Factor",
            value=profile.get('success_factor', ''),
            help="One thing that would make you successful"
        )
        
        # Daily digest time preference
        digest_time = st.time_input(
            "Preferred Daily Digest Time",
            value=_parse_time(profile.get('digest_time', '20:00')),
            help="When would you like your daily summary email?"
        )
        
        submitted = st.form_submit_button("💾 Save Profile Changes")
        
        if submitted:
            try:
                storage = get_storage()
                data = storage.load_data(user_id)
                
                # Update profile
                data['coaching_profile']['life_goals'] = life_goals
                data['coaching_profile']['main_habit'] = main_habit.strip()
                data['coaching_profile']['biggest_obstacle'] = biggest_obstacle
                data['coaching_profile']['why_now'] = why_now.strip()
                data['coaching_profile']['timezone'] = timezone
                data['coaching_profile']['success_factor'] = success_factor.strip()
                
                # Update chronotype and digest time
                if 'Morning' in chronotype:
                    data['coaching_profile']['chronotype'] = 'morning'
                elif 'Evening' in chronotype:
                    data['coaching_profile']['chronotype'] = 'evening'
                else:
                    data['coaching_profile']['chronotype'] = 'flexible'
                
                data['coaching_profile']['digest_time'] = digest_time.strftime('%H:%M')
                
                storage.save_data(user_id, data)
                st.success("✅ Profile updated! Your coaching will adapt accordingly.")
                return True
            except Exception as e:
                st.error(f"Error saving profile: {e}")
                return False
    
    return False


def _parse_time(time_str: str):
    """Parse HH:MM string to time object for st.time_input."""
    try:
        from datetime import time
        parts = time_str.split(':')
        return time(int(parts[0]), int(parts[1]))
    except:
        from datetime import time
        return time(20, 0)  # Default to 8 PM


def get_habit_info(user_id: str, habit_name: str) -> Optional[Dict[str, Any]]:
    """Get detailed info about a specific habit for personalized coaching."""
    try:
        storage = get_storage()
        data = storage.load_data(user_id)
        habits = data.get('habits', {})
        return habits.get(habit_name, {})
    except:
        return None


def calculate_days_since_signup(user_id: str) -> int:
    """Calculate days since user first created an account or first tracked."""
    try:
        import datetime
        storage = get_storage()
        data = storage.load_data(user_id)
        completions = data.get('completions', {})
        
        if not completions:
            return 0
        
        first_date = min(completions.keys())
        first = datetime.datetime.fromisoformat(first_date).date()
        today = datetime.date.today()
        return (today - first).days
    except:
        return 0
