"""
Background Scheduler Service
Handles automated daily/weekly notifications via APScheduler.

This module avoids importing the main tracker runtime to prevent circular
imports. It uses the storage provider to load per-user data and computes
minimal statistics required for notifications.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except Exception:
    BackgroundScheduler = None
    CronTrigger = None

from storage import get_storage
from notifications import (
    notify_weekly_summary,
    notify_streak_milestone,
    notify_missed_day,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None


def compute_stats(data: Dict[str, Any]) -> Tuple[int, Dict[str, Dict[str, Any]], List[str]]:
    """Compute lightweight stats from a user's data.

    Returns (global_xp, habit_stats, earned_badges)
    """
    habits = data.get("habits", {})
    completions = data.get("completions", {})

    habit_stats = {h: {"streak": 0, "total_xp": 0, "completions": 0, "level": 1} for h in habits}
    global_xp = 0
    perfect_days_count = 0

    # Historical XP calculation
    all_dates = sorted(list(completions.keys()))
    temp_streaks = {h: 0 for h in habits}

    if all_dates:
        start_date = datetime.fromisoformat(all_dates[0]).date()
        end_date = datetime.today().date()
        delta_days = (end_date - start_date).days
        for i in range(delta_days + 1):
            d = (start_date + timedelta(days=i)).isoformat()
            days_completed = completions.get(d, [])

            for habit, details in habits.items():
                base_xp = details.get("xp", 10)
                if habit in days_completed:
                    temp_streaks[habit] += 1
                    current_streak = temp_streaks[habit]
                    habit_stats[habit]["completions"] += 1
                    bonus_multiplier = 0.1 * (current_streak - 1)
                    if bonus_multiplier < 0:
                        bonus_multiplier = 0
                    earned_xp = int(base_xp * (1 + bonus_multiplier))
                    habit_stats[habit]["total_xp"] += earned_xp
                    global_xp += earned_xp
                else:
                    temp_streaks[habit] = 0

            # perfect day check
            active_habit_names = {h for h, d in habits.items() if d.get("active", True)}
            completed_set = set(days_completed)
            if active_habit_names and active_habit_names.issubset(completed_set):
                global_xp += 50
                perfect_days_count += 1

    # display streak calculation (backward check)
    today = datetime.today().date()
    for habit in habits:
        streak = 0
        check_date = today
        while True:
            d_str = check_date.isoformat()
            if habit in completions.get(d_str, []):
                streak += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        habit_stats[habit]["streak"] = streak
        habit_stats[habit]["level"] = 1 + (habit_stats[habit]["completions"] // 30)

    # badges (simple derivation)
    earned_badges = []
    max_streak = max((habit_stats[h]["streak"] for h in habit_stats), default=0)
    if max_streak >= 7:
        earned_badges.append("week_streak")
    if max_streak >= 30:
        earned_badges.append("month_streak")
    if any(hs["level"] >= 3 for hs in habit_stats.values()):
        earned_badges.append("habit_master")
    if perfect_days_count >= 7:
        earned_badges.append("perfect_week")

    return global_xp, habit_stats, list(set(earned_badges))


def get_scheduler():
    """Get or create the background scheduler."""
    global _scheduler
    if BackgroundScheduler is None:
        logger.warning("APScheduler not available. Scheduler disabled.")
        return None
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        logger.info("🎯 Background Scheduler Started")
    return _scheduler


def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("⏹️ Background Scheduler Stopped")


def job_weekly_summary():
    """Send weekly summary to all users."""
    logger.info("📊 Running weekly summary job...")
    storage = get_storage()
    users = storage.list_users() or []
    if not users:
        logger.info("No users to notify")
        return

    for user_id in users:
        try:
            user_email = storage.get_user_email(user_id)
            if not user_email:
                continue

            user_data = storage.load_data(user_id)
            global_xp, habit_stats, earned_badges = compute_stats(user_data)
            completed_count = sum(s.get("completions", 0) for s in habit_stats.values())
            total_habits = len(user_data.get("habits", {}))
            top_habit = None
            top_habit_completions = 0
            for h, s in habit_stats.items():
                if s.get("completions", 0) > top_habit_completions:
                    top_habit_completions = s.get("completions", 0)
                    top_habit = h

            notify_weekly_summary(user_id, completed_count, total_habits, global_xp, top_habit)
            logger.info(f"Weekly summary queued for {user_id}")
        except Exception as e:
            logger.error(f"Error preparing weekly summary for {user_id}: {e}")


def job_daily_reminder():
    """Daily reminder to users who haven't completed today's habits."""
    logger.info("⏰ Running daily reminder job...")
    storage = get_storage()
    users = storage.list_users() or []
    today_str = datetime.now().date().isoformat()

    for user_id in users:
        try:
            user_email = storage.get_user_email(user_id)
            if not user_email:
                continue

            user_data = storage.load_data(user_id)
            completed_today = set(user_data.get("completions", {}).get(today_str, []))
            active_habits = {h: d for h, d in user_data.get("habits", {}).items() if d.get("active", True)}
            incomplete_habits = [h for h in active_habits.keys() if h not in completed_today]
            if incomplete_habits:
                # For now, we only log; a future improvement could send reminder emails.
                logger.info(f"User {user_id} has {len(incomplete_habits)} incomplete habits today")
        except Exception as e:
            logger.error(f"Error in daily reminder for {user_id}: {e}")


def job_streak_checks():
    """Check for streak milestones and send celebrations."""
    logger.info("🔥 Running streak milestone checks...")
    storage = get_storage()
    users = storage.list_users() or []
    milestone_streaks = [5, 10, 20, 30, 50, 100]

    for user_id in users:
        try:
            user_email = storage.get_user_email(user_id)
            if not user_email:
                continue

            user_data = storage.load_data(user_id)
            global_xp, habit_stats, earned_badges = compute_stats(user_data)

            for habit_name, stats in habit_stats.items():
                current_streak = stats.get("streak", 0)
                if current_streak in milestone_streaks:
                    habit_xp = user_data.get("habits", {}).get(habit_name, {}).get("xp", 10)
                    notify_streak_milestone(user_id, habit_name, current_streak, habit_xp)
                    logger.info(f"Streak milestone: {user_id} {habit_name} -> {current_streak}")
        except Exception as e:
            logger.error(f"Error checking streaks for {user_id}: {e}")


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
        logger.info("Scheduled daily/weekly/streak jobs")


def init_scheduler():
    """Initialize scheduler and schedule jobs."""
    scheduler = get_scheduler()
    if scheduler is None:
        return None
    schedule_jobs()
    return scheduler


def get_scheduler_status():
    global _scheduler
    if _scheduler is None:
        return {"status": "⏹️ Stopped", "jobs": []}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({"id": job.id, "next_run": str(job.next_run_time)})
    return {"status": "🟢 Running" if _scheduler.running else "⏹️ Stopped", "jobs": jobs}
