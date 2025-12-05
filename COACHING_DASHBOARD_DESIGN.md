# 🎯 Interactive Coaching Dashboard - Design Document

**Status**: Design Phase (Alpha Consideration)  
**Date**: December 5, 2025  
**Goal**: Add conversational AI coaching directly in the app

---

## 📊 Problem Statement

Current state:
- ✅ Notifications are **event-triggered** (one-way emails)
- ❌ Users can't **ask questions** to coach
- ❌ No **guided goal setting** in-app
- ❌ No **real-time journaling prompts**
- ❌ No **habit recommendations** based on goals

Desired:
- 💬 Two-way conversation with AI coach
- 🎯 Goal setup wizard
- 📝 Smart journaling prompts
- 💡 Habit suggestions
- 🏆 Level-up achievement coaching

---

## 🎯 Three Approaches (Simple → Advanced)

### **Option 1: Email-First Coaching (Simplest - Alpha Ready)**

**How it works**:
1. User requests coaching via email
2. System automatically replies with advice
3. Works through existing email infrastructure

**Pros**:
- ✅ No UI changes needed
- ✅ Works on any email client
- ✅ Asynchronous (users get responses later)
- ✅ Easy to implement (1-2 hours)

**Cons**:
- ❌ Not real-time
- ❌ Requires email roundtrip

**Implementation**:
```python
# coaching_email_commands.py (NEW)
def process_coaching_request(user_email: str, question: str) -> str:
    """
    User emails: coaching-request@xptracker.app
    Subject: "Goal: Learn Spanish in 30 days"
    Body: "How do I break this into habits?"
    
    System replies with Gemini-generated advice
    """
    prompt = f"""
User's goal: {question}
User's current stats: [from database]

Generate a specific, actionable coaching response with:
1. 3 habit suggestions
2. Weekly milestones
3. Daily actions
4. Potential obstacles & solutions
"""
    return gemini_model.generate_content(prompt)
```

**Example flow**:
```
User emails:
  To: coach@xptracker.app
  Subject: "Help me build a morning routine"
  
System replies (within 5 mins):
  Subject: "Your Morning Routine Coaching Plan"
  
  "Here's what I'd build:
   1. 5-min meditation (builds discipline)
   2. 10-min reading (mental activation)
   3. Quick journal (clarity check)
   
   Week 1 target: Do all 3 on 3 days
   Week 2 target: Do all 3 on 5 days
   Week 3: Every day
   
   Biggest trap: Starting too ambitious
   Antidote: Do 1 habit for 5 days, then add next one"
```

---

### **Option 2: Chat Widget in Dashboard (Moderate - 4-6 hours)**

**How it works**:
1. Add a chatbot sidebar in Streamlit
2. User types questions
3. Gemini responds in real-time
4. Conversation history stored

**Pros**:
- ✅ Real-time interaction
- ✅ In-app (no email)
- ✅ Beautiful UX
- ✅ Conversation history

**Cons**:
- ⚠️ Requires UI changes
- ⚠️ Token usage (Gemini costs ~$0.01 per conversation)
- ⚠️ Can get off-topic

**Implementation Sketch**:
```python
# In tracker.py - new sidebar tab: 💬 Coach

import streamlit as st
import google.generativeai as genai

def coach_chat():
    st.subheader("💬 AI Coach")
    
    # Initialize session state for conversation
    if "coach_messages" not in st.session_state:
        st.session_state.coach_messages = []
    
    # Display conversation history
    for message in st.session_state.coach_messages:
        if message["role"] == "user":
            st.chat_message("user").write(message["content"])
        else:
            st.chat_message("assistant").write(message["content"])
    
    # User input
    user_input = st.chat_input("Ask me anything about your goals, habits, or progress...")
    
    if user_input:
        # Add user message
        st.session_state.coach_messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Get context
        user_data = storage.load_data(authenticated_user)
        context = {
            "current_level": user_data.get("level", 1),
            "total_xp": user_data.get("xp", 0),
            "habits": list(user_data.get("habits", {}).keys()),
            "streaks": {h: v.get("current_streak", 0) 
                       for h, v in user_data.get("habits", {}).items()}
        }
        
        # Generate response
        prompt = f"""
You are a Price Pritchett quantum coach. User context:
{json.dumps(context, indent=2)}

User question: {user_input}

Respond with:
- Specific, data-driven advice
- Action steps (not philosophy)
- Reference their actual progress where relevant
- Slightly provocative but supportive tone
"""
        
        client = genai.GenerativeModel('gemini-pro')
        response = client.generate_content(prompt)
        
        # Add assistant message
        st.session_state.coach_messages.append({
            "role": "assistant",
            "content": response.text
        })
        
        st.rerun()

# In sidebar
with st.sidebar:
    if authenticated_user and st.session_state.get("admin_authenticated"):
        if st.button("💬 Coach"):
            coach_chat()
```

