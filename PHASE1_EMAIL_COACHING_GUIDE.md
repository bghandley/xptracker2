# 🚀 Implement Phase 1: Email-First Coaching (Quick Start)

**Effort**: 2-3 hours  
**Complexity**: Low  
**Impact**: High (adds conversational coaching via email)

---

## 📋 Overview

Users can email coaching requests and get AI responses. Examples:

```
User emails:
  To: coach-support@example.com
  Subject: "Goal: Build a morning routine"

System replies (within minutes):
  Subject: "Re: Goal: Build a morning routine"
  Body: "[Gemini-generated coaching with 3-4 specific habits to build]"
```

---

## 🔧 Implementation Steps

### Step 1: Create Email Command Parser

Create new file: `coaching_email_commands.py`

```python
"""
Email command processor for coaching requests.
Users can email coaching requests with specific subject patterns.
"""

import json
from datetime import datetime
from storage import get_storage
import google.generativeai as genai


def parse_coaching_email(subject: str, body: str) -> dict:
    """
    Parse coaching request email and determine type.
    
    Subject patterns:
    - "Goal: Learn Spanish in 30 days"
    - "Question: How do I build consistency?"
    - "Review: I hit a 10-day streak!"
    - "Habit: Should I add morning yoga?"
    """
    
    subject_lower = subject.lower()
    
    if subject_lower.startswith("goal:"):
        request_type = "goal_setup"
        content = subject.replace("Goal:", "").replace("goal:", "").strip()
    elif subject_lower.startswith("question:"):
        request_type = "question"
        content = body.strip()
    elif subject_lower.startswith("review:"):
        request_type = "achievement"
        content = subject.replace("Review:", "").replace("review:", "").strip()
    elif subject_lower.startswith("habit:"):
        request_type = "habit_advice"
        content = subject.replace("Habit:", "").replace("habit:", "").strip()
    else:
        request_type = "general"
        content = f"{subject}\n\n{body}".strip()
    
    return {
        "type": request_type,
        "content": content,
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat()
    }


def get_user_context(user_id: str) -> dict:
    """Get user's current stats for coaching context."""
    try:
        storage = get_storage()
        user_data = storage.load_data(user_id)
        
        # Calculate streaks
        streaks = {}
        for habit_name, habit_data in user_data.get("habits", {}).items():
            streaks[habit_name] = habit_data.get("current_streak", 0)
        
        return {
            "level": user_data.get("level", 1),
            "xp": user_data.get("xp", 0),
            "total_xp": user_data.get("total_xp", 0),
            "active_habits": list(user_data.get("habits", {}).keys()),
            "streaks": streaks,
            "top_habit": max(streaks, key=streaks.get) if streaks else None,
            "badges": len(user_data.get("badges", []))
        }
    except Exception as e:
        print(f"Error getting user context: {e}")
        return {}


def generate_coaching_response(user_id: str, request: dict) -> str:
    """
    Generate Gemini-powered coaching response based on request type.
    """
    
    try:
        context = get_user_context(user_id)
        
        # Build request-specific prompt
        prompts = {
            "goal_setup": f"""
You are a Price Pritchett quantum coach. A user wants to: {request['content']}

Their current progress:
- Level: {context.get('level', 1)}
- Active habits: {', '.join(context.get('active_habits', [])) or 'None yet'}
- Best streak: {max(context.get('streaks', {}).values()) if context.get('streaks') else 'N/A'} days

Generate a specific, actionable coaching response with:
1. Breakdown their goal into 3-4 daily habits (be specific)
2. Timeline: Week 1, 2, 3, 4 targets
3. Identify the biggest trap they'll hit
4. Give a specific daily action (not philosophy)
5. End with a slightly provocative but supportive challenge

Keep it under 180 words. Price Pritchett tone: data-driven, slightly edgy, warm underneath.

DO NOT say "Here's my recommendation" - just give it direct.
""",

            "question": f"""
You are a Price Pritchett quantum coach. User question: {request['content']}

Their stats:
- Level: {context.get('level', 1)}
- Current habits: {', '.join(context.get('active_habits', [])) or 'Building from scratch'}
- Top habit: {context.get('top_habit')} ({context.get('streaks', {}).get(context.get('top_habit'), 0)} days)

Answer their question with:
1. Specific, data-driven advice
2. Reference their actual progress
3. Give 1-2 micro-actions they can do today
4. Slightly provocative but supportive tone

Keep it under 150 words. Be direct and actionable.
""",

            "achievement": f"""
You are a Price Pritchett quantum coach. User milestone: {request['content']}

Their stats:
- Level: {context.get('level', 1)}
- Total XP: {context.get('total_xp', 0)}
- Active habits: {context.get('active_habits', [])}

Celebrate their win, then:
1. Acknowledge what this proves about them
2. Identify the NEXT edge they're not playing yet
3. Raise the bar slightly (make it feel like a dare)
4. Give 1 specific action for this week

Keep it under 130 words. Slightly provocative but warm. Make them feel seen AND challenged.
""",

            "habit_advice": f"""
You are a Price Pritchett quantum coach. User considering habit: {request['content']}

Their current setup:
- Level: {context.get('level', 1)}
- Current habits: {', '.join(context.get('active_habits', [])) or 'Starting fresh'}
- Best streak: {context.get('top_habit')} ({max(context.get('streaks', {}).values()) if context.get('streaks') else 0} days)

Should they add this habit? Advise:
1. Yes/No - but with nuance
2. If yes: when to do it (morning/evening/stack with what)
3. If no: what to focus on first
4. The real game (what this habit unlocks)

Keep it under 140 words. Be honest, slightly edgy, supportive.
""",

            "general": f"""
You are a Price Pritchett quantum coach.

User message: {request['content']}

Their stats: Level {context.get('level')}, {len(context.get('active_habits', []))} active habits

Respond with coaching wisdom. Be specific, slightly edgy, warm, actionable.
Keep it under 150 words.
"""
        }
        
        prompt = prompts.get(request["type"], prompts["general"])
        
        # Call Gemini
        try:
            client = genai.GenerativeModel('gemini-pro')
            response = client.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Gemini error: {e}")
            # Fallback response
            return f"""I'm having trouble reaching the coaching AI right now. 

In the meantime: {request['content']}

Try again in a few minutes, or check back soon. Your XP Tracker coach will be ready to help!"""
    
    except Exception as e:
        print(f"Error generating coaching response: {e}")
        return f"I encountered an error while preparing your coaching. Please try again soon."


def format_coaching_email(response_body: str, request_type: str) -> str:
    """
    Format the coaching response as a professional email.
    """
    
    footer = f"""

---
💡 **Your XP Tracker AI Coach**

Powered by Google Gemini | Price Pritchett Quantum Coaching

**Keep the conversation going:**
- "Goal: [your new goal]"
- "Question: [your question]"
- "Review: [your milestone]"
- "Habit: [habit you're considering]"

Just reply with a new subject line to continue!

Questions? Check out the HOWTO_USE.md or email support.
"""
    
    return response_body + footer


def log_coaching_interaction(user_id: str, request: dict, response: str):
    """
    Store coaching interaction in history.
    """
    try:
        # Could store in database or JSON file
        coaching_log = {
            "user_id": user_id,
            "timestamp": request["timestamp"],
            "request_type": request["type"],
            "request_preview": request["content"][:100],
            "response_length": len(response)
        }
        # TODO: Store in notifications_history.json or coaching_history.json
        print(f"Logged coaching interaction: {coaching_log}")
    except Exception as e:
        print(f"Error logging coaching interaction: {e}")


# Main entry point
def process_coaching_email_request(user_id: str, subject: str, body: str) -> dict:
    """
    Main function to process a coaching email.
    
    Returns:
    {
        "success": bool,
        "response": str,
        "request_type": str
    }
    """
    
    try:
        # Parse request
        request = parse_coaching_email(subject, body)
        
        # Generate response
        response_body = generate_coaching_response(user_id, request)
        
        # Format as email
        formatted_response = format_coaching_email(response_body, request["type"])
        
        # Log interaction
        log_coaching_interaction(user_id, request, response_body)
        
        return {
            "success": True,
            "response": formatted_response,
            "request_type": request["type"]
        }
    
    except Exception as e:
        print(f"Error processing coaching email: {e}")
        return {
            "success": False,
            "response": f"Error processing your request: {str(e)}",
            "request_type": "error"
        }
```

