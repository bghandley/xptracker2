"""
Drip Email Campaign System
Automated onboarding and engagement emails for new users (first 30 days).
Generated using Gemini AI with context-aware messaging.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from storage import get_storage
from email_utils import send_email
from coaching_emails import generate_personalized_coaching


DRIP_HISTORY_FILE = "drip_campaign_history.json"

# Drip campaign schedule (days after signup, email template name)
DRIP_SCHEDULE = [
    (0, "welcome"),                  # Day 0: Welcome email
    (1, "getting_started"),          # Day 1: Getting started guide
    (3, "first_habits_tip"),         # Day 3: Tips for first habits
    (7, "week_1_check_in"),          # Day 7: Week 1 check-in
    (10, "momentum_building"),       # Day 10: Building momentum
    (14, "two_week_review"),         # Day 14: Two-week review
    (21, "three_week_milestone"),    # Day 21: Three-week milestone
    (28, "month_review"),            # Day 28: Month review
    (30, "next_steps"),              # Day 30: Next steps & advanced features
]


def load_drip_history() -> Dict[str, Dict]:
    """Load drip campaign history."""
    if not os.path.exists(DRIP_HISTORY_FILE):
        return {}
    
    try:
        with open(DRIP_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading drip history: {e}")
        return {}


def save_drip_history(history: Dict[str, Dict]) -> None:
    """Save drip campaign history."""
    try:
        with open(DRIP_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving drip history: {e}")


def get_user_signup_date(user_id: str) -> Optional[datetime]:
    """
    Get user signup date.
    Inferred from oldest completion date or falls back to today if new.
    """
    storage = get_storage()
    data = storage.load_data(user_id)
    
    if not data:
        return None
    
    # Get first completion date
    completions = data.get("completions", {})
    if completions:
        dates = sorted(completions.keys())
        try:
            return datetime.fromisoformat(dates[0])
        except:
            return datetime.now()
    
    return datetime.now()


def get_days_since_signup(user_id: str) -> int:
    """Get number of days since user signup."""
    signup_date = get_user_signup_date(user_id)
    if not signup_date:
        return 0
    
    return (datetime.now() - signup_date).days


def has_user_activity(user_id: str) -> Tuple[bool, int]:
    """
    Check if user has any habit activity.
    Returns: (has_activity, habit_count)
    """
    storage = get_storage()
    data = storage.load_data(user_id)
    
    if not data:
        return False, 0
    
    completions = data.get("completions", {})
    habits = data.get("habits", {})
    
    has_activity = len(completions) > 0
    return has_activity, len(habits)


def generate_welcome_email(user_id: str) -> Tuple[str, str]:
    """Generate personalized welcome email."""
    subject = "🎮 Welcome to XP Tracker! Your habit journey starts now"
    
    body = f"""
Hello {user_id}!

Welcome to XP Tracker! 🎮 

I'm excited to have you here. Over the next 30 days, I'll be sending you bite-sized coaching tips, momentum builders, and personalized encouragement to help you build unstoppable habits.

Here's what you're getting access to:

📊 **Gamified Tracking** — Every habit completion earns XP and builds streaks
🎯 **Smart Goals** — Organize habits by goals and track progress
📈 **Weekly Reports** — See your patterns, celebrate wins
🤖 **AI Coaching** — Get personalized tips based on YOUR data
🏆 **Leaderboard** — See how you stack up (friendly competition!)

**Your first micro-action**: Create 2-3 habits this week. Start stupidly small.
- Instead of "Exercise daily" → "10 min walk"
- Instead of "Read more" → "Read 1 page"
- Instead of "Meditate" → "5 min breathing"

Small wins compound into unstoppable momentum.

Tomorrow, I'll send you a quick getting-started guide with the exact steps.

You've got this,
Your XP Tracker Coach 🚀
"""
    
    return subject, body


def generate_getting_started_email(user_id: str) -> Tuple[str, str]:
    """Generate getting started guide email."""
    subject = "🚀 Getting Started: Create Your First Habits (2 min read)"
    
    body = f"""
Hey {user_id},

Quick 2-minute guide to get you rolling:

**Step 1: Create Your First Habits**
1. Go to "Daily Quests" tab
2. Click "+ Add Habit"
3. Name it (e.g., "Morning coffee ritual")
4. Set XP (start with 10 for easy wins)
5. Save

Pro tip: Start with 2-3 habits, not 10. You can add more later.