**Example conversation**:
```
User: "I want to get better at Spanish but don't know how to start"

Coach: "Your current routine has 4 active habits with a 7-day meditation streak. 
Here's the move: Add 'Spanish Duolingo - 5 min' right after meditation. 
That's a 2-minute stack that compounds.

Week 1: Just 5 min daily. Week 2: Add 5-min conversation practice.

What's the real friction - motivation or consistency?"

User: "Consistency - I keep forgetting"

Coach: "That's honest. So the play isn't motivation, it's friction removal.
Stack it after meditation (your strongest habit). 
Set a phone reminder for 30 min before.
Track it in your 'Spanish' habit here.

If you miss 2 days, we pivot strategy. Deal?"
```

---

### **Option 3: Full Coaching Mode (Advanced - 8+ hours)**

**Features**:
- 🎯 Goal-setting wizard with sub-goal creation
- 📝 Smart journaling with AI prompts
- 💡 Habit recommendations (AI suggests habits based on goals)
- 🏆 Level-up celebrations with achievement coaching
- 📊 Weekly coaching reviews
- 🎮 Gamified coaching (badges for "coached habits")

**Pros**:
- ✅ Comprehensive coaching experience
- ✅ Guided workflows
- ✅ Highly personalized

**Cons**:
- ❌ Large implementation (multiple files)
- ❌ Complex state management
- ❌ Higher token usage

**Architecture**:
```
tracker.py
├── coach_dashboard.py (NEW)
│   ├── goal_wizard()
│   ├── smart_journaling()
│   ├── habit_recommender()
│   └── achievement_coaching()
├── coach_prompts.py (NEW)
│   └── All coaching conversation templates
└── coach_history.py (NEW)
    └── Store coaching interactions
```

---

## 🚀 Recommended Path for Alpha

### Phase 1: Email-First Coaching (Week 1)
**Effort**: 2-3 hours  
**Impact**: High (email is familiar)  
**Files**:
- `coaching_email_commands.py` (new)
- `email_utils.py` (update to handle replies)
- `notifications.py` (integrate with existing system)

### Phase 2: Chat Widget (Week 2)
**Effort**: 4-6 hours  
**Impact**: Very High (in-app is better UX)  
**Files**:
- `tracker.py` (add 💬 Coach tab)
- `coach_conversational.py` (new)

### Phase 3: Full Dashboard (Week 3+)
**Effort**: 8-12 hours  
**Impact**: High (but can iterate)  
**Files**:
- Multiple new modules

---

## 📝 Specific Use Cases

### Use Case 1: Goal Setup with Coaching

```
User clicks: "🎯 Set New Goal"

Coach: "What's your goal? Be specific (not 'get fit' but 'run a 5K in 3 months')"

User: "Master Python for data science in 6 months"

Coach: "Good. That's specific. Here's how I'd build it:

HABITS (do 2-3 daily):
1. Solve 1 LeetCode problem - 15 min (muscle memory)
2. Read 1 chapter of 'Python for Data Analysis' - 20 min (theory)
3. Build 1 small script - 30 min (application)

MILESTONES:
- Month 1: Write clean, readable code
- Month 2: Use pandas & numpy fluently
- Month 3: Build 1 data analysis project
- Months 4-6: Contribute to open-source

BIGGEST TRAP: Tutorial rabbit hole (endless watching, no building)
FIX: Build > learn > repeat

Ready to lock this in? I'll track your habits against this goal."
```