### Step 2: Add Admin Panel UI

In `tracker.py`, add to **Admin** tab:

```python
# Around line 1380 (in Admin tab)

st.subheader("📧 Coaching Email Simulator")
st.write("Test the coaching email system without needing actual email")

col1, col2 = st.columns([1, 1])

with col1:
    coach_user = st.selectbox(
        "Select user to coach",
        options=list(storage.list_users()),
        key="coach_user_select"
    )

with col2:
    request_type = st.selectbox(
        "Request type",
        options=["Goal", "Question", "Review", "Habit", "General"],
        key="coach_request_type"
    )

# Dynamic input based on request type
if request_type == "Goal":
    subject = f"Goal: {st.text_input('What goal?', 'Build a morning routine', key='coach_goal')}"
    body = ""
elif request_type == "Question":
    subject = "Question: How do I improve?"
    body = st.text_area("Their question:", "How do I stay consistent?", key='coach_question')
elif request_type == "Review":
    subject = f"Review: {st.text_input('Their achievement:', 'Hit a 10-day streak', key='coach_review')}"
    body = ""
elif request_type == "Habit":
    subject = f"Habit: {st.text_input('Habit they consider:', 'Morning yoga', key='coach_habit')}"
    body = ""
else:
    subject = st.text_input("Subject:", key="coach_subject")
    body = st.text_area("Message:", key="coach_body")

if st.button("🤖 Generate Coaching Response"):
    from coaching_email_commands import process_coaching_email_request
    
    result = process_coaching_email_request(coach_user, subject, body)
    
    if result["success"]:
        st.success(f"✅ Coaching generated ({result['request_type']})")
        st.text_area("Response:", value=result["response"], height=200)
        
        # Option to actually send
        if st.checkbox("Send this as email"):
            user_data = storage.load_data(coach_user)
            user_email = user_data.get("email")
            
            if user_email:
                send_result = send_email(
                    user_email,
                    f"Re: {subject}",
                    result["response"]
                )
                if send_result:
                    st.success(f"📧 Email sent to {user_email}")
                else:
                    st.error("Failed to send email")
            else:
                st.error(f"No email on file for {coach_user}")
    else:
        st.error(f"❌ Error: {result['response']}")
```

