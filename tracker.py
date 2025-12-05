import streamlit as st
import datetime
import time
import uuid
from typing import Dict, List, Any, Tuple
import pandas as pd
import plotly.express as px
from storage import get_storage

# --- Configuration & Constants ---
st.set_page_config(
    page_title="Level Up: XP Tracker",
    page_icon="⚔️",
    layout="wide"
)

XP_PER_LEVEL = 200

# Rank thresholds
RANKS = {
    1: "🌱 Novice",
    5: "🗡️ Squire",
    10: "🛡️ Knight",
    20: "👑 Champion",
    50: "🐉 Legend"
}

PRIORITY_MAP = {
    "High": "🔴",
    "Medium": "🟡",
    "Low": "🔵"
}

# --- Data Management Wrappers ---

def get_user_id():
    """Retrieve the current user ID from session state or default."""
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = "default"
    return st.session_state['user_id']

def load_data() -> Dict[str, Any]:
    return get_storage().load_data(get_user_id())

def save_data(data: Dict[str, Any]) -> None:
    get_storage().save_data(get_user_id(), data)

# --- Core Logic ---

BADGES_DEF = {
    "week_streak": {"name": "🔥 On Fire", "desc": "7 Day Streak on any habit", "icon": "🔥"},
    "month_streak": {"name": "⚡ Unstoppable", "desc": "30 Day Streak on any habit", "icon": "⚡"},
    "habit_master": {"name": "🧘 Grandmaster", "desc": "Reach Level 3 on a habit", "icon": "🧘"},
    "perfect_week": {"name": "🌟 Perfectionist", "desc": "7 Perfect Days", "icon": "🌟"},
    "task_force": {"name": "📋 Task Force", "desc": "Complete 10 Missions", "icon": "📋"},
    "veteran": {"name": "⚔️ Veteran", "desc": "Reach Level 10 Profile", "icon": "⚔️"}
}

def get_date_str(offset: int = 0) -> str:
    d = datetime.date.today() + datetime.timedelta(days=offset)
    return d.isoformat()

def get_week_range(week_offset: int = 0):
    """Get start and end dates for a week (Monday to Sunday)"""
    today = datetime.date.today()
    # Calculate the start of the current week (Monday)
    start_of_week = today - datetime.timedelta(days=today.weekday())
    # Apply week offset
    start_of_week += datetime.timedelta(weeks=week_offset)
    end_of_week = start_of_week + datetime.timedelta(days=6)
    return start_of_week, end_of_week

