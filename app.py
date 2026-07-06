# app.py - Gym Bro v7.0 (All tabs working + AI control, web search, form check)

import streamlit as st
import json
import random
import os
import shutil
from datetime import datetime, timedelta, date
from typing import Dict, List
import plotly.graph_objects as go
from openai import OpenAI
from tools import search_exercises, analyze_form, parse_program_payload, normalize_exercises

# ============================================
# GYM BRO CLASS
# ============================================

class GymBro:
    def __init__(self, username="default"):
        self.username = username
        self.data_dir = f"user_data/{username}"
        os.makedirs(self.data_dir, exist_ok=True)
        self.workouts = self._load_json("workouts.json", [])
        self.exercise_progress = self._load_json("progress.json", {})
        self.achievements = self._load_json("achievements.json", [])
        self.custom_exercises = self._load_json("custom_exercises.json", [])
        self.profile = self._load_json("profile.json", {})
        self.current_program = self._load_json("current_program.json", None)

    def _load_json(self, filename, default):
        path = os.path.join(self.data_dir, filename)
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return default

    def _save_json(self, filename, data):
        path = os.path.join(self.data_dir, filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def setup_profile(self, goals, experience, days_per_week, focus_areas, time_per_session):
        self.profile = {
            "goals": goals,
            "experience": experience,
            "days_per_week": days_per_week,
            "focus_areas": focus_areas,
            "time_per_session": time_per_session,
            "created": datetime.now().isoformat()
        }
        self._save_json("profile.json", self.profile)

    def generate_program(self):
        """Offline fallback program generator."""
        if not self.profile:
            return None
        days_map = {2: ["Monday", "Thursday"], 3: ["Monday", "Wednesday", "Friday"],
                    4: ["Monday", "Tuesday", "Thursday", "Friday"],
                    5: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
        days = days_map.get(self.profile['days_per_week'], ["Monday", "Wednesday", "Friday"])
        program = {"program_name": f"{self.profile['experience'].title()} {', '.join(self.profile['goals'])} Plan", "days": []}
        for i, d in enumerate(days):
            if i % 2 == 0:
                focus = "Upper Body"
                exercises = [{"name": "Bench Press", "sets": 3, "reps": "8-10", "notes": "Focus on control"},
                             {"name": "Barbell Row", "sets": 3, "reps": "8-10", "notes": "Squeeze at top"},
                             {"name": "Overhead Press", "sets": 3, "reps": "10-12", "notes": ""},
                             {"name": "Face Pulls", "sets": 3, "reps": "15-20", "notes": "Light, perfect form"}]
            else:
                focus = "Lower Body"
                exercises = [{"name": "Barbell Squat", "sets": 3, "reps": "8-10", "notes": "Depth over weight"},
                             {"name": "Romanian Deadlift", "sets": 3, "reps": "10-12", "notes": "Hamstring stretch"},
                             {"name": "Leg Press", "sets": 3, "reps": "12-15", "notes": "Constant tension"},
                             {"name": "Calf Raises", "sets": 4, "reps": "15-20", "notes": ""}]
            program["days"].append({"day": d, "focus": focus, "exercises": exercises})
        self.current_program = program
        self._save_json("current_program.json", program)
        return program

    def log_workout(self, exercises_data, energy, sleep, duration):
        workout = {
            "date": datetime.now().isoformat(),
            "exercises": exercises_data,
            "energy_level": energy,
            "sleep_quality": sleep,
            "duration_minutes": duration
        }
        self.workouts.append(workout)
        self._save_json("workouts.json", self.workouts)
        for ex in exercises_data:
            name = ex["name"]
            if name not in self.exercise_progress:
                self.exercise_progress[name] = []
            total_volume = sum(s["weight"] * s["reps"] for s in ex["sets"] if s["weight"] > 0)
            best_set = max(ex["sets"], key=lambda s: s["weight"] * (1 + s["reps"]/30)) if ex["sets"] else None
            estimated_1rm = best_set["weight"] * (1 + best_set["reps"]/30) if best_set and best_set["weight"] > 0 else 0
            self.exercise_progress[name].append({
                "date": datetime.now().isoformat(),
                "volume": total_volume,
                "estimated_1rm": round(estimated_1rm, 1)
            })
        self._save_json("progress.json", self.exercise_progress)
        new_prs = self._check_prs(exercises_data)
        return {
            "feedback": self._generate_feedback(workout),
            "new_prs": new_prs,
            "total_workouts": len(self.workouts)
        }

    def _check_prs(self, exercises_data):
        new_prs = []
        for ex in exercises_data:
            name = ex["name"]
            if name in self.exercise_progress and len(self.exercise_progress[name]) >= 2:
                current = max(s["weight"] * (1 + s["reps"]/30) for s in ex["sets"] if s["weight"] > 0)
                previous = max(e["estimated_1rm"] for e in self.exercise_progress[name][:-1]) if self.exercise_progress[name][:-1] else 0
                if previous > 0 and current > previous * 1.01:
                    improvement = round((current - previous)/previous * 100, 1)
                    new_prs.append({
                        "exercise": name,
                        "old_est_1rm": round(previous, 1),
                        "new_est_1rm": round(current, 1),
                        "improvement": improvement
                    })
                    self.achievements.append({
                        "type": "PR",
                        "exercise": name,
                        "date": datetime.now().isoformat(),
                        "improvement": improvement
                    })
        self._save_json("achievements.json", self.achievements)
        return new_prs

    def _generate_feedback(self, workout):
        total_volume = sum(sum(s["weight"] * s["reps"] for s in ex["sets"]) for ex in workout["exercises"])
        fb = []
        if total_volume > 10000:
            fb.append("Bro, you moved some SERIOUS weight today! 💪")
        elif total_volume > 5000:
            fb.append("Solid volume bro! Building that foundation! 🏗️")
        else:
            fb.append("Good work bro! Every rep counts! 🎯")
        if workout["energy_level"] >= 8:
            fb.append("Energy was HIGH today! ⚡")
        elif workout["energy_level"] >= 5:
            fb.append("Good energy bro! 👊")
        else:
            fb.append("You showed up despite low energy – mental toughness! 🧠")
        if workout["sleep_quality"] <= 5:
            fb.append("Get more sleep tonight bro, recovery is key! 😴")
        return " ".join(fb)

    def get_streak_info(self):
        if not self.workouts:
            return {"current_streak": 0, "longest_streak": 0, "weekly_consistency": 0}
        workout_dates = sorted({datetime.fromisoformat(w["date"]).date() for w in self.workouts}, reverse=True)
        today = date.today()
        cur = 0
        for d in workout_dates:
            if d == today - timedelta(days=cur):
                cur += 1
            else:
                break
        best = temp = 0
        all_dates = sorted(workout_dates)
        for i, d in enumerate(all_dates):
            if i == 0 or d == all_dates[i-1] + timedelta(days=1):
                temp += 1
                best = max(best, temp)
            else:
                temp = 1
        last_7 = [today - timedelta(days=i) for i in range(7)]
        week = sum(1 for d in last_7 if d in workout_dates)
        return {"current_streak": cur, "longest_streak": best, "weekly_consistency": week}

    def get_progress(self):
        if not self.exercise_progress:
            return None
        summary = {}
        for ex, hist in self.exercise_progress.items():
            if len(hist) > 0:
                last = hist[-1]["estimated_1rm"]
                first = hist[0]["estimated_1rm"] if len(hist) >= 2 else last
                change = round((last - first)/first*100, 1) if first > 0 else 0
                summary[ex] = {
                    "first_1rm": round(first, 1),
                    "current_1rm": round(last, 1),
                    "sessions": len(hist),
                    "change_percent": change,
                    "trend": "📈 Up" if change>0 else "📉 Down" if change<0 else "➡️ Same"
                }
        return summary

# ============================================
# STREAMLIT UI
# ============================================

st.set_page_config(page_title="Gym Bro", page_icon="💪", layout="wide")

# Custom CSS (unchanged beautiful theme)
st.markdown("""
<style>
    :root {
        --bg: #07111f; --panel: rgba(10,18,32,0.9); --panel-2: rgba(16,29,49,0.95);
        --accent: #ff6b35; --accent-2: #ffcf5c; --text: #f5f7fb; --muted: #9aa8bf;
        --border: rgba(255,255,255,0.08);
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #07111f 0%, #121c2d 45%, #1b2d4d 100%);
        color: var(--text);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1220 0%, #14233a 100%);
        border-right: 1px solid var(--border);
    }
    .block-container { padding-top: 1.2rem; max-width: 1400px; }
    .hero-box {
        background: linear-gradient(135deg, rgba(255,107,53,0.95), rgba(255,207,92,0.9));
        color: #07111f; border-radius: 24px; padding: 1.35rem 1.5rem; margin-bottom: 1rem;
        box-shadow: 0 14px 40px rgba(0,0,0,0.25);
    }
    .hero-box h1 { margin: 0; font-size: 2rem; }
    .section-card {
        background: var(--panel); border: 1px solid var(--border); border-radius: 18px;
        padding: 1rem; margin: 0.4rem 0 1rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }
    .streak-card {
        background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
        border-radius: 18px; padding: 1rem 0.5rem; margin: 0.3rem 0;
        border: 1px solid #333; text-align: center;
    }
    .streak-card h3 { margin: 0; font-size: 1.8rem; font-weight: 700; }
    .calendar-day {
        background: #1e1e1e; border-radius: 14px; padding: 0.6rem 0.3rem;
        margin: 2px; text-align: center; border: 1px solid #333; flex: 1 1 0; min-width: 32px;
    }
    .calendar-day.trained { border: 2px solid #FF4B4B; background: #2d1a1a; }
    .calendar-day.planned { border: 2px solid #4B9FFF; background: #1a1a2d; }
    .pr-badge {
        background: linear-gradient(90deg, var(--accent-2), var(--accent));
        color: #07111f; padding: 10px; border-radius: 12px; margin: 6px 0; font-weight: 700;
    }
    .stButton>button {
        border-radius: 999px; border: 0; padding: 0.55rem 1rem;
        background: linear-gradient(90deg, var(--accent), #ff8f5e);
        color: white; font-weight: 700; box-shadow: 0 8px 18px rgba(255,107,53,0.2);
    }
    .stButton>button:hover { transform: translateY(-1px); box-shadow: 0 10px 20px rgba(255,107,53,0.25); }
    [data-testid="stExpander"] {
        background: var(--panel-2); border: 1px solid var(--border); border-radius: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def get_existing_users():
    if not os.path.exists("user_data"):
        return []
    return sorted([d for d in os.listdir("user_data") if os.path.isdir(os.path.join("user_data", d))])

def delete_user_folder(username):
    folder = os.path.join("user_data", username)
    if os.path.exists(folder):
        shutil.rmtree(folder)
        return True
    return False

# --- Sidebar ---
with st.sidebar:
    st.title("👤 User")
    existing_users = get_existing_users()
    if "selected_user" not in st.session_state:
        st.session_state.selected_user = None
    if existing_users:
        opt = st.radio("Select or new user", ["Existing user", "New user"], horizontal=True)
        if opt == "Existing user":
            sel = st.selectbox("Choose your profile", existing_users)
            st.session_state.selected_user = sel
        else:
            new = st.text_input("Enter new username", placeholder="e.g. IronWarrior")
            if new:
                if new in existing_users:
                    st.warning("That user already exists.")
                else:
                    st.session_state.selected_user = new
    else:
        new = st.text_input("Enter your name", value="default")
        st.session_state.selected_user = new if new else "default"

    username = st.session_state.selected_user
    if username:
        if "gym_bro" not in st.session_state or st.session_state.get("current_user") != username:
            st.session_state.gym_bro = GymBro(username)
            st.session_state.current_user = username
            st.session_state.show_intro = True
            st.session_state.current_exercises = []
            st.session_state.chat_messages = []
            st.session_state.pending_program = None
            st.session_state.pending_program_text = None
            st.session_state.pending_program_error = None
            for i in range(5):
                if f"w_{i}" not in st.session_state:
                    st.session_state[f"w_{i}"] = 20.0
                if f"r_{i}" not in st.session_state:
                    st.session_state[f"r_{i}"] = 10
                if f"n_{i}" not in st.session_state:
                    st.session_state[f"n_{i}"] = ""

    gym_bro = st.session_state.gym_bro if username else None

    if username and gym_bro:
        st.markdown("---")
        if not gym_bro.profile:
            st.info("Set up your profile first!")
        else:
            streak = gym_bro.get_streak_info()
            col1,col2,col3 = st.columns(3)
            with col1:
                st.markdown(f'<div class="streak-card"><h3>🔥 {streak["current_streak"]}</h3><small>Streak</small></div>', unsafe_allow_html=True)
            with col2:
                st.markdown(f'<div class="streak-card"><h3>👑 {streak["longest_streak"]}</h3><small>Best</small></div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="streak-card"><h3>📅 {streak["weekly_consistency"]}/7</h3><small>This Week</small></div>', unsafe_allow_html=True)

        # Delete user
        if "delete_mode" not in st.session_state:
            st.session_state.delete_mode = False
        if not st.session_state.delete_mode:
            if st.button("🗑️ Delete this user"):
                st.session_state.delete_mode = True
                st.rerun()
        else:
            st.warning(f"Delete '{username}'? All data lost.")
            c1,c2 = st.columns(2)
            with c1:
                if st.button("Yes, delete"):
                    if delete_user_folder(username):
                        st.success("User deleted.")
                        del st.session_state.gym_bro
                        st.session_state.current_user = None
                        st.session_state.selected_user = None
                        st.session_state.current_exercises = []
                        st.session_state.chat_messages = []
                        st.session_state.pending_program = None
                        st.session_state.show_intro = True
                        st.session_state.delete_mode = False
                        st.rerun()
            with c2:
                if st.button("Cancel"):
                    st.session_state.delete_mode = False
                    st.rerun()

if not username or not gym_bro:
    st.stop()

# --- Main Content ---
st.markdown('<div class="hero-box"><h1>🏋️‍♂️ Gym Bro</h1><p>Your AI training partner – smarter than ever</p></div>', unsafe_allow_html=True)

# Profile setup wizard
if not gym_bro.profile:
    with st.form("profile"):
        st.subheader("Let's get to know you, bro! 💪")
        c1,c2 = st.columns(2)
        with c1:
            goals = st.multiselect("Main goals", ["Build muscle","Lose fat","Get stronger","Improve endurance","Tone up","General fitness"], default=["Build muscle"])
            experience = st.selectbox("Experience", ["Beginner","Intermediate","Advanced"])
            days = st.slider("Days per week", 2,6,4)
        with c2:
            focus = st.multiselect("Focus areas", ["Chest","Back","Legs","Shoulders","Arms","Core","Overall"], default=["Overall"])
            time = st.selectbox("Time per session", ["30 min","45 min","60 min","75 min","90 min"], index=2)
        if st.form_submit_button("🚀 Create My Program"):
            gym_bro.setup_profile(goals, experience, days, focus, time)
            try:
                from openai import OpenAI
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt = f"Create a {days}-day gym workout plan for a {experience} lifter. Goals: {goals}. Focus: {focus}. Session: {time}. Return ONLY JSON."
                resp = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7, max_tokens=1000
                )
                prog, _ = parse_program_payload(resp.choices[0].message.content)
                if prog:
                    gym_bro.current_program = prog
                    gym_bro._save_json("current_program.json", prog)
                else:
                    gym_bro.generate_program()
            except:
                gym_bro.generate_program()
            st.session_state.show_intro = False
            st.rerun()
    st.stop()

if st.session_state.get("show_intro", False):
    with st.chat_message("assistant", avatar="💪"):
        st.markdown(f"### Yo {username}! Your {gym_bro.profile['days_per_week']}-day split is ready. Let's crush it! 💪")
    if st.button("Let's Go! 🚀", use_container_width=True, type="primary"):
        st.session_state.show_intro = False
        st.rerun()
    st.stop()

# ============================================
# TABS
# ============================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📅 Calendar", "💪 Log Workout", "📊 Progress", "🎯 My Program", "🤖 AI Chat", "📸 Form Check"])

# --- TAB 1: CALENDAR ---
with tab1:
    st.header("Your Training Calendar")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    days_of_week = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    cols = st.columns(7)
    workout_dates = {datetime.fromisoformat(w["date"]).date() for w in gym_bro.workouts}
    planned_days = set()
    if gym_bro.current_program:
        for d in gym_bro.current_program["days"]:
            day_name = d["day"]
            idx = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].index(day_name)
            planned_days.add(week_start + timedelta(days=idx))
    for i, col in enumerate(cols):
        day = week_start + timedelta(days=i)
        is_trained = day in workout_dates
        is_planned = day in planned_days
        class_name = "calendar-day"
        if is_trained: class_name += " trained"
        elif is_planned and day >= today: class_name += " planned"
        with col:
            st.markdown(f'<div class="{class_name}"><strong>{days_of_week[i]}</strong><span>{day.day}</span><br>{"✅" if is_trained else "📋" if is_planned and day >= today else ""}</div>', unsafe_allow_html=True)
    st.caption("✅ Trained   📋 Planned")
    st.markdown("---")
    st.subheader("Today's Session")
    if gym_bro.current_program:
        today_name = today.strftime("%A")
        today_prog = next((d for d in gym_bro.current_program["days"] if d["day"] == today_name), None)
        if today_prog:
            st.success(f"🎯 **{today_prog['focus']}** day!")
            for ex in today_prog["exercises"]:
                st.write(f"• **{ex.get('name','')}** – {ex.get('sets','?')}×{ex.get('reps','?')} {('('+ex.get('notes','')+')') if ex.get('notes') else ''}")
            if st.button("Log This Workout", type="primary"):
                st.session_state.current_exercises = []
                for ex in today_prog["exercises"]:
                    sets = [{"weight": 20.0, "reps": 10, "notes": ex.get('notes','')} for _ in range(ex.get('sets',3))]
                    st.session_state.current_exercises.append({"name": ex['name'], "sets": sets})
                st.rerun()
        else:
            st.info("Rest day or nothing planned. Enjoy the recovery, bro! 🛌")
    else:
        st.info("No program yet. Generate one in My Program tab.")

# --- TAB 2: LOG WORKOUT ---
with tab2:
    st.header("Log Today's Workout")
    col1,col2,col3 = st.columns(3)
    with col1: energy = st.slider("⚡ Energy", 1,10,7)
    with col2: sleep = st.slider("😴 Sleep", 1,10,7)
    with col3: duration = st.number_input("⏱️ Minutes", 15,180,45)

    st.markdown("---")
    st.subheader("Add Exercise")
    common = [
        "Barbell Squat","Deadlift","Bench Press","Overhead Press",
        "Barbell Row","Pull-ups","Lat Pulldowns","Dumbbell Press",
        "Lateral Raises","Bicep Curls","Tricep Pushdowns","Leg Press",
        "Romanian Deadlift","Face Pulls","Planks","Lunges",
        "Calf Raises","Dips","Push-ups"
    ]
    all_ex = common + gym_bro.custom_exercises
    mode = st.radio("Select or type your own", ["📋 Choose from list", "✏️ Type custom"], horizontal=True)
    if mode.startswith("📋"):
        exercise_name = st.selectbox("Pick exercise", all_ex)
    else:
        exercise_name = st.text_input("Exercise name", placeholder="e.g., Bulgarian Split Squat")
        if exercise_name and exercise_name not in gym_bro.custom_exercises:
            if st.button("➕ Save custom exercise"):
                gym_bro.custom_exercises.append(exercise_name)
                gym_bro._save_json("custom_exercises.json", gym_bro.custom_exercises)
                st.success(f"'{exercise_name}' saved!")

    num_sets = st.selectbox("Number of sets", [1,2,3,4,5], index=2)
    sets_data = []
    col1,col2,col3 = st.columns(3)
    with col1: w0 = st.number_input("Set 1 Weight (kg)", 0.0,500.0,st.session_state.w_0, key="w_0")
    with col2: r0 = st.number_input("Set 1 Reps", 1,30,st.session_state.r_0, key="r_0")
    with col3: n0 = st.text_input("Set 1 Notes", st.session_state.n_0, key="n_0")
    sets_data.append({"weight":w0,"reps":r0,"notes":n0})

    if num_sets > 1:
        if st.button("⬇️ Apply Set 1 to all", use_container_width=True):
            for i in range(1,num_sets):
                st.session_state[f"w_{i}"] = w0
                st.session_state[f"r_{i}"] = r0
                st.session_state[f"n_{i}"] = n0
            st.rerun()

    for i in range(1,num_sets):
        c1,c2,c3 = st.columns(3)
        with c1: weight = st.number_input(f"Set {i+1} Weight", 0.0,500.0,st.session_state[f"w_{i}"], key=f"w_{i}")
        with c2: reps = st.number_input(f"Set {i+1} Reps", 1,30,st.session_state[f"r_{i}"], key=f"r_{i}")
        with c3: notes = st.text_input(f"Set {i+1} Notes", st.session_state[f"n_{i}"], key=f"n_{i}")
        sets_data.append({"weight":weight,"reps":reps,"notes":notes})

    if st.button("➕ Add to workout", use_container_width=True):
        st.session_state.current_exercises.append({"name":exercise_name,"sets":sets_data})
        for i in range(5):
            st.session_state[f"w_{i}"] = 20.0
            st.session_state[f"r_{i}"] = 10
            st.session_state[f"n_{i}"] = ""
        st.rerun()

    if st.session_state.current_exercises:
        st.markdown("---")
        st.subheader("Today's Exercises")
        for i, ex in enumerate(st.session_state.current_exercises):
            with st.container():
                cols = st.columns([3,1])
                with cols[0]:
                    st.markdown(f"**{ex['name']}**")
                    for j,s in enumerate(ex["sets"]):
                        n = f" ({s['notes']})" if s.get('notes') else ""
                        st.caption(f"Set {j+1}: {s['weight']}kg × {s['reps']}{n}")
                with cols[1]:
                    if st.button("🗑️", key=f"del_{i}"):
                        st.session_state.current_exercises.pop(i)
                        st.rerun()
        if st.button("✅ Complete Workout", type="primary", use_container_width=True):
            result = gym_bro.log_workout(
                exercises_data=st.session_state.current_exercises,
                energy=energy, sleep=sleep, duration=duration
            )
            st.session_state.current_exercises = []
            st.balloons()
            st.success("Workout logged! 💪")
            with st.expander("📋 Summary", expanded=True):
                st.write(f"**Gym Bro says:** {result['feedback']}")
                st.write(f"Total workouts: {result['total_workouts']}")
                if result["new_prs"]:
                    for pr in result["new_prs"]:
                        st.markdown(f'<div class="pr-badge">{pr["exercise"]}: +{pr["improvement"]}%</div>', unsafe_allow_html=True)

# --- TAB 3: PROGRESS ---
with tab3:
    st.header("Your Progress")
    progress = gym_bro.get_progress()
    if not progress:
        st.info("Log some workouts to see progress!")
    else:
        for exercise, data in progress.items():
            with st.expander(f"📈 {exercise} ({data['sessions']} sessions)"):
                c1,c2,c3 = st.columns(3)
                c1.metric("Best 1RM", f"{data['current_1rm']}kg")
                c2.metric("First 1RM", f"{data['first_1rm']}kg")
                c3.metric("Change", f"{data['change_percent']}%", data['trend'])
                if exercise in gym_bro.exercise_progress:
                    hist = gym_bro.exercise_progress[exercise]
                    dates = [h["date"][:10] for h in hist]
                    rms = [h["estimated_1rm"] for h in hist]
                    fig = go.Figure(data=go.Scatter(x=dates, y=rms, mode='lines+markers'))
                    fig.update_layout(height=250, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True)
        if gym_bro.achievements:
            st.markdown("---")
            st.subheader("🏆 Achievements")
            for a in gym_bro.achievements[-5:]:
                st.write(f"- {a['exercise']}: +{a['improvement']}% on {a['date'][:10]}")

# --- TAB 4: MY PROGRAM ---
with tab4:
    st.header("Your Personalized Program")
    if not gym_bro.current_program:
        if st.button("Generate My Program", type="primary"):
            gym_bro.generate_program()
            st.rerun()
    else:
        prog = gym_bro.current_program
        st.subheader(prog.get("program_name", "My Program"))
        for d in prog["days"]:
            with st.expander(f"📅 {d['day']} – {d['focus']}"):
                for ex in d["exercises"]:
                    n = ex.get("notes","")
                    st.write(f"• **{ex['name']}** – {ex.get('sets','?')}×{ex.get('reps','?')} {f'({n})' if n else ''}")
        if st.button("🔄 Regenerate Program"):
            gym_bro.generate_program()
            st.rerun()

# --- TAB 5: AI CHAT (powered by GPT-4 function calling) ---
with tab5:
    st.header("💬 Chat with Gym Bro AI")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="💪" if msg["role"]=="assistant" else None):
            st.markdown(msg["content"])

    functions = [
        {
            "name": "create_program",
            "description": "Create or update the user's workout program. Provide complete JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_json": {"type": "string", "description": "Full program JSON string"}
                },
                "required": ["program_json"]
            }
        },
        {
            "name": "log_todays_workout",
            "description": "Log a completed workout for the current day.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercises": {"type": "string", "description": "JSON list of exercises with sets, reps, weights, notes"}
                },
                "required": ["exercises"]
            }
        },
        {
            "name": "search_web",
            "description": "Search the internet for exercise tips, best movements for a muscle, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    ]

    if prompt := st.chat_input("Ask Gym Bro..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.spinner("Gym Bro is thinking..."):
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                system_context = f"You are Gym Bro, a helpful gym coach. User: {username}. "
                if gym_bro.current_program:
                    system_context += f"Current program: {json.dumps(gym_bro.current_program)}. "
                messages = [{"role": "system", "content": system_context}]
                messages.extend(st.session_state.chat_messages[-6:])
                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages,
                    functions=functions,
                    function_call="auto",
                    temperature=0.8,
                    max_tokens=1000
                )
                reply_msg = response.choices[0].message
                if reply_msg.function_call:
                    func_name = reply_msg.function_call.name
                    args = json.loads(reply_msg.function_call.arguments)
                    if func_name == "create_program":
                        prog, err = parse_program_payload(args["program_json"])
                        if prog:
                            gym_bro.current_program = prog
                            gym_bro._save_json("current_program.json", prog)
                            reply = "✅ Program updated! Check your calendar."
                        else:
                            reply = f"Couldn't update program: {err}"
                    elif func_name == "log_todays_workout":
                        exercises = json.loads(args["exercises"])
                        result = gym_bro.log_workout(exercises, 7, 7, 60)
                        reply = f"Workout logged! {result['feedback']}"
                    elif func_name == "search_web":
                        results = search_exercises(args["query"])
                        reply = f"Search results:\n{results}"
                    else:
                        reply = "Function not implemented."
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                else:
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply_msg.content})
            except Exception as e:
                st.session_state.chat_messages.append({"role": "assistant", "content": f"Error: {e}"})
            st.rerun()

# --- TAB 6: FORM CHECK ---
with tab6:
    st.header("📸 Upload a photo of your form")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="Your form", use_column_width=True)
        if st.button("Analyze my form"):
            with st.spinner("Analyzing..."):
                try:
                    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                    analysis = analyze_form(uploaded_file, client)
                    st.write(analysis)
                except Exception as e:
                    st.error(f"Form analysis failed: {e}")

st.markdown("---")
st.caption(f"Gym Bro v7.0 | User: {username} | We go jim! 🏋️")