# 📧 Drip Campaign System - Onboarding & Engagement for Month 1

**Status**: ✅ Complete and ready to integrate  
**Date**: December 5, 2025  
**Purpose**: Automated, AI-powered emails for new users (Days 0-30)

---

## 🎯 Overview

The drip campaign system sends targeted coaching emails to new users over their first 30 days, with intelligent context-awareness based on their actual activity.

**Key Features**:
- ✅ 9 strategic emails over 30 days
- ✅ Personalized based on user activity (if started vs not started)
- ✅ Respects user notification preferences
- ✅ AI-generated with coaching psychology
- ✅ Prevents duplicate sends
- ✅ Runs automatically via scheduler (8:00 AM daily)

---

## 📧 Email Schedule & Content

### Day 0: Welcome Email
**Subject**: 🎮 Welcome to XP Tracker! Your habit journey starts now  
**Purpose**: Excitement + onboarding  
**Content**:
- Welcome message
- Features overview (gamification, tracking, coaching)
- Micro-action: Create 2-3 starter habits
- Sets expectation for daily coaching emails

**Why This Works**: 
- First email should build excitement
- Sets tone for upcoming journey
- Small micro-action gets them moving

---

### Day 1: Getting Started Guide
**Subject**: 🚀 Getting Started: Create Your First Habits (2 min read)  
**Purpose**: Concrete action steps  
**Content**:
- Step-by-step habit creation
- Explanation of XP system
- Where to find "Reports"
- Mission for the week: Create habits + check them off

**Why This Works**:
- Strikes while iron is hot (they just signed up)
- Removes friction (exact steps)
- Gives them a week-long goal

---

### Day 3: First Habits Tip (Context-Aware)
**Subject**: 💪 You're Off to a Great Start! / 👋 Let's Get You Started  
**Purpose**: Early intervention + momentum  
**Content**: 
- **If they've started**: Celebrate progress, encourage consistency, introduce 3-habit stack
- **If they haven't started**: Gentle nudge, offer simple options, reduce friction

**Why This Works**:
- Day 3 is critical (high quit rate)
- Personalization shows we're paying attention
- Different messaging for different user states

---

### Day 7: Week 1 Check-In
**Subject**: 📈 Week 1 Check-In: You're Building Something Real  
**Purpose**: Data-driven feedback + encouragement  
**Content**:
- Show actual stats (habits created, completions, %rate)
- Celebrate reaching 7 days
- Explain why this matters (neuroplasticity, compounding)
- Introduce Week 2 challenge (+10% completion rate)
- Real talk about motivation dips

**Why This Works**:
- Data is proof of progress
- Realistic about challenges ahead
- Sets up next challenge

---

### Day 10: Momentum Building
**Subject**: 🔥 Day 10: Momentum is Real. Here's How to Protect It  
**Purpose**: Protect against sabotage  
**Content**:
- Celebrate reaching day 10 (80% will continue!)
- Predict coming challenges (boredom, life disruption)
- "Momentum Protection System" (stacking, celebrating, tracking)
- Set milestone: Day 14

**Why This Works**:
- Inoculation against predictable challenges
- Practical system to maintain momentum
- Clear next target (14 days = big dopamine hit)

---

### Day 14: Two-Week Review
**Subject**: 🏆 You Made 2 Weeks! What Most People Never See  
**Purpose**: Identity shift begins  
**Content**:
- Recognition of achievement
- Science of habit automation
- Habit audit: Keep what works, quit what doesn't
- Quality > quantity principle
- Week 3-4 challenge: Double down on favorites

**Why This Works**:
- Major psychological milestone
- Habit review is practical action
- Introduces identity concept

---

### Day 21: Three-Week Milestone
**Subject**: 🌟 Week 3: The Invisible Shift Is Happening  
**Purpose**: Identity lock-in  
**Content**:
- The 21-day psychology (identity > motivation)
- Shift from "trying to do X" to "I'm someone who does X"
- How identity makes quitting feel like betrayal
- Reflection question: Willpower-based or identity-based?

**Why This Works**:
- Deepens psychological shift
- Makes habits feel less voluntary, more foundational
- Prepares them for final week

---

