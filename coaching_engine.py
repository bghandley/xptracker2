"""
Coaching Engine - Pattern Detection & Adaptive Recommendations
Analyzes user habits and creates personalized coaching recommendations after Day 14.
Responses in style of Thug Kitchen Cookbook meets the movie Heathers, but warm underneath.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from storage import get_storage
from onboarding import get_coaching_profile, calculate_days_since_signup


COACHING_INSIGHTS_FILE = "coaching_insights.json"


def load_coaching_insights() -> Dict[str, Dict]:
    """Load coaching insights history."""
    if not os.path.exists(COACHING_INSIGHTS_FILE):
        return {}
    
    try:
        with open(COACHING_INSIGHTS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading coaching insights: {e}")
        return {}


def save_coaching_insights(insights: Dict[str, Dict]) -> None:
    """Save coaching insights history."""
    try:
        with open(COACHING_INSIGHTS_FILE, 'w') as f:
            json.dump(insights, f, indent=2)
    except Exception as e:
        print(f"Error saving coaching insights: {e}")


def analyze_user_patterns(user_id: str) -> Dict[str, Any]:
    """
    Analyze user's habit patterns and return coaching insights.
    Only generates insights after Day 14.
    """
    days_since_signup = calculate_days_since_signup(user_id)
    
    # Only generate insights after Day 14
    if days_since_signup < 14:
        return {
            "ready": False,
            "reason": f"Check back on Day 14. You're on Day {days_since_signup}."
        }
    
    try:
        storage = get_storage()
        data = storage.load_data(user_id)
        profile = get_coaching_profile(user_id)
        
        habits = data.get("habits", {})
        completions = data.get("completions", {})
        
        if not habits or not completions:
            return {"ready": False, "reason": "Not enough data yet."}
        
        insights = {
            "ready": True,
            "generated_at": datetime.now().isoformat(),
            "days_since_signup": days_since_signup,
            "patterns": {},
            "recommendations": [],
            "strengths": [],
            "challenges": []
        }
        
        # === PATTERN 1: TIMING ANALYSIS ===
        timing_patterns = _analyze_timing_patterns(habits, completions)
        insights["patterns"]["timing"] = timing_patterns
        
        # === PATTERN 2: CONSISTENCY ANALYSIS ===
        consistency_patterns = _analyze_consistency(habits, completions)
        insights["patterns"]["consistency"] = consistency_patterns
        
        # === PATTERN 3: HABIT STREAKS ===
        streak_patterns = _analyze_streaks(habits, completions)
        insights["patterns"]["streaks"] = streak_patterns
        
        # === PATTERN 4: PROFILE ALIGNMENT ===
        alignment = _analyze_profile_alignment(profile, habits, completions)
        insights["patterns"]["profile_alignment"] = alignment
        
        # === GENERATE RECOMMENDATIONS ===
        insights["recommendations"] = _generate_recommendations(
            profile, 
            timing_patterns,
            consistency_patterns,
            streak_patterns,
            alignment
        )
        
        # === STRENGTHS & CHALLENGES ===
        insights["strengths"] = _identify_strengths(habits, completions, timing_patterns)
        insights["challenges"] = _identify_challenges(habits, completions, profile)
        
        return insights
    
    except Exception as e:
        print(f"Error analyzing patterns for {user_id}: {e}")
        return {"ready": False, "reason": "Error analyzing patterns."}


def _analyze_timing_patterns(habits: Dict, completions: Dict) -> Dict[str, Any]:
    """Detect timing patterns: morning vs evening, consistency of time."""
    from datetime import datetime as dt
    
    timing_data = {}
    
    for date_str, day_completions in completions.items():
        try:
            date_obj = dt.fromisoformat(date_str)
            hour = date_obj.hour
            
            for habit_name in day_completions:
                if habit_name not in timing_data:
                    timing_data[habit_name] = {"hours": []}
                timing_data[habit_name]["hours"].append(hour)
        except:
            continue
    
    # Analyze patterns
    patterns = {}
    for habit, data in timing_data.items():
        if not data["hours"]:
            continue
        
        avg_hour = sum(data["hours"]) / len(data["hours"])
        
        if avg_hour < 12:
            pattern = "morning"
        elif avg_hour < 17:
            pattern = "afternoon"
        else:
            pattern = "evening"
        
        consistency = len(set(data["hours"])) / len(data["hours"]) if data["hours"] else 1
        
        patterns[habit] = {
            "primary_time": pattern,
            "average_hour": round(avg_hour, 1),
            "consistency": round(consistency, 2),  # Lower = more consistent
            "total_completions": len(data["hours"])
        }
    
    return patterns


def _analyze_consistency(habits: Dict, completions: Dict) -> Dict[str, Any]:
    """Analyze habit completion consistency: daily, weekends, weekdays."""
    from datetime import datetime as dt
    
    consistency = {}
    
    for habit_name in habits:
        habit_completions = []
        
        for date_str, day_completions in completions.items():
            if habit_name in day_completions:
                try:
                    date_obj = dt.fromisoformat(date_str)
                    habit_completions.append(date_obj)
                except:
                    continue
        
        if not habit_completions:
            continue
        
        # Calculate streaks
        sorted_dates = sorted(habit_completions)
        current_streak = 1
        max_streak = 1
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        
        # Calculate completion rate
        days_with_habit = (max(sorted_dates) - min(sorted_dates)).days + 1 if sorted_dates else 1
        completion_rate = len(sorted_dates) / days_with_habit if days_with_habit > 0 else 0
        
        # Check weekday vs weekend preference
        weekday_count = sum(1 for d in sorted_dates if d.weekday() < 5)
        weekend_count = sum(1 for d in sorted_dates if d.weekday() >= 5)
        
        consistency[habit_name] = {
            "completion_rate": round(completion_rate, 2),
            "current_streak": current_streak,
            "max_streak": max_streak,
            "total_days_tracked": len(sorted_dates),
            "weekday_preference": "strong_weekday" if weekday_count > weekend_count * 1.5 else ("strong_weekend" if weekend_count > weekday_count * 1.5 else "balanced"),
            "weekday_completions": weekday_count,
            "weekend_completions": weekend_count
        }
    
    return consistency


def _analyze_streaks(habits: Dict, completions: Dict) -> Dict[str, Any]:
    """Get current streak info for each habit."""
    from datetime import datetime as dt
    
    streak_info = {}
    today = dt.now().date()
    
    for habit_name in habits:
        streak = 0
        check_date = today
        
        # Count backwards from today
        while True:
            date_str = check_date.isoformat()
            if date_str in completions and habit_name in completions[date_str]:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        streak_info[habit_name] = {
            "current_streak": streak,
            "status": "🔥 Hot!" if streak >= 7 else ("⚡ Good" if streak >= 3 else ("🌱 Building" if streak > 0 else "❌ Needs restart"))
        }
    
    return streak_info


def _analyze_profile_alignment(profile: Dict, habits: Dict, completions: Dict) -> Dict[str, Any]:
    """Check if habits align with stated goals and profile."""
    main_habit = profile.get("main_habit", "").lower()
    life_goals = [g.lower() for g in profile.get("life_goals", [])]
    biggest_obstacle = profile.get("biggest_obstacle", "")
    chronotype = profile.get("chronotype", "morning")
    
    alignment = {
        "main_habit_tracked": False,
        "main_habit_consistent": False,
        "goal_alignment": 0,  # 0-100
        "obstacle_insights": None
    }
    
    # Check if main habit is being tracked
    for habit_name in habits:
        if main_habit in habit_name.lower() or habit_name.lower() in main_habit:
            alignment["main_habit_tracked"] = True
            # Check if consistent (>50% completion rate)
            break
    
    # Check goal alignment
    health_keywords = ["health", "fitness", "exercise", "sleep", "meditat", "yoga", "walk", "run"]
    learning_keywords = ["learn", "study", "read", "code", "course", "skill"]
    mental_keywords = ["mental", "wellness", "mindful", "journal", "therapy"]
    
    matching_habits = 0
    for habit_name in habits:
        habit_lower = habit_name.lower()
        if any(kw in habit_lower for kw in health_keywords + learning_keywords + mental_keywords):
            matching_habits += 1
    
    alignment["goal_alignment"] = min(100, (matching_habits / max(len(habits), 1)) * 100) if habits else 0
    
    # Obstacle-specific insights
    if "time" in biggest_obstacle.lower():
        alignment["obstacle_insights"] = "time_issue"
    elif "motivation" in biggest_obstacle.lower():
        alignment["obstacle_insights"] = "motivation_issue"
    elif "forget" in biggest_obstacle.lower():
        alignment["obstacle_insights"] = "memory_issue"
    elif "perfect" in biggest_obstacle.lower():
        alignment["obstacle_insights"] = "perfectionism"
    
    return alignment


def _generate_recommendations(
    profile: Dict,
    timing_patterns: Dict,
    consistency_patterns: Dict,
    streak_patterns: Dict,
    alignment: Dict
) -> List[str]:
    """Generate personalized coaching recommendations."""
    recommendations = []
    
    # === TIMING RECOMMENDATIONS ===
    for habit, timing in timing_patterns.items():
        if timing["consistency"] > 0.5:  # Low consistency
            time = timing["primary_time"]
            recommendations.append(
                f"🕐 {habit}: You usually do this in the {time}. Try habit stacking with an existing routine."
            )
    
    # === CONSISTENCY RECOMMENDATIONS ===
    for habit, cons in consistency_patterns.items():
        rate = cons["completion_rate"]
        
        if rate < 0.5:
            recommendations.append(
                f"📊 {habit}: Only {int(rate*100)}% completion. This might be too ambitious or wrong time. Scale down or reschedule."
            )
        
        if cons["weekday_preference"] == "strong_weekday":
            recommendations.append(
                f"📅 {habit}: You're skipping weekends. Try stacking with weekend routines."
            )
        elif cons["weekday_preference"] == "strong_weekend":
            recommendations.append(
                f"📅 {habit}: You're skipping weekdays. This habit might need a different trigger on weekdays."
            )
    
    # === MOTIVATION RECOMMENDATIONS ===
    for habit, streak in streak_patterns.items():
        if streak["current_streak"] == 0:
            recommendations.append(
                f"💪 {habit}: Momentum lost. Pick ONE action: reschedule, reduce scope, or pair with an easy habit."
            )
    
    # === PROFILE ALIGNMENT ===
    if not alignment["main_habit_tracked"]:
        recommendations.append(
            "🎯 Your main habit isn't in the tracker. Add it so we can coach you on it specifically."
        )
    
    # === OBSTACLE-SPECIFIC ===
    obstacle = alignment.get("obstacle_insights")
    if obstacle == "time_issue":
        recommendations.append(
            "⏰ Time is your challenge. Try: identify your peak hour, batch habits, or use time-blocking."
        )
    elif obstacle == "motivation_issue":
        recommendations.append(
            "🔥 Motivation dips are normal by Week 2. Focus on identity: 'I'm someone who...'"
        )
    elif obstacle == "memory_issue":
        recommendations.append(
            "🔔 Forgetting? Add phone notifications or anchor to existing habits (stacking)."
        )
    elif obstacle == "perfectionism":
        recommendations.append(
            "⭐ Perfectionism kills consistency. One imperfect day doesn't break your streak. Progress over perfection."
        )
    
    return recommendations[:5]  # Top 5 recommendations


def _identify_strengths(habits: Dict, completions: Dict, timing_patterns: Dict) -> List[str]:
    """Identify user's strengths and wins."""
    strengths = []
    
    if len(habits) >= 3:
        strengths.append("🎯 Ambitious: You're tracking 3+ habits simultaneously")
    
    if len(completions) >= 7:
        strengths.append("💪 Consistent: You've been tracking for over a week")
    
    if len(completions) >= 14:
        strengths.append("🔥 Dedicated: You've hit the critical 2-week mark")
    
    # Check for high-consistency habits
    for habit, timing in timing_patterns.items():
        if timing["consistency"] < 0.3:  # High consistency
            strengths.append(f"⚡ {habit} is locked in: Same time every day")
    
    return strengths