### Step 3: Test It Out

1. **Test locally**:
```bash
streamlit run tracker.py
```

2. **Go to Admin tab** → **Coaching Email Simulator**

3. **Try a few scenarios**:
   - Goal: "Learn Spanish in 30 days"
   - Question: "How do I stay consistent?"
   - Review: "Hit a 10-day meditation streak!"

---

## 📧 Next: Email Integration (Zapier/Make)

Once the system works, you can connect real emails:

### Option A: Gmail + Zapier

```
Gmail (coach@yourapp.com)
    ↓
Zapier (watch for emails)
    ↓
Streamlit Cloud API
    ↓
process_coaching_email_request()
    ↓
Send reply email
```

### Option B: SendGrid Webhook

```
SendGrid (inbound email parsing)
    ↓
Webhook → Your app
    ↓
Generate coaching
    ↓
Send reply
```

---

## 🎯 Testing Scenarios

| Scenario | Input | Expected Output |
|----------|-------|-----------------|
| Goal setup | "Goal: Build a workout routine" | 3-4 habit suggestions + weekly targets |
| Consistency Q | "Question: I keep missing days. Why?" | Data-driven analysis + micro-actions |
| Achievement | "Review: 21-day streak!" | Celebration + next edge to play |
| Habit consideration | "Habit: Should I add journaling?" | Yes/no + when/how to stack it |

---

## 🚀 Timeline

- **Today**: Implement Phase 1 (2-3 hours)
- **Tomorrow**: Connect real email (1-2 hours)
- **This week**: Beta test with 2-3 users
- **Next week**: Move to Phase 2 (chat widget)

---

## 📊 Cost

- **Gemini API**: ~$0.01-0.05 per coaching email
- **Email**: Free (Gmail/SendGrid)
- **Storage**: Already included
- **Total**: ~$5-10/month for 100-200 users

---

## ✅ Checklist

- [ ] Create `coaching_email_commands.py`
- [ ] Add Admin UI to `tracker.py`
- [ ] Test all 5 request types locally
- [ ] Send test emails to yourself
- [ ] Connect real email (Zapier or SendGrid)
- [ ] Beta test with users

---

**Ready to build?** Let me know and I'll implement the full Phase 1!