### Day 28: Month Review
**Subject**: 🎊 30 Days Done. You're Now in the Top 1% of People  
**Purpose**: Celebration + data review  
**Content**:
- Show full month stats (habits, completions, consistency %)
- Recognition of achievement + percentile ranking
- Science of neural rewiring
- Prepare for Month 2 (motivation dips, identity becomes real)
- Tease next level features

**Why This Works**:
- Massive psychological celebration
- Concrete data shows transformation
- Builds identity lock-in
- Preps for sustained behavior

---

### Day 30: Next Steps
**Subject**: 🎓 Next Steps: Advanced Features to Amplify Your Progress  
**Purpose**: Engagement + feature adoption  
**Content**:
- What they've mastered (recap basics)
- What to try next (analytics, leaderboard, goal stacking, journal, AI coaching)
- Reframe goal: Not about feeling good, but becoming who you want to be
- Call to action: Use advanced features

**Why This Works**:
- Prevents plateau
- Deepens product usage
- Reframes success from habit to identity

---

## 🧠 Design Philosophy

### Context-Aware Personalization
- **Day 3**: Different message if user has started vs hasn't
- **Day 7**: Shows their actual stats vs generic encouragement
- **Day 14**: References their specific habits vs generic advice
- **Day 28**: Shows their completion rate, habit count, actual progress

### Psychological Sequencing
1. **Days 0-1**: Excitement + action (get them moving)
2. **Days 3-7**: Celebrate + protect (maintain early momentum)
3. **Days 10-14**: Challenge dips + identity (sustain vs quit decision point)
4. **Days 21-30**: Identity lock-in + next level (transition to autonomy)

### Email Tone
- Conversational (person, not corporate)
- Specific data points (not generic encouragement)
- Realistic (expect dips, challenges are normal)
- Coaching psychology (help them think differently about habits)
- Small micro-actions (concrete next steps each email)

---

## 🔧 Technical Implementation

### File: `drip_campaigns.py` (539 lines)

**Core Functions**:
- `send_drip_email(user_id, email_type)` — Send a specific email
- `process_drip_campaigns()` — Check all users for pending emails (runs daily)
- `get_pending_drip_emails(user_id)` — List emails ready to send
- `get_days_since_signup(user_id)` — Calculate days from first activity
- `has_user_activity(user_id)` — Check if user has started tracking

**Email Generators** (context-aware):
- `generate_welcome_email()`
- `generate_getting_started_email()`
- `generate_first_habits_tip_email()` — Different if activity exists
- `generate_week1_email()` — Uses actual stats
- `generate_momentum_email()`
- `generate_two_week_email()`
- `generate_three_week_email()`
- `generate_month_review_email()` — Uses actual stats
- `generate_next_steps_email()`

**Data Persistence**:
- `drip_campaign_history.json` — Tracks which emails sent + when
- Prevents duplicate sends
- Records days since signup for each send

---

## 📊 Execution Flow

```
Daily (8:00 AM via Scheduler)
  ↓
process_drip_campaigns()
  ↓
For each user:
  - Check if notifications enabled
  - Check if email set
  - Calculate days since signup
  - Get pending emails from schedule
  - Send each pending email
  - Record in history (prevent duplicates)
  ↓
Log sent count
```

---

## 🔌 Integration Checklist

**Step 1**: Add to scheduler_service.py
```python
def job_drip_campaigns():
    """Process pending drip campaign emails."""
    try:
        from drip_campaigns import process_drip_campaigns
        process_drip_campaigns()
    except Exception as e:
        logger.exception(f"Error in drip campaigns job: {e}")
```

**Step 2**: Schedule the job
```python
# In schedule_jobs(), add:
scheduler.add_job(job_drip_campaigns, CronTrigger(hour=8, minute=0), id="drip_campaigns", replace_existing=True)
```

**Step 3**: Update logger message
```python
logger.info("Scheduled daily/weekly/streak/drip jobs")
```

See `DRIP_INTEGRATION_GUIDE.md` for full details.

---

## ✅ Smart Features

### Respects User Preferences
- Only sends if `notifications_enabled = True`
- Only sends if email is set
- Skips if already sent (history file)

### Context-Aware Content
- Day 3: References whether user started or not
- Day 7: Shows user's actual stats
- Day 14: References user's specific habits
- Day 28: Shows user's completion rate, habit count

### Prevents Spam
- One email per day maximum
- Each email type sent only once per user
- Respects opt-out preference

