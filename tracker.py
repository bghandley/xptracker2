import streamlit as st
import json
import datetime
import os
import time
import uuid
from typing import Dict, List, Any

# --- Configuration & Constants ---
st.set_page_config(
    page_title="Level Up: XP Tracker",
    page_icon="⚔️",
    layout="wide"
)

DATA_FILE = "xp_data.json"
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

# --- Data Management Functions ---

def load_data() -> Dict[str, Any]:
    """
    Loads data. Migrates old data to include 'tasks' and other fields.
    """
    default_data = {
        "goals": ["General"], 
        "habits": {},         
        "tasks": [],          # List of task dicts
        "completions": {}     
    }
    
    if not os.path.exists(DATA_FILE):
        save_data(default_data)
        return default_data
    
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            
            dirty = False
            
            # Ensure basic keys
            if "habits" not in data: data["habits"] = {}
            if "completions" not in data: data["completions"] = {}
            if "goals" not in data: 
                data["goals"] = ["General"]
                dirty = True
            if "tasks" not in data:
                data["tasks"] = []
                dirty = True
            
            # Ensure habits have 'active' status and 'goal' link
            for habit in data["habits"]:
                if "active" not in data["habits"][habit]:
                    data["habits"][habit]["active"] = True
                    dirty = True
                if "goal" not in data["habits"][habit]:
                    data["habits"][habit]["goal"] = "General"
                    dirty = True
            
            if dirty:
                save_data(data)
                
            return data
    except (json.JSONDecodeError, IOError):
        st.error("Error reading data file. Using empty default.")
        return default_data

def save_data(data: Dict[str, Any]) -> None:
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        st.error(f"Failed to save data: {e}")

# --- Core Logic ---

def get_date_str(offset: int = 0) -> str:
    d = datetime.date.today() + datetime.timedelta(days=offset)
    return d.isoformat()

def calculate_stats(data: Dict[str, Any]):
    habits = data.get("habits", {})
    completions = data.get("completions", {})
    tasks = data.get("tasks", [])
    
    habit_stats = {h: {'streak': 0, 'total_xp': 0} for h in habits}
    global_xp = 0
    
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
            
            for habit, details in habits.items():
                base_xp = details['xp']
                
                if habit in days_completed:
                    temp_streaks[habit] += 1
                    current_streak = temp_streaks[habit]
                    
                    # Bonus: 10% per extra streak day
                    bonus_multiplier = 0.1 * (current_streak - 1)
                    if bonus_multiplier < 0: bonus_multiplier = 0
                    
                    earned_xp = int(base_xp * (1 + bonus_multiplier))
                    
                    habit_stats[habit]['total_xp'] += earned_xp
                    global_xp += earned_xp
                else:
                    temp_streaks[habit] = 0
            
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

    # 3. Task XP Calculation
    for task in tasks:
        if task.get("status") == "Done":
            global_xp += task.get("xp", 0)

    return global_xp, habit_stats

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

# --- Main App Layout ---

def main():
    data = load_data()
    today_str = get_date_str(0)
    
    global_xp, habit_stats = calculate_stats(data)
    current_level, xp_in_level, level_progress = calculate_level(global_xp)
    current_rank = get_rank(current_level)

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
    tab_habits, tab_tasks = st.tabs(["📅 Daily Quests", "📜 Mission Log"])

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
                    st.markdown(
                        f"**{habit_name}** <span style='background-color:#f0f2f6; color:#31333f; padding:2px 6px; border-radius:4px; font-size:0.75em'>{habit_goal}</span> <span style='color:gray; font-size:0.8em'>({details['xp']} XP)</span>", 
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
                    "Status": status,
                    "Base XP": data["habits"][h]["xp"],
                    "Current Streak": habit_stats[h]['streak'],
                    "Total XP": habit_stats[h]['total_xp']
                })
            st.dataframe(summary_data, use_container_width=True)

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

if __name__ == "__main__":
    main()