def calculate_stats(data: Dict[str, Any]):
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    tasks = data.get("tasks", [])
    
    habit_stats = {h: {'streak': 0, 'total_xp': 0, 'completions': 0, 'level': 1} for h in habits}
    global_xp = 0
    perfect_days_count = 0
    
    # Active habits count (approximation for perfect day logic)
    active_habits = [h for h, d in habits.items() if d.get("active", True)]
    active_count = len(active_habits)

    # 1. Historical XP Calculation (Habits)
    all_dates = sorted(list(completions.keys()))
    temp_streaks = {h: 0 for h in habits}
    
    if all_dates:
        start_date = datetime.date.fromisoformat(all_dates[0])
        end_date = datetime.date.today()
        delta = datetime.timedelta(days=1)
        
        current_d = start_date
        while current_d <= end_date:
            d_str = current_d.isoformat()
            days_completed = completions.get(d_str, [])
            
            # Count daily completions
            daily_habits_done = 0

            for habit, details in habits.items():
                base_xp = details['xp']
                
                if habit in days_completed:
                    daily_habits_done += 1
                    temp_streaks[habit] += 1
                    current_streak = temp_streaks[habit]
                    
                    # Track total completions
                    habit_stats[habit]['completions'] += 1

                    # Bonus: 10% per extra streak day
                    bonus_multiplier = 0.1 * (current_streak - 1)
                    if bonus_multiplier < 0: bonus_multiplier = 0
                    
                    earned_xp = int(base_xp * (1 + bonus_multiplier))
                    
                    habit_stats[habit]['total_xp'] += earned_xp
                    global_xp += earned_xp
                else:
                    temp_streaks[habit] = 0
            
            # Perfect Day Bonus (All active habits completed)
            # Logic: If at least 1 active habit exists, and completions >= active_count
            if active_count > 0 and daily_habits_done >= active_count:
                global_xp += 50 # Bonus XP for perfect day
                perfect_days_count += 1

            current_d += delta

    # 2. Display Streak Calculation (Backward check)
    today_str = get_date_str(0)
    for habit in habits:
        streak = 0
        check_date = datetime.date.today()
        while True:
            d_str = check_date.isoformat()
            completed_on_date = habit in completions.get(d_str, [])
            
            if completed_on_date:
                streak += 1
                check_date -= datetime.timedelta(days=1)
            else:
                if d_str == today_str:
                    check_date -= datetime.timedelta(days=1)
                    continue
                else:
                    break
        habit_stats[habit]['streak'] = streak

        # Calculate Level (Simple: Level up every 30 completions)
        habit_stats[habit]['level'] = 1 + (habit_stats[habit]['completions'] // 30)

    # 3. Task XP Calculation
    completed_tasks_count = 0
    for task in tasks:
        if task.get("status") == "Done":
            global_xp += task.get("xp", 0)
            completed_tasks_count += 1

    # 4. Badges Calculation
    earned_badges = []

    # Streak Badges
    max_streak = 0
    for h in habits:
        s = habit_stats[h]['streak']
        if s > max_streak: max_streak = s
        if habit_stats[h]['level'] >= 3:
            earned_badges.append("habit_master")

    if max_streak >= 7: earned_badges.append("week_streak")
    if max_streak >= 30: earned_badges.append("month_streak")

    if perfect_days_count >= 7: earned_badges.append("perfect_week")
    if completed_tasks_count >= 10: earned_badges.append("task_force")

    # Profile Level Badge (calculated outside, but we can check xp)
    # We'll handle veteran in the main loop or pass level in

    return global_xp, habit_stats, list(set(earned_badges))

def calculate_level(total_xp: int):
    level = 1 + (total_xp // XP_PER_LEVEL)
    xp_in_level = total_xp % XP_PER_LEVEL
    progress = xp_in_level / XP_PER_LEVEL
    return level, xp_in_level, progress

def get_rank(level: int) -> str:
    current_rank = "🌱 Novice"
    for threshold, title in sorted(RANKS.items()):
        if level >= threshold:
            current_rank = title
    return current_rank

def get_weekly_stats(data: Dict[str, Any], week_offset: int = 0):
    """Calculate stats for a specific week"""
    start_date, end_date = get_week_range(week_offset)
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    
    weekly_data = {}
    total_weekly_xp = 0
    
    # Initialize daily data
    daily_stats = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.isoformat()
        day_name = current_date.strftime("%a")
        daily_stats[date_str] = {"day_name": day_name, "xp": 0, "habits_completed": 0}
        current_date += datetime.timedelta(days=1)
    
    # Calculate daily XP from habits
    for habit, details in habits.items():
        if not details.get("active", True):
            continue
        base_xp = details['xp']
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.isoformat()
            if habit in completions.get(date_str, []):
                daily_stats[date_str]["xp"] += base_xp
                daily_stats[date_str]["habits_completed"] += 1
                total_weekly_xp += base_xp
            current_date += datetime.timedelta(days=1)
    
    # Calculate daily XP from tasks (completed during that week)
    tasks = data.get("tasks", [])
    for task in tasks:
        if task.get("status") == "Done" and task.get("completed_at"):
            completed_date = task["completed_at"][:10]
            if start_date.isoformat() <= completed_date <= end_date.isoformat():
                daily_stats[completed_date]["xp"] += task.get("xp", 0)
                total_weekly_xp += task.get("xp", 0)
    
    return daily_stats, total_weekly_xp, start_date, end_date

# --- UI Action Handlers ---

def add_goal(goal_name: str):
    data = load_data()
    if goal_name and goal_name not in data["goals"]:
        data["goals"].append(goal_name)
        save_data(data)
        st.success(f"Goal Added: {goal_name}")

def add_new_habit(name: str, xp: int, goal: str):
    data = load_data()
    if name and name not in data["habits"]:
        data["habits"][name] = {"xp": xp, "active": True, "goal": goal}
        save_data(data)
        st.success(f"Added habit: {name}")
    elif name in data["habits"]:
        st.warning("Habit already exists.")
    else:
        st.warning("Invalid name.")

def archive_habit(name: str):
    data = load_data()
    if name in data["habits"]:
        data["habits"][name]["active"] = False
        save_data(data)
        st.success(f"Archived: {name}")

def restore_habit(name: str):
    data = load_data()
    if name in data["habits"]:
        data["habits"][name]["active"] = True
        save_data(data)
        st.success(f"Restored: {name}")

def toggle_habit(habit_name: str, date_str: str):
    data = load_data()
    if date_str not in data["completions"]:
        data["completions"][date_str] = []
    
    current_list = data["completions"][date_str]
    if habit_name in current_list:
        current_list.remove(habit_name)
    else:
        current_list.append(habit_name)
        
    if not current_list:
        del data["completions"][date_str]
    save_data(data)

# --- Task Actions ---

def add_task(title, desc, xp, goal, priority, due_date):
    data = load_data()
    new_task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": desc,
        "xp": xp,
        "goal": goal,
        "priority": priority,
        "due_date": due_date.isoformat() if due_date else None,
        "status": "Todo",
        "created_at": datetime.datetime.now().isoformat()
    }
    data["tasks"].append(new_task)
    save_data(data)

def toggle_task_status(task_id, new_status):
    data = load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = new_status
            if new_status == "Done":
                task["completed_at"] = datetime.datetime.now().isoformat()
            break
    save_data(data)

def delete_task(task_id):
    data = load_data()
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    save_data(data)

# --- Journal Actions ---

def add_journal_section(section_name: str):
    data = load_data()
    if section_name and section_name not in data["journal_sections"]:
        data["journal_sections"].append(section_name)
        data["journal_entries"][section_name] = []
        save_data(data)
        st.success(f"Section Created: {section_name}")
    elif section_name in data["journal_sections"]:
        st.warning("Section already exists.")

def delete_journal_section(section_name: str):
    data = load_data()
    if section_name in data["journal_sections"]:
        data["journal_sections"].remove(section_name)
        del data["journal_entries"][section_name]
        save_data(data)
        st.success(f"Section Deleted: {section_name}")

def add_journal_entry(section_name: str, entry_text: str):
    data = load_data()
    if section_name in data["journal_sections"]:
        new_entry = {
            "id": str(uuid.uuid4()),
            "date": datetime.datetime.now().isoformat(),
            "text": entry_text
        }
        data["journal_entries"][section_name].append(new_entry)
        save_data(data)
        st.success("Entry saved!")

def delete_journal_entry(section_name: str, entry_id: str):
    data = load_data()
    if section_name in data["journal_entries"]:
        data["journal_entries"][section_name] = [
            e for e in data["journal_entries"][section_name] if e["id"] != entry_id
        ]
        save_data(data)

def export_data_to_csv(data: Dict[str, Any]):
    """Export tracking data to CSV format"""
    output = []
    
    # Habits Summary
    output.append("HABITS SUMMARY\n")
    output.append("Habit Name,XP Value,Active,Goal\n")
    for habit_name, details in data["habits"].items():
        active = "Yes" if details.get("active", True) else "No"
        goal = details.get("goal", "General")
        output.append(f"{habit_name},{details['xp']},{active},{goal}\n")
    
    output.append("\n")
    
    # Completions
    output.append("DAILY COMPLETIONS\n")
    output.append("Date,Habits Completed\n")
    for date_str in sorted(data["completions"].keys()):
        habits_list = "; ".join(data["completions"][date_str])
        output.append(f"{date_str},{habits_list}\n")
    
    output.append("\n")
    
    # Tasks
    output.append("TASKS\n")
    output.append("Title,Goal,Priority,XP,Status,Due Date,Created Date\n")
    for task in data["tasks"]:
        created = task.get("created_at", "")[:10]
        due = task.get("due_date", "")
        title = task['title'].replace(",", ";")  # Escape commas in title
        output.append(f"{title},{task.get('goal', 'General')},{task.get('priority', 'Low')},{task.get('xp', 0)},{task['status']},{due},{created}\n")
    
    return "".join(output)

# --- Main App Layout ---

def main():
    # --- Login / User Selection ---
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = "default"

    with st.sidebar:
        st.title("👤 User Profile")
        user_input = st.text_input("Username (Enter to switch)", value=st.session_state['user_id'])
        if user_input != st.session_state['user_id']:
            st.session_state['user_id'] = user_input
            st.rerun()
        st.divider()

    data = load_data()
    today_str = get_date_str(0)
    
    global_xp, habit_stats, earned_badges = calculate_stats(data)
    current_level, xp_in_level, level_progress = calculate_level(global_xp)
    current_rank = get_rank(current_level)

    if current_level >= 10 and "veteran" not in earned_badges:
        earned_badges.append("veteran")

    # --- Celebration Logic ---
    if 'previous_level' not in st.session_state:
        st.session_state['previous_level'] = current_level
    
    if current_level > st.session_state['previous_level']:
        st.balloons()
        st.toast(f"🎉 LEVEL UP! You are now Level {current_level}!", icon="🆙")
        st.session_state['previous_level'] = current_level
        time.sleep(1)

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Guild Management")
        
        tab_goals, tab_add, tab_manage = st.tabs(["Goals", "Add Quest", "Archive"])
        
        with tab_goals:
            with st.form("add_goal_form", clear_on_submit=True):
                st.subheader("Define a New Goal")
                new_goal = st.text_input("Goal Name (e.g., Get Fit)")
                if st.form_submit_button("Add Goal"):
                    add_goal(new_goal)
                    st.rerun()
            st.divider()
            st.write("Current Goals:")
            for g in data["goals"]:
                st.caption(f"• {g}")

        with tab_add:
            with st.form("add_habit_form", clear_on_submit=True):
                st.subheader("New Habit Quest")
                new_habit_name = st.text_input("Habit Name")
                new_habit_xp = st.number_input("XP Reward", min_value=1, value=10)
                habit_goal = st.selectbox("Link to Goal", options=data["goals"])
                
                submitted_add = st.form_submit_button("Create Habit")
                if submitted_add:
                    add_new_habit(new_habit_name, new_habit_xp, habit_goal)
                    st.rerun()

        with tab_manage:
            st.subheader("Habit Status")
            active_habits = [h for h, d in data["habits"].items() if d.get("active", True)]
            archived_habits = [h for h, d in data["habits"].items() if not d.get("active", True)]
            
            if active_habits:
                to_archive = st.selectbox("Archive Quest", options=active_habits)
                if st.button("Archive"):
                    archive_habit(to_archive)
                    st.rerun()
            
            st.divider()

            if archived_habits:
                to_restore = st.selectbox("Restore Quest", options=archived_habits)
                if st.button("Restore"):
                    restore_habit(to_restore)
                    st.rerun()

    # --- Header Stats ---
    st.title("🛡️ Hero's Journal")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Level {current_level}: {current_rank}")
        st.progress(level_progress)
        st.caption(f"XP: {xp_in_level} / {XP_PER_LEVEL} to next level (Total: {global_xp})")
    with col2:
        active_count = len([h for h, d in data["habits"].items() if d.get("active", True)])
        pending_tasks = len([t for t in data["tasks"] if t["status"] == "Todo"])
        st.metric("Active Quests", f"{active_count} Habits / {pending_tasks} Missions")

    st.markdown("---")

    # --- Tabs ---
    tab_habits, tab_tasks, tab_journal, tab_reports, tab_profile = st.tabs(["📅 Daily Quests", "📜 Mission Log", "📔 Journal", "📊 Reports", "🏅 Profile & Badges"])

    # === TAB 1: DAILY HABITS ===
    with tab_habits:
        st.header(f"Daily Quests: {today_str}")
        
        active_habits_dict = {k: v for k, v in data["habits"].items() if v.get("active", True)}

        if not active_habits_dict:
            st.info("No active quests! Check the sidebar to add new ones.")
        else:
            sorted_habits = sorted(active_habits_dict.items(), key=lambda x: x[1].get("goal", "General"))
            
            for habit_name, details in sorted_habits:
                is_completed = habit_name in data["completions"].get(today_str, [])
                current_streak = habit_stats[habit_name]['streak']
                total_habit_xp = habit_stats[habit_name]['total_xp']
                habit_level = habit_stats[habit_name]['level']
                habit_goal = details.get("goal", "General")
                
                c1, c2, c3, c4 = st.columns([0.5, 3, 1, 1])
                
                with c1:
                    checked = st.checkbox(
                        "Complete", 
                        value=is_completed, 
                        key=f"check_{habit_name}",
                        label_visibility="collapsed"
                    )
                    if checked != is_completed:
                        toggle_habit(habit_name, today_str)
                        st.rerun()

                with c2:
                    level_badge = f"<span style='background-color:#FFD700; color:#000; padding:1px 4px; border-radius:3px; font-weight:bold; font-size:0.75em'>Lvl {habit_level}</span>" if habit_level > 1 else ""
                    st.markdown(
                        f"**{habit_name}** {level_badge} <br> <span style='background-color:#f0f2f6; color:#31333f; padding:2px 6px; border-radius:4px; font-size:0.75em'>{habit_goal}</span> <span style='color:gray; font-size:0.8em'>({details['xp']} XP)</span>",
                        unsafe_allow_html=True
                    )
                    
                with c3:
                    if current_streak > 0:
                        st.markdown(f"🔥 **{current_streak}**")
                    else:
                        st.markdown("❄️ 0")
                        
                with c4:
                    st.markdown(f"⭐ {total_habit_xp}")
                    
                st.divider()
        
        # Summary Table for Habits
        with st.expander("📊 Full Habit Log"):
            summary_data = []
            for h in data["habits"]:
                is_active = data["habits"][h].get("active", True)
                status = "🟢 Active" if is_active else "🗄️ Archived"
                
                summary_data.append({
                    "Habit": h,
                    "Goal": data["habits"][h].get("goal", "General"),
                    "Level": habit_stats[h]['level'],
                    "Status": status,
                    "Base XP": data["habits"][h]["xp"],
                    "Current Streak": habit_stats[h]['streak'],
                    "Total XP": habit_stats[h]['total_xp'],
                    "Total Completions": habit_stats[h]['completions']
                })
            st.dataframe(summary_data, use_container_width=True)

    # === TAB 5: PROFILE & BADGES ===
    with tab_profile:
        st.header("🏅 Your Achievements")

        st.subheader("🏆 Badges")

        if not earned_badges:
            st.info("No badges yet. Keep training!")
        else:
            cols = st.columns(4)
            for i, badge_id in enumerate(earned_badges):
                if badge_id in BADGES_DEF:
                    badge = BADGES_DEF[badge_id]
                    with cols[i % 4]:
                        st.markdown(
                            f"""
                            <div style="text-align:center; border: 1px solid #ddd; padding: 10px; border-radius: 10px; background-color: #fafafa;">
                                <div style="font-size: 3em;">{badge['icon']}</div>
                                <div style="font-weight: bold; margin-top: 5px;">{badge['name']}</div>
                                <div style="font-size: 0.8em; color: gray;">{badge['desc']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        st.divider()
        st.subheader("📊 Career Stats")
        st.write(f"**Current Level:** {current_level}")
        st.write(f"**Total XP:** {global_xp}")
        st.write(f"**Rank:** {current_rank}")

    # === TAB 2: TASKS ===
    with tab_tasks:
        st.header("Mission Log")
        
        # Add Task Expander
        with st.expander("➕ Add New Mission"):
            with st.form("new_task_form", clear_on_submit=True):
                t_col1, t_col2 = st.columns(2)
                with t_col1:
                    task_title = st.text_input("Mission Title")
                    task_goal = st.selectbox("Goal", options=data["goals"], key="task_goal")
                    task_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
                with t_col2:
                    task_xp = st.number_input("XP Reward", value=50, step=10)
                    task_due = st.date_input("Due Date", value=None)
                    
                task_desc = st.text_area("Description (Optional)")
                
                if st.form_submit_button("Add Mission"):
                    if task_title:
                        add_task(task_title, task_desc, task_xp, task_goal, task_priority, task_due)
                        st.success("Mission Added!")
                        st.rerun()
                    else:
                        st.error("Title is required.")

        # Filter Tabs for Tasks
        t_tab_active, t_tab_done = st.tabs(["Active Missions", "Completed Missions"])
        
        # ACTIVE TASKS
        with t_tab_active:
            active_tasks = [t for t in data["tasks"] if t["status"] == "Todo"]
            if not active_tasks:
                st.info("No active missions. Good job... or get to work!")
            else:
                # Sort by Priority (High -> Low)
                priority_order = {"High": 0, "Medium": 1, "Low": 2}
                active_tasks.sort(key=lambda x: priority_order.get(x["priority"], 3))

                for task in active_tasks:
                    p_icon = PRIORITY_MAP.get(task["priority"], "🔵")
                    
                    with st.container():
                        tc1, tc2, tc3, tc4 = st.columns([0.5, 4, 1, 1])
                        with tc1:
                            if st.button("⬜", key=f"btn_done_{task['id']}", help="Mark Complete"):
                                toggle_task_status(task['id'], "Done")
                                st.rerun()
                        with tc2:
                            st.markdown(f"**{p_icon} {task['title']}**")
                            st.caption(f"{task['goal']} • Due: {task['due_date'] if task['due_date'] else 'No Date'}")
                        with tc3:
                            st.markdown(f"**+{task['xp']} XP**")
                        with tc4:
                             if st.button("🗑️", key=f"del_{task['id']}"):
                                 delete_task(task['id'])
                                 st.rerun()
                        
                        if task['description']:
                            with st.expander("Details"):
                                st.write(task['description'])
                        st.divider()

        # COMPLETED TASKS
        with t_tab_done:
            done_tasks = [t for t in data["tasks"] if t["status"] == "Done"]
            if not done_tasks:
                st.caption("No completed missions yet.")
            else:
                # Show most recent first
                done_tasks.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
                
                for task in done_tasks:
                    with st.container():
                        st.markdown(f"~~{task['title']}~~ (+{task['xp']} XP)")
                        st.caption(f"Completed: {task.get('completed_at', '')[:10]}")
                        if st.button("Undo", key=f"undo_{task['id']}"):
                            toggle_task_status(task['id'], "Todo")
                            st.rerun()
                        st.divider()

    # === TAB 3: JOURNAL ===
    with tab_journal:
        st.header("📔 Journal & Practice")
        
        # Create New Section
        with st.expander("➕ Create New Section"):
            with st.form("new_section_form", clear_on_submit=True):
                section_name = st.text_input("Section Name (e.g., Daily Reflections, Practice Questions)")
                if st.form_submit_button("Create Section"):
                    if section_name:
                        add_journal_section(section_name)
                        st.rerun()
                    else:
                        st.error("Section name is required.")
        
        # Display Sections
        if not data["journal_sections"]:
            st.info("No sections yet. Create one to get started!")
        else:
            for section in data["journal_sections"]:
                with st.expander(f"📝 {section}", expanded=False):
                    # Add Entry Form
                    with st.form(f"entry_form_{section}", clear_on_submit=True):
                        entry_text = st.text_area(
                            "Write your entry...",
                            placeholder="Share your thoughts, practice questions, or reflections...",
                            height=150,
                            key=f"textarea_{section}"
                        )
                        if st.form_submit_button("Save Entry", key=f"save_{section}"):
                            if entry_text:
                                add_journal_entry(section, entry_text)
                                st.rerun()
                            else:
                                st.error("Entry cannot be empty.")
                    
                    st.divider()
                    
                    # Display Entries
                    entries = data["journal_entries"].get(section, [])
                    if entries:
                        st.caption(f"📚 {len(entries)} entry(ies)")
                        for entry in reversed(entries):  # Most recent first
                            entry_date = entry["date"][:10]  # Extract date part
                            entry_time = entry["date"][11:16]  # Extract time part
                            
                            with st.container():
                                col_delete, col_date = st.columns([0.1, 0.9])
                                with col_delete:
                                    if st.button("🗑️", key=f"del_entry_{entry['id']}", help="Delete entry"):
                                        delete_journal_entry(section, entry["id"])
                                        st.rerun()
                                with col_date:
                                    st.caption(f"📅 {entry_date} at {entry_time}")
                                
                                st.write(entry["text"])
                                st.divider()
                    else:
                        st.caption("No entries yet. Start writing!")
                    
                    # Delete Section Button
                    if st.button(f"🗑️ Delete '{section}' Section", key=f"del_section_{section}"):
                        delete_journal_section(section)
                        st.rerun()

    # === TAB 4: REPORTS ===
    with tab_reports:
        st.header("📊 Weekly Reports & Analytics")
        
        # Week Navigation
        col_nav1, col_nav2, col_nav3 = st.columns([1, 2, 1])
        with col_nav1:
            if st.button("⬅️ Previous Week"):
                st.session_state.week_offset = st.session_state.get("week_offset", 0) - 1
                st.rerun()
        
        with col_nav2:
            week_offset = st.session_state.get("week_offset", 0)
            if st.button("📅 This Week"):
                st.session_state.week_offset = 0
                st.rerun()
            start, end = get_week_range(week_offset)
            st.markdown(f"<h3 style='text-align: center;'>Week of {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}</h3>", unsafe_allow_html=True)
        
        with col_nav3:
            if st.button("Next Week ➡️"):
                st.session_state.week_offset = st.session_state.get("week_offset", 0) + 1
                st.rerun()
        
        st.divider()
        
        # Get weekly stats
        week_offset = st.session_state.get("week_offset", 0)
        daily_stats, total_weekly_xp, week_start, week_end = get_weekly_stats(data, week_offset)
        
        # Summary Cards
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            st.metric("📈 Weekly XP", total_weekly_xp)
        with summary_col2:
            days_active = len([d for d in daily_stats.values() if d["xp"] > 0])
            st.metric("🔥 Active Days", f"{days_active}/7")
        with summary_col3:
            avg_daily_xp = total_weekly_xp // 7 if total_weekly_xp > 0 else 0
            st.metric("⭐ Avg Daily XP", avg_daily_xp)
        
        st.divider()
        
        # Charts
        chart_col1, chart_col2 = st.columns(2)
        
        # Daily XP Chart
        with chart_col1:
            chart_data = []
            for date_str in sorted(daily_stats.keys()):
                day_info = daily_stats[date_str]
                chart_data.append({
                    "Day": day_info["day_name"] + " " + date_str.split("-")[2],
                    "XP": day_info["xp"]
                })
            
            df_daily = pd.DataFrame(chart_data)
            fig_daily = px.bar(
                df_daily,
                x="Day",
                y="XP",
                title="Daily XP Earned",
                color="XP",
                color_continuous_scale="Viridis"
            )
            fig_daily.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        # Habits Completion Rate
        with chart_col2:
            active_habits = [h for h, d in data["habits"].items() if d.get("active", True)]
            if active_habits:
                habit_completions = {h: 0 for h in active_habits}
                for date_str in daily_stats.keys():
                    completed_habits = []
                    # Get habits completed on this date
                    if date_str in data["completions"]:
                        for h in data["completions"][date_str]:
                            if h in habit_completions:
                                habit_completions[h] += 1
                
                habit_chart_data = [{"Habit": h, "Completions": habit_completions[h]} for h in active_habits]
                df_habits = pd.DataFrame(habit_chart_data)
                fig_habits = px.bar(
                    df_habits,
                    x="Habit",
                    y="Completions",
                    title="Habit Completion Rate (This Week)",
                    color="Completions",
                    color_continuous_scale="RdYlGn"
                )
                fig_habits.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_habits, use_container_width=True)
        
        st.divider()
        
        # Detailed Daily Breakdown
        st.subheader("📅 Daily Breakdown")
        breakdown_data = []
        for date_str in sorted(daily_stats.keys()):
            day_info = daily_stats[date_str]
            breakdown_data.append({
                "Date": date_str,
                "Day": day_info["day_name"],
                "XP": day_info["xp"],
                "Habits Completed": day_info["habits_completed"]
            })
        
        df_breakdown = pd.DataFrame(breakdown_data)
        st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # Data Export
        st.subheader("📥 Export Data")
        export_col1, export_col2 = st.columns(2)
        
        with export_col1:
            csv_data = export_data_to_csv(data)
            st.download_button(
                label="📊 Download as CSV",
                data=csv_data,
                file_name=f"xp_tracker_export_{datetime.date.today().isoformat()}.csv",
                mime="text/csv"
            )
        
        with export_col2:
            json_data = json.dumps(data, indent=2)
            st.download_button(
                label="📋 Download as JSON",
                data=json_data,
                file_name=f"xp_tracker_export_{datetime.date.today().isoformat()}.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()