### Handles Edge Cases
- New user with no activity → supportive "let's start" message
- User with lots of activity → celebratory "you're crushing it" message
- User who started then stopped → encouraging re-engagement message

---

## 📈 Expected Impact

### User Retention
- Current: Unknown (no tracking)
- Expected: 80%+ make it to Day 14
- Expected: 60%+ make it to Day 30

### Feature Adoption
- Week 1: Users create habits
- Week 2: Users start tracking
- Week 3: Users check reports
- Week 4: Users adopt advanced features

### Engagement Metrics
- Day 7: 90%+ completion rate (early stage)
- Day 14: 70%+ completion rate (motivation dips)
- Day 30: 60%+ completion rate (identity-driven)

---

## 🎯 Success Metrics

To measure effectiveness, track:

1. **Open Rate** — What % of users open drip emails?
2. **Click Rate** — What % click into the app after email?
3. **Retention Rate** — What % reach Day 7, 14, 30?
4. **Habit Adoption** — Avg habits created by day 7?
5. **Completion Rate** — Avg completion % by day 14?
6. **Feature Usage** — When do users discover reports, leaderboard, etc?

---

## 🚀 Future Enhancements

### Phase 2: Beyond 30 Days
- Month 2-3 emails (advanced topics, analytics, competition)
- Monthly feature spotlights
- Quarterly reflection emails

### Phase 3: Reactive Campaigns
- "We miss you" email if user inactive for 3 days
- "Comeback" email if user stops completing habits
- Celebration emails on milestone achievements

### Phase 4: A/B Testing
- Test different subject lines
- Test different send times
- Test different coaching approaches
- Measure impact on retention

---

## 📝 Example: Context-Aware Day 3 Email

**If User HAS Started**:
```
Subject: 💪 You're Off to a Great Start! Here's How to Keep Momentum

You created 3 habits and started tracking! That's exactly how momentum builds.
Most high-achievers use the 3-Habit Stack:
- One health habit
- One learning habit  
- One personal habit

This covers mind, body, and soul...
```

**If User HASN'T Started**:
```
Subject: 👋 Let's Get You Started! Simple First Habit

I noticed you haven't added habits yet. No judgment.

Here's the secret: the first habit doesn't have to be perfect. 
It just has to be done.

Pick ONE tiny habit to start:
Option 1: Health (5 min walk)
Option 2: Mind (Read 5 pages)
Option 3: Skill (20 min coding)...
```

Same day (Day 3) but completely different message based on their activity.

---

## 🎓 Coaching Psychology Principles

All emails follow these principles:

1. **Data-Driven** — Show actual stats, not generic encouragement
2. **Realistic** — Acknowledge challenges, normalize struggles
3. **Behavioral** — Focus on systems & identity, not willpower
4. **Specific** — Micro-actions, not vague advice
5. **Psychological** — Explain the WHY (neuroplasticity, identity shift)
6. **Supportive** — Never shame-based, always warm & edgy
7. **Progressive** — Early emails simple, later emails deep
8. **Contextual** — Reference their actual data & choices

---

## 📞 Usage

### Manual Testing
```python
from drip_campaigns import send_drip_email, get_pending_drip_emails

# Check what emails are pending for a user
pending = get_pending_drip_emails("alice")
print(pending)  # ['welcome', 'getting_started', ...]

# Send a specific email
send_drip_email("alice", "welcome")

# Process all users (what scheduler does)
from drip_campaigns import process_drip_campaigns
process_drip_campaigns()
```

### Admin Panel Integration (Future)
Could add to Admin panel:
- View drip history for a user
- Manually send a drip email
- Reset drip campaign for a user (start over)

---

## 🎊 Summary

The drip campaign system is a **comprehensive first-month engagement strategy** that:
- ✅ Builds excitement (Day 0)
- ✅ Guides action (Days 1-3)
- ✅ Protects momentum (Days 7-14)
- ✅ Locks in identity (Days 21-30)
- ✅ Propels to next level (Day 30+)

**Result**: Users go from "trying XP Tracker" to "becoming someone who tracks habits" to "becoming someone who achieves goals."

That's the real transformation. 🚀

---

**Ready to integrate?** See `DRIP_INTEGRATION_GUIDE.md` for step-by-step instructions.