### Use Case 2: Journaling with Prompts

```
User clicks: "📝 Journal"

Coach (sees 7-day meditation streak): "You're in a flow state.
Write about:
1. What made today's habit stack work?
2. What edge are you not playing yet?
3. What's the smallest next evolution?"

User writes entry, saves

Coach (analyzes entry): "I see you're noticing the power of stacking.
Here's your next move: Layer in gratitude journaling.
Why? It amplifies the meditation benefits.
New habit suggestion: 'Gratitude - 3 min' right after meditation.

Want to add it?"
```

### Use Case 3: Level-Up with Coaching

```
User reaches Level 5

Coach (special celebration): "Level 5 🏆

You know what this means? You've proven you CAN do hard things.
Most people quit before Level 2.

Here's the inflection point: You're no longer in habit-building mode.
You're in optimization mode.

NEW CHALLENGE: Pick your 1 keystone habit (the one that makes others easier).
Make it unbreakable for 30 days. That's your Level 5 quest.

Which habit is it?"
```

### Use Case 4: Habit Suggestions

```
User created goals:
- "Learn Spanish"
- "Get fit"
- "Read more"

Coach: "I see your goals. Here's what I'd stack:

MORNING (15 min):
- Duolingo Spanish - 5 min
- Morning jog - 10 min

EVENING (20 min):
- Read - 20 min
- (Spanish reading counts as both 'Spanish' and 'Read')

Why this stack?
- Exercise energizes your day
- Spanish before sleep = better retention
- Reading is your wind-down

This keeps you focused. Too many habits = failure mode.

Launch these 3 for 2 weeks before adding more?"
```

---

## 🛠️ Implementation - Phase 1 (Email-First, Simplest)

### Step 1: Email Command Parser

```python
# coaching_email_commands.py (NEW)

def parse_coaching_email(subject: str, body: str, user_id: str) -> dict:
    """
    Parse coaching request email.
    
    Format examples:
    - Subject: "Goal: Learn Spanish in 30 days"
    - Subject: "Question: How do I build a morning routine?"
    - Subject: "Review: I hit 5 days, what now?"
    """
    
    request_type = None
    content = None
    
    if subject.lower().startswith("goal:"):
        request_type = "goal_setup"
        content = subject.replace("Goal:", "").strip()
    elif subject.lower().startswith("question:"):
        request_type = "question"
        content = body
    elif subject.lower().startswith("review:"):
        request_type = "achievement"
        content = subject.replace("Review:", "").strip()
    else:
        request_type = "general"
        content = f"{subject}\n{body}"
    
    return {
        "type": request_type,
        "content": content,
        "user_id": user_id,
        "timestamp": datetime.now()
    }


def generate_coaching_response(request: dict) -> str:
    """
    Generate Gemini coaching response based on request type.
    """
    
    user_data = storage.load_data(request["user_id"])
    context = {
        "level": user_data.get("level", 1),
        "xp": user_data.get("xp", 0),
        "habits": list(user_data.get("habits", {}).keys()),
        "streaks": {h: v.get("current_streak", 0) 
                   for h, v in user_data.get("habits", {}).items()}
    }
    
    prompts = {
        "goal_setup": f"""
User wants to: {request["content"]}

Current context:
{json.dumps(context, indent=2)}

Generate a Price Pritchett quantum coaching response:
1. Break their goal into 3-4 specific habits
2. Give weekly progression targets
3. Identify the biggest trap they'll hit
4. Give specific daily actions (not philosophy)
5. Ask a provocative but supportive question to start

Be concise (under 150 words). Slightly edgy but warm.
""",
        
        "question": f"""
User question: {request["content"]}

Their progress:
{json.dumps(context, indent=2)}

Give specific, actionable advice in 100 words max.
Reference their actual progress.
Price Pritchett tone (data-driven, slightly provocative).
""",
        
        "achievement": f"""
User milestone: {request["content"]}

Their stats:
{json.dumps(context, indent=2)}

Celebrate the win, then give them the NEXT edge they're not playing.
Slightly raise the bar. Make it feel like a dare, not a demand.
Keep it under 120 words.
"""
    }
    
    prompt = prompts.get(request["type"], prompts["question"])
    
    client = genai.GenerativeModel('gemini-pro')
    response = client.generate_content(prompt)
    
    return response.text


def send_coaching_reply(user_id: str, original_subject: str, response_body: str):
    """
    Send coaching response back via email.
    """
    user_data = storage.load_data(user_id)
    user_email = user_data.get("email")
    
    if not user_email:
        print(f"No email on file for {user_id}")
        return False
    
    subject = f"Re: {original_subject}"
    body = f"""
{response_body}

---
XP Tracker Coach
Powered by Google Gemini

Reply with a new subject line to continue the conversation:
- "Goal: [your goal]"
- "Question: [your question]"
- "Review: [your milestone]"
"""
    
    return send_email(user_email, subject, body)
```