def _identify_challenges(habits: Dict, completions: Dict, profile: Dict) -> List[str]:
    """Identify current challenges and friction points."""
    challenges = []
    
    obstacle = profile.get("biggest_obstacle", "").lower()
    
    if "time" in obstacle:
        challenges.append("⏰ Time management is hard—let's find your 'peak hour'")
    
    if "motivation" in obstacle or "discipline" in obstacle:
        challenges.append("🔥 Motivation dips by Week 2—this is normal. We'll shift to identity.")
    
    if "forget" in obstacle:
        challenges.append("🔔 Remembering is tough. We'll help you build better triggers.")
    
    if "perfect" in obstacle:
        challenges.append("⭐ One missed day doesn't erase your progress. Let's aim for consistency, not perfection.")
    
    # Detect actual challenges in data
    if len(completions) < 7:
        challenges.append("📉 You're in the danger zone (Week 1-2). Most people quit here.")
    
    return challenges[:3]


def get_coaching_email_for_user(user_id: str) -> Optional[Dict[str, str]]:
    """
    Generate coaching email content based on current analysis.
    Used in daily digests and drip campaigns after Day 14.
    """
    insights = analyze_user_patterns(user_id)
    
    if not insights.get("ready"):
        return None
    
    profile = get_coaching_profile(user_id)
    
    subject = f"🎯 Your Day {insights['days_since_signup']} Coaching Insight"
    
    # Build email body
    body = f"""
Hi {profile.get('success_factor', 'there')},

**Your Pattern Report (Day {insights['days_since_signup']})**

🎯 **Your Top Recommendations:**
"""
    
    for i, rec in enumerate(insights.get("recommendations", []), 1):
        body += f"\n{i}. {rec}"
    
    body += f"\n\n💪 **Your Strengths:**\n"
    for strength in insights.get("strengths", []):
        body += f"- {strength}\n"
    
    body += f"\n⚠️ **Current Challenges:**\n"
    for challenge in insights.get("challenges", []):
        body += f"- {challenge}\n"
    
    body += f"""

Remember: This data shows patterns. Small tweaks compound. You're building something real.

Your XP Tracker Coach
"""
    
    return {
        "subject": subject,
        "body": body,
        "insights": insights
    }
