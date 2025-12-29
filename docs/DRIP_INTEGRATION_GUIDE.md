# Integration Guide: Adding Drip Campaigns to Scheduler

## Summary
Drip campaigns have been created in `drip_campaigns.py`. Follow these steps to integrate with the scheduler.

## Step 1: Update scheduler_service.py

Add this function before `schedule_jobs()` (around line 216):

```python
def job_drip_campaigns():
    """Process pending drip campaign emails."""
    try:
        from drip_campaigns import process_drip_campaigns
        process_drip_campaigns()
    except Exception as e:
        logger.exception(f"Error in drip campaigns job: {e}")
```

## Step 2: Update schedule_jobs() function

In the `schedule_jobs()` function (around line 230), add this line with the other scheduler.add_job calls:

```python
scheduler.add_job(job_drip_campaigns, CronTrigger(hour=8, minute=0), id="drip_campaigns", replace_existing=True)
```

And update the logger message to include drip:
```python
logger.info("Scheduled daily/weekly/streak/drip jobs")
```

## Full Updated schedule_jobs() Function

```python
def schedule_jobs():
    """Schedule all automated notification jobs."""
    scheduler = get_scheduler()
    if scheduler is None:
        return

    # remove existing jobs
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass

    # daily reminder at 7:00
    if CronTrigger:
        scheduler.add_job(job_daily_reminder, CronTrigger(hour=7, minute=0), id="daily_reminder", replace_existing=True)
        # weekly summary Sunday 9:00
        scheduler.add_job(job_weekly_summary, CronTrigger(day_of_week=6, hour=9, minute=0), id="weekly_summary", replace_existing=True)
        # streak checks 6:00
        scheduler.add_job(job_streak_checks, CronTrigger(hour=6, minute=0), id="streak_checks", replace_existing=True)
        # drip campaigns 8:00 AM (check daily for pending emails)
        scheduler.add_job(job_drip_campaigns, CronTrigger(hour=8, minute=0), id="drip_campaigns", replace_existing=True)
        logger.info("Scheduled daily/weekly/streak/drip jobs")
```

## Step 3: Verify Integration

The system will automatically:
1. Check each user's signup date daily at 8:00 AM
2. Send Welcome email at Day 0
3. Send Getting Started at Day 1
4. Continue through the full 30-day drip schedule
5. Skip users without email or notification opt-in disabled

## Drip Email Schedule

- Day 0: Welcome email
- Day 1: Getting started guide
- Day 3: First habits tips
- Day 7: Week 1 check-in
- Day 10: Momentum building
- Day 14: Two-week review
- Day 21: Three-week milestone
- Day 28: Month review
- Day 30: Next steps

## Context-Aware Features

The system is smart about content:
- If user has activity, emails reference their progress
- If user hasn't started, emails encourage first steps
- All emails generated with Gemini AI context (if integrated later)
- Per-user personalization throughout

## Testing

To test manually:
```python
from drip_campaigns import send_drip_email, get_pending_drip_emails

# Check pending emails for a user
pending = get_pending_drip_emails("testuser")
print(pending)

# Send a specific email
send_drip_email("testuser", "welcome")
```

## Data Files

New file created:
- `drip_campaign_history.json` - Tracks which emails have been sent to each user (auto-created)

Existing integration with:
- `notifications.py` - Respects notification opt-in settings
- `storage.py` - Uses existing email and preferences
- `scheduler_service.py` - Runs via APScheduler daily