**Step 2: Mark Them Complete**
Each day, check off habits as you do them. You'll earn XP instantly.
- 3-day streak = 🔥 (see it build!)
- Week streak = 📈 (momentum!)
- Missed day = 💪 (we'll send encouragement)

**Step 3: Check Your Progress**
Go to "Reports" tab to see:
- Daily completion rate
- Habit patterns
- Top performing habits

**Your Mission for This Week**
✅ Create 2-3 starter habits
✅ Check them off daily (even small wins count!)
✅ Don't worry about perfection—consistency > perfection

In a few days, I'll send you momentum tips based on YOUR progress.

Keep crushing,
Coach 🎯
"""
    
    return subject, body


def generate_first_habits_tip_email(user_id: str) -> Tuple[str, str]:
    """Generate tips for first habits based on user activity."""
    has_activity, habit_count = has_user_activity(user_id)
    
    if has_activity:
        subject = "💪 You're Off to a Great Start! Here's How to Keep Momentum"
        body = f"""
Hey {user_id}!

I see you've already created {habit_count} habit(s) and started tracking! 🔥

That's exactly how momentum builds—one small action at a time.

Here's what's working for people like you:

**The 3-Habit Stack**
Most high-achievers start with:
1. One health habit (exercise, sleep, meditation)
2. One learning habit (reading, course, practice)
3. One personal habit (journaling, creative time)

This covers mind, body, and soul. 

**Pro Tips for Week 1**
✅ Do habits at the SAME TIME each day (builds automaticity)
✅ Link habits to existing routines (after coffee, before bed)
✅ Celebrate small wins (check marks ARE wins!)
❌ Don't add new habits until you have 2 weeks consistency

**You're on Day 3** — The crucial phase is NOW. Most people quit here.

What's your biggest temptation to skip a habit? (Usually it's "I'm too busy")

Next week I'll share the exact anti-quit system that works.

Stay in the arena,
Coach 🏹
"""
    else:
        subject = "👋 Let's Get You Started! Simple First Habit"
        body = f"""
Hey {user_id}!

I noticed you haven't added habits yet. No judgment—this is where most people hesitate.

Here's the secret: the first habit doesn't have to be perfect. It just has to be done.

**Pick ONE tiny habit to start:**

Option 1: Health
- 5 min walk
- Drink 2L water
- Sleep by 11pm

Option 2: Mind
- Read 5 pages
- 10 min meditation
- Practice 15 min

Option 3: Skill
- 20 min coding/learning
- Practice instrument
- Write 100 words

That's IT. One habit. 

Then go to "Daily Quests" tab and create it.

Do it for 3 days straight. Just 3 days. See how you feel.

Most people are shocked at how good it feels to see "3-day streak" 🔥

I'm rooting for you,
Coach 💪
"""
    
    return subject, body


def generate_week1_email(user_id: str) -> Tuple[str, str]:
    """Generate week 1 check-in email with data insights."""
    subject = "📈 Week 1 Check-In: You're Building Something Real"
    
    storage = get_storage()
    data = storage.load_data(user_id)
    
    has_activity, habit_count = has_user_activity(user_id)
    
    if has_activity:
        completions = data.get("completions", {})
        total_completions = sum(len(v) for v in completions.values())
        completion_rate = round((total_completions / max(habit_count, 1) / 7) * 100) if habit_count > 0 else 0
        
        body = f"""
Hey {user_id}!

**Week 1 Results** 🎉

✅ Habits Created: {habit_count}
✅ Completions This Week: {total_completions}
✅ Completion Rate: {completion_rate}%

Here's what this means: You're already ahead of 90% of people who start this.

Most people quit after day 1. You didn't.

**Why This Matters**
Every habit completion is literally rewiring your brain. Day by day. No magic, just compound interest.

**Week 2 Challenge**
Increase your completion rate by 10%. If you were at {completion_rate}%, aim for {min(completion_rate + 10, 100)}%.