### Step 2: Webhook to Process Incoming Emails

```python
# In email_utils.py (add this)

def process_coaching_email_webhook(email_data):
    """
    Webhook endpoint for incoming emails.
    
    Usage with Gmail:
    1. Set up Gmail forwarding to coaching@yourapp.com
    2. Use something like Zapier/Make to POST to:
       https://yourapp.streamlit.app/api/coaching-email
    """
    
    try:
        subject = email_data.get("subject")
        body = email_data.get("body")
        sender_email = email_data.get("from")
        
        # Find user by email
        user_id = find_user_by_email(sender_email)
        if not user_id:
            return {"error": "User not found"}
        
        # Parse request
        request = parse_coaching_email(subject, body, user_id)
        
        # Generate response
        response_body = generate_coaching_response(request)
        
        # Send reply
        success = send_coaching_reply(user_id, subject, response_body)
        
        # Store in coaching history
        coaching_history.append({
            "user_id": user_id,
            "request_type": request["type"],
            "timestamp": datetime.now(),
            "request": request["content"],
            "response": response_body,
            "sent": success
        })
        
        return {"status": "success", "response_sent": success}
    
    except Exception as e:
        print(f"Coaching email processing error: {e}")
        return {"error": str(e)}
```

### Step 3: Update Admin Panel

In `tracker.py`, add to Admin tab:

```python
# In Admin tab

st.subheader("📧 Coaching Email Commands")
st.info("""
Users can email coaching requests:
- Subject: "Goal: [what they want to achieve]"
- Subject: "Question: [their question]"
- Subject: "Review: [milestone they hit]"

System auto-replies with Gemini coaching.
""")

if st.button("🔄 Process Pending Coaching Emails"):
    # Connect to email inbox
    # Process new emails
    st.success("Checked for new coaching emails")
```

---

## 💰 Cost Analysis (Phase 1)

| Component | Cost/Month |
|-----------|-----------|
| Email forwarding | $0 (Gmail/Zapier free tier) |
| Gemini API | ~$1-5 (at alpha scale) |
| Streamlit Cloud | Free |
| **Total** | **~$1-5/month** |

---

## 🎯 Recommendation for Alpha

**Start with Phase 1 (Email-First Coaching)**:
- ✅ Simple to implement (2-3 hours)
- ✅ No UI changes needed
- ✅ Email is familiar to users
- ✅ Can iterate quickly
- ✅ Build toward chat widget later

**Then move to Phase 2 (Chat Widget)** when you're ready for in-app coaching.

---

## 📋 To Get Started

1. **Review this design** - Does it align with your vision?
2. **Choose a phase** - Email-first or jump to chat?
3. **I'll build Phase 1** - Takes ~2 hours to implement

What do you think? Want to go with email-first coaching?

---

**Design created**: December 5, 2025  
**Status**: Ready to implement  
**Complexity**: Phase 1 = Low, Phase 2 = Medium, Phase 3 = High
