"""
Gemini Goal Recommendation Engine
Generates personalized goal ideas using Google Gemini, with deterministic fallbacks.
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from coaching_emails import get_gemini_client, get_gemini_status

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

def generate_goal_recommendations_gemini(
    profile: Dict[str, Any],
    extra_context: Dict[str, Any] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Generate personalized goal ideas using Gemini.

    Args:
        profile: User onboarding profile (life_goals, why_now, biggest_obstacle, etc.)
        extra_context: Optional extra user input (e.g., specific area of focus)

    Returns:
        Tuple: (List of dicts, error_message_string)
        - If successful: ([...], None)
        - If failed: ([], "Error reason")
    """
    client = get_gemini_client()
    if not client:
        # Check why it failed
        ok, msg, _ = get_gemini_status()
        return [], msg or "Unknown Gemini error"

    life_goals = profile.get("life_goals", []) or ["General Improvement"]
    why_now = profile.get("why_now", "To get better.")
    obstacle = profile.get("biggest_obstacle", "None")
    success_factor = profile.get("success_factor", "Consistency")

    context_str = f"""
    Life Goals: {', '.join(life_goals)}
    Why Now: {why_now}
    Biggest Obstacle: {obstacle}
    Success Factor: {success_factor}
    """

    if extra_context:
        for k, v in extra_context.items():
            if v:
                context_str += f"\n    {k}: {v}"

    prompt = f"""
You are an expert life coach. Based on the user's profile, suggest 3-4 specific, high-impact high-level GOALS (not just habits, but the outcome/objective).
The goals should be exciting, achievable, and directly address their "Why Now".

Profile:
{context_str}

Return ONLY JSON (no markdown, no prose) in this exact shape:
[
  {{
    "name": "Run a 5k in under 30 mins",
    "category": "Health",
    "reason": "Directly addresses your desire to get fit, with a clear metric."
  }}
]

Rules:
- Make goals specific (SMART goals where possible).
- Ensure they align with the 'Life Goals' categories.
- 'Reason' should explain why this specific goal fits their profile.
"""

    try:
        response = client.generate_content(prompt)
        cleaned = _clean_json_block(response.text)
        data = json.loads(cleaned)

        # Validate structure
        valid_recs = []
        for item in data:
            if isinstance(item, dict) and "name" in item and "category" in item:
                valid_recs.append(item)

        return valid_recs, None

    except Exception as e:
        print(f"Gemini goal rec error: {e}")
        return [], str(e)

def generate_goal_recommendations(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic fallback for goal recommendations."""
    life_goals = profile.get("life_goals", [])
    recs = []

    for category in life_goals:
        cat_lower = category.lower()
        if "health" in cat_lower or "fitness" in cat_lower:
            recs.append({
                "name": "Complete a 30-Day Fitness Challenge",
                "category": category,
                "reason": "A time-bound challenge is a great way to jumpstart your fitness journey."
            })
        elif "career" in cat_lower or "learning" in cat_lower:
            recs.append({
                "name": "Master a New Skill (e.g. Python, Public Speaking)",
                "category": category,
                "reason": "Focusing on a single skill helps you make tangible career progress."
            })
        elif "mental" in cat_lower:
            recs.append({
                "name": "Establish a Daily Mindfulness Routine",
                "category": category,
                "reason": "Consistent mindfulness reduces stress and improves focus."
            })
        elif "finance" in cat_lower or "money" in cat_lower:
            recs.append({
                "name": "Save $1,000 Emergency Fund",
                "category": category,
                "reason": "Financial security starts with a safety net."
            })
        else:
             recs.append({
                "name": f"Improve {category}",
                "category": category,
                "reason": f" dedicating time to {category} will improve your life balance."
            })

    # Deduplicate and limit
    unique_recs = []
    seen = set()
    for r in recs:
        if r["name"] not in seen:
            unique_recs.append(r)
            seen.add(r["name"])

    return unique_recs[:4]