(Don't add new habits—just maintain and deepen what you have.)

**Real Talk**
Week 2 is where it gets real. The initial excitement fades. Motivation dips. This is NORMAL.

What separates people who succeed:
1. They expect the dip (you now do!)
2. They have a system (XP Tracker IS your system)
3. They focus on the streak, not the perfection

Keep going,
Coach 🚀
"""
    else:
        body = f"""
Hey {user_id}!

Week 1 is done. You've got XP Tracker set up.

Now comes the hard part: actually using it. 😊

Here's the thing—I can send you 100 motivational emails, but the real motivation comes from ONE successful week.

**Your Challenge This Week**
Pick ONE habit. Do it 3 days in a row. 

Doesn't matter if it's "Drink water" or "10 min walk." 

Just pick something. Do it. See the streak grow.

Once you get that "7-day streak" feeling, you'll be hooked.

Let me know when you've got that first streak going. Seriously.

Ready to go,
Coach 💪
"""
    
    return subject, body


def generate_momentum_email(user_id: str) -> Tuple[str, str]:
    """Generate momentum building email at day 10."""
    subject = "🔥 Day 10: Momentum is Real. Here's How to Protect It"
    
    has_activity, habit_count = has_user_activity(user_id)
    
    body = f"""
Hey {user_id}!

You're at Day 10. 🎯

The research is clear: if you can make it to day 10, you're 80% likely to keep going.

Congratulations. You're in the 20% now.

**What to Expect Days 11-14**
- Habits start feeling automatic (YES!)
- You might get bored (normal sign of progress)
- Life will try to disrupt you (someone invites you out, you get sick, etc.)

This is where most people sabotage themselves.

**The Momentum Protection System**
✅ Stack habits on existing routines (coffee → meditation → shower)
✅ Celebrate weekly, not daily (big wins > small wins)
✅ Track completion rate, not just streaks
✅ Have a "relapse protocol" (missed 1 day? Get back on Day 2, not Week 2)

**Your Next Milestone**
Day 14 = 2 week streak. Biggest dopamine hit in early habit building.

After 14 days, habits stop being "motivation" and start being "identity."

You've got this,
Coach 🏹
"""
    
    return subject, body


def generate_two_week_email(user_id: str) -> Tuple[str, str]:
    """Generate 2-week review email."""
    subject = "🏆 You Made 2 Weeks! What Most People Never See"
    
    body = f"""
Hey {user_id}!

You've officially hit the 2-week mark. 🏆

Do you know what's crazy? Most people quit before this point.

You didn't.

**What This Means (Scientifically)**
- Your habits are becoming automatic (neuroplasticity!)
- You've rewired your dopamine system (doing > wanting)
- You've proven to yourself you can actually do this

That last one? That's the real win.

**14-Day Habit Wisdom**
✅ Habits that survived to 14 days = core values
❌ Habits that didn't = nice-to-haves (remove them!)

**Deep Dive: What to Do Now**
Review your habits:
- Which ones feel automatic? (KEEP, maybe increase difficulty)
- Which ones feel like a chore? (QUIT, no shame)
- Which ones get you excited? (ADD MORE LIKE THIS)

Quality > quantity. Always.

**Your Challenge for Weeks 3-4**
Keep what's working. Double down on your favorite habits.

You're not "building habits" anymore. You're becoming the person with these habits.

Slight shift. Huge impact.

See you at 30 days,
Coach 💪
"""
    
    return subject, body


def generate_three_week_email(user_id: str) -> Tuple[str, str]:
    """Generate 3-week milestone email."""
    subject = "🌟 Week 3: The Invisible Shift Is Happening"
    
    body = f"""
Hey {user_id}!

You're 3 weeks in. 🌟

Nobody's watching. Nobody's clapping. But something invisible is happening.

You're becoming someone who does the thing.

**The 21-Day Psychology**
Most people think willpower builds habits. Wrong.

Habits build IDENTITY. Identity drives behavior.

After 21 days:
- You're not "someone trying to meditate"
- You're becoming "someone who meditates"

See the difference?

Identity > motivation. Always.

**Proof Points**
- Meditation habit = "I'm someone who takes mental health seriously"
- Exercise habit = "I'm someone who respects my body"
- Reading habit = "I'm someone who grows"

Your habits aren't just routine. They're identity markers.

**This Matters Because**
When identity is locked in, quitting feels like betraying yourself.

That's when habits stick for life.

**Your Invitation**
Week 4 is the final week. By then, your habits should feel effortless.

If they don't, you're probably still relying on willpower instead of identity.

Which one are YOUR habits? (Willpower-based or identity-based?)

Think about it,
Coach 🔥
"""
    
    return subject, body


def generate_month_review_email(user_id: str) -> Tuple[str, str]:
    """Generate 30-day month review email."""
    subject = "🎊 30 Days Done. You're Now in the Top 1% of People"
    
    storage = get_storage()
    data = storage.load_data(user_id)
    
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    total_xp = sum(sum(h.get("xp", 0) for h in (completions.get(d, [])) if isinstance(h, str)) for d in completions)
    
    # Rough XP calculation
    total_completions = sum(len(v) for v in completions.values())
    
    body = f"""
Hey {user_id}!

🎊 **MONTH 1 COMPLETE** 🎊

You're officially in the top 1% of people who START a habit system AND stick with it for 30 days.

Let that sink in.

**Your 30-Day Stats**
✅ Habits Tracked: {len(habits)}
✅ Total Completions: {total_completions}
✅ Days Active: 30
✅ Consistency Score: {round((total_completions / (len(habits) * 30)) * 100) if habits else 0}%

**What You've Built**
You haven't just created a routine. You've:
- Rewired your neural pathways ✓
- Built identity around these habits ✓
- Proven you can commit to something ✓
- Created momentum that compounds for LIFE ✓

**The Next 30 Days**
Most people think Month 2 is easier. Wrong. It gets HARDER because the excitement is gone.

But here's the secret: that's when the real growth happens.

Months 1-3: You're building habit.
Months 3+: The habit is building you.

**Your Next Level**
- Increase difficulty (5 min → 20 min)
- Add strategic new habits (max 1 new habit per month)
- Track deeper metrics (quality, not just completion)
- Compete on the leaderboard (friendly!

You've got something special started here. Don't waste it.

Ready for Month 2?
Coach 🚀
"""
    
    return subject, body


def generate_next_steps_email(user_id: str) -> Tuple[str, str]:
    """Generate next steps email at day 30+."""
    subject = "🎓 Next Steps: Advanced Features to Amplify Your Progress"
    
    body = f"""
Hey {user_id}!

You've crushed Month 1. Now it's time to level up your game. 🎓

**You've Mastered:**
✅ Daily habit tracking
✅ Streak building
✅ XP system
✅ Weekly reports

**Now Try:**
📊 **Deep Analytics** — Spot patterns in your completions
🏆 **Leaderboard** — See how you rank vs others
🎯 **Goal Stacking** — Link habits to bigger life goals
📝 **Journal Integration** — Reflect on your why
🤖 **AI Coaching** — Get personalized advice based on YOUR data

**But Here's the Real Secret**
The system doesn't matter anymore. YOU matter.

You've proven you can do this. Now the question is: what do you want to become?

Habits are the tool. Identity is the prize.

Use XP Tracker not to feel good about yourself, but to become the person you're meant to be.

That's the real game.

Let's go,
Coach 🔥
"""
    
    return subject, body


def should_send_drip_email(user_id: str, email_type: str) -> bool:
    """Check if we should send a drip email."""
    storage = get_storage()
    
    # Check if user has email
    email = storage.get_user_email(user_id)
    if not email:
        return False
    
    # Check if notifications enabled
    if not storage.get_notifications_enabled(user_id):
        return False
    
    # Check if already sent
    history = load_drip_history()
    user_history = history.get(user_id, {})
    
    if user_history.get(email_type):
        return False
    
    return True


def get_pending_drip_emails(user_id: str) -> List[str]:
    """Get list of pending drip emails for user."""
    days_since_signup = get_days_since_signup(user_id)
    history = load_drip_history()
    user_history = history.get(user_id, {})
    
    pending = []
    for days, email_type in DRIP_SCHEDULE:
        # Email should be sent when days_since_signup >= days
        if days_since_signup >= days and not user_history.get(email_type):
            pending.append(email_type)
    
    return pending


def send_drip_email(user_id: str, email_type: str) -> bool:
    """Send a drip email and record it."""
    if not should_send_drip_email(user_id, email_type):
        return False
    
    # Generate email based on type
    email_generators = {
        "welcome": generate_welcome_email,
        "getting_started": generate_getting_started_email,
        "first_habits_tip": generate_first_habits_tip_email,
        "week_1_check_in": generate_week1_email,
        "momentum_building": generate_momentum_email,
        "two_week_review": generate_two_week_email,
        "three_week_milestone": generate_three_week_email,
        "month_review": generate_month_review_email,
        "next_steps": generate_next_steps_email,
    }
    
    if email_type not in email_generators:
        print(f"Unknown email type: {email_type}")
        return False
    
    try:
        subject, body = email_generators[email_type](user_id)
        
        storage = get_storage()
        email = storage.get_user_email(user_id)
        
        if not email:
            return False
        
        # Send email
        success = send_email(email, subject, body)
        
        if success:
            # Record in history
            history = load_drip_history()
            if user_id not in history:
                history[user_id] = {}
            
            history[user_id][email_type] = {
                "sent_at": datetime.now().isoformat(),
                "days_since_signup": get_days_since_signup(user_id)
            }
            
            save_drip_history(history)
            print(f"✅ Sent drip email '{email_type}' to {user_id}")
            return True
        else:
            print(f"❌ Failed to send drip email '{email_type}' to {user_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending drip email '{email_type}': {e}")
        return False


def process_drip_campaigns():
    """Process all pending drip emails for all users."""
    storage = get_storage()
    users = storage.list_users()
    
    sent_count = 0
    for user_id in users:
        pending = get_pending_drip_emails(user_id)
        for email_type in pending:
            if send_drip_email(user_id, email_type):
                sent_count += 1
    
    if sent_count > 0:
        print(f"✅ Sent {sent_count} drip campaign email(s)")
    
    return sent_count
