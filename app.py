# app.py - Gym Bro v4.1 (AI chat programs now update calendar, syntax fixed)

import streamlit as st
import json
import random
import os
import shutil
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import plotly.graph_objects as go
import pandas as pd

# ============================================
# GYM BRO CLASS (now with profile & programs)
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
        """Generate a weekly program using AI (or offline logic) based on profile."""
        if not self.profile:
            return None

        # Try OpenAI first
        try:
            from openai import OpenAI
            if "OPENAI_API_KEY" in st.secrets:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt = f"""Create a {self.profile['days_per_week']}-day gym workout plan for a {self.profile['experience']} lifter.
Goals: {', '.join(self.profile['goals'])}.
Focus areas: {', '.join(self.profile['focus_areas'])}.
Session length: about {self.profile['time_per_session']} minutes.
Respond ONLY with valid JSON. Structure:
{{
  "program_name": "string",
  "days": [
    {{
      "day": "Monday",
      "focus": "string",
      "exercises": [
        {{"name": "string", "sets": 3, "reps": "8-10", "notes": "string"}}
      ]
    }}
  ]
}}"""
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=500
                )
                program = json.loads(response.choices[0].message.content)
                self.current_program = program
                self._save_json("current_program.json", program)
                return program
        except:
            pass

        # Offline fallback program
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

    def log_workout(self, exercises_data: List[Dict], energy: int, sleep: int, duration: int):
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
        feedback = []
        if total_volume > 10000:
            feedback.append("Bro, you moved some SERIOUS weight today! 💪")
        elif total_volume > 5000:
            feedback.append("Solid volume bro! Building that foundation! 🏗️")
        else:
            feedback.append("Good work bro! Every rep counts! 🎯")
        if workout["energy_level"] >= 8:
            feedback.append("Energy was HIGH today! Love to see it! ⚡")
        elif workout["energy_level"] >= 5:
            feedback.append("Good energy bro! You pushed through! 👊")
        else:
            feedback.append("Low energy but you still showed up. That's mental toughness bro! 🧠")
        if workout["sleep_quality"] <= 5:
            feedback.append("Try to get more sleep tonight bro, recovery is key! 😴")
        return " ".join(feedback)

    def get_streak_info(self):
        if not self.workouts:
            return {"current_streak": 0, "longest_streak": 0, "weekly_consistency": 0}
        workout_dates = sorted({datetime.fromisoformat(w["date"]).date() for w in self.workouts}, reverse=True)
        today = date.today()
        current_streak = 0
        for d in workout_dates:
            if d == today - timedelta(days=current_streak):
                current_streak += 1
            else:
                break
        longest = 0
        temp = 0
        all_dates = sorted(workout_dates)
        for i, d in enumerate(all_dates):
            if i == 0 or d == all_dates[i-1] + timedelta(days=1):
                temp += 1
                longest = max(longest, temp)
            else:
                temp = 1
        # Weekly consistency: days worked in last 7 days
        last_7 = [today - timedelta(days=i) for i in range(7)]
        days_worked = sum(1 for d in last_7 if d in workout_dates)
        return {
            "current_streak": current_streak,
            "longest_streak": longest,
            "weekly_consistency": days_worked
        }

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

    def ai_chat(self, user_message, conversation_history):
        last_workout_context = ""
        if self.workouts:
            last = self.workouts[-1]
            exercises = [f"{ex['name']} ({len(ex['sets'])} sets)" for ex in last["exercises"]]
            last_workout_context = (
                f"User's last workout: {len(exercises)} exercises – {', '.join(exercises)}. "
                f"Energy: {last['energy_level']}/10, Sleep: {last['sleep_quality']}/10, Duration: {last['duration_minutes']} min."
            )
        try:
            from openai import OpenAI
            if "OPENAI_API_KEY" in st.secrets:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                system_prompt = (
                    "You are Gym Bro, a supportive and knowledgeable gym coach. "
                    "You give advice on exercises, form, nutrition, motivation, and programming. "
                    "Speak like a friendly bro: use 'bro', emojis, and hype. "
                    "Be encouraging but honest. Keep responses under 150 words unless you are providing a program.\n"
                    f"{last_workout_context}\n"
                    "IMPORTANT: If the user asks you to create or update their workout program, you MUST respond with a valid JSON object wrapped in a code block like:\n"
                    "```json\n"
                    "{\n"
                    '  "program_name": "...",\n'
                    '  "days": [\n'
                    '    {"day": "Monday", "focus": "...", "exercises": [{"name": "...", "sets": 3, "reps": "8-10", "notes": "..."}]}\n'
                    "  ]\n"
                    "}\n"
                    "```\n"
                    "Do not include any other text outside the code block if you are providing the program."
                )
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(conversation_history[-6:])
                messages.append({"role": "user", "content": user_message})
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=500
                )
                return response.choices[0].message.content
        except:
            pass

        # Offline fallback
        msg = user_message.lower()
        if any(word in msg for word in ["squat", "bench", "deadlift", "form"]):
            return "Bro! Focus on form: keep your core tight, control the weight, and don't ego-lift. Slow and steady wins the gains! 🎯"
        elif any(word in msg for word in ["eat", "nutrition", "food", "protein"]):
            return "Eat big, eat clean! Protein is your best friend – aim for 1.6–2.2g per kg of bodyweight. Don't forget carbs for energy! 🍗🥗"
        elif any(word in msg for word in ["motivation", "lazy", "tired"]):
            return "Bro, even on days you don't feel like it – just show up. The hardest rep is walking through the door. You got this! 💪🔥"
        elif any(word in msg for word in ["program", "routine", "split"]):
            return "A solid PPL (Push/Pull/Legs) split is great for beginners. Train each muscle twice a week, 3–4 exercises per session, 3–4 sets of 8–12 reps. Consistency beats perfection! 🗓️"
        elif any(word in msg for word in ["sore", "pain", "rest"]):
            return "Soreness is normal, sharp pain isn't. Listen to your body, take an extra rest day if needed, and come back stronger. Recovery is part of training! 🛌"
        elif any(word in msg for word in ["cardio", "running", "fat"]):
            return "Cardio is great for heart health, but don't overdo it if you're trying to build muscle. 2–3 sessions of 20–30 min per week is plenty. Balance is key! 🏃"
        else:
            return f"Bro, I'm in offline mode. Ask me about form, nutrition, motivation, or programming – I've got you covered! 💪"

# ============================================
# STREAMLIT UI (v4.1)
# ============================================

st.set_page_config(page_title="Gym Bro", page_icon="💪", layout="wide")

# Custom CSS for beautiful, mobile-friendly design
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main .block-container {
        padding-top: 1rem;
    }
    .stButton>button {
        border-radius: 12px;
        background: linear-gradient(135deg, #FF4B4B, #FF6B6B);
        color: white;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #FF6B6B, #FF4B4B);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255,75,75,0.4);
    }
    .streak-card {
        background: linear-gradient(135deg, #1e1e1e, #2d2d2d);
        border-radius: 16px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        border: 1px solid #333;
    }
    .calendar-day {
        background: #1e1e1e;
        border-radius: 12px;
        padding: 0.8rem;
        margin: 0.3rem;
        text-align: center;
        border: 1px solid #333;
    }
    .calendar-day.trained {
        border: 2px solid #FF4B4B;
        background: #2d1a1a;
    }
    .calendar-day.planned {
        border: 2px solid #4B9FFF;
    }
    @media (max-width: 768px) {
        .streak-card {
            padding: 0.8rem;
        }
        .calendar-day {
            padding: 0.4rem;
            font-size: 0.8rem;
        }
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

# --- Sidebar: User Management ---
st.sidebar.title("👤 User")
existing_users = get_existing_users()

if "selected_user" not in st.session_state:
    st.session_state.selected_user = None

if existing_users:
    user_option = st.sidebar.radio("Select or new user", ["Existing user", "New user"], horizontal=True)
    if user_option == "Existing user":
        selected = st.sidebar.selectbox("Choose your profile", existing_users)
        st.session_state.selected_user = selected
    else:
        new_name = st.sidebar.text_input("Enter new username", placeholder="e.g. IronWarrior")
        if new_name:
            if new_name in existing_users:
                st.sidebar.warning("That user already exists. Switch to 'Existing user' to select it.")
            else:
                st.session_state.selected_user = new_name
else:
    new_name = st.sidebar.text_input("Enter your name", value="default")
    st.session_state.selected_user = new_name if new_name else "default"

username = st.session_state.selected_user

if username:
    if "gym_bro" not in st.session_state or st.session_state.get("current_user") != username:
        st.session_state.gym_bro = GymBro(username)
        st.session_state.current_user = username
        st.session_state.show_intro = True
        st.session_state.current_exercises = []
        st.session_state.chat_messages = []
        # Initialize set data session state keys
        for i in range(5):
            if f"w_{i}" not in st.session_state:
                st.session_state[f"w_{i}"] = 20.0
            if f"r_{i}" not in st.session_state:
                st.session_state[f"r_{i}"] = 10
            if f"n_{i}" not in st.session_state:
                st.session_state[f"n_{i}"] = ""

gym_bro = st.session_state.gym_bro

# Sidebar quick stats (streaks, etc.)
st.sidebar.markdown("---")
if not gym_bro.profile:
    st.sidebar.info("Set up your profile first!")
else:
    streak = gym_bro.get_streak_info()
    col1, col2, col3 = st.sidebar.columns(3)
    col1.metric("🔥 Streak", streak["current_streak"])
    col2.metric("👑 Best", streak["longest_streak"])
    col3.metric("📅 Week", f"{streak['weekly_consistency']}/7")
st.sidebar.markdown("---")

# Delete user (unchanged)
if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False
if not st.session_state.delete_mode:
    if st.sidebar.button("🗑️ Delete this user"):
        st.session_state.delete_mode = True
        st.rerun()
else:
    st.sidebar.warning(f"Delete '{username}'? All data will be lost.")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Yes, delete", type="primary"):
            if delete_user_folder(username):
                st.sidebar.success(f"User '{username}' deleted.")
                if st.session_state.current_user == username:
                    del st.session_state.gym_bro
                    st.session_state.current_user = None
                    st.session_state.selected_user = None
                    st.session_state.current_exercises = []
                    st.session_state.chat_messages = []
                    st.session_state.show_intro = True
                st.session_state.delete_mode = False
                st.rerun()
    with col2:
        if st.button("Cancel"):
            st.session_state.delete_mode = False
            st.rerun()

# --- Main Content ---
st.title("🏋️‍♂️ Gym Bro – Your AI Training Partner")

# Profile setup wizard (if no profile yet)
if not gym_bro.profile:
    with st.form("profile_setup"):
        st.subheader("Let's get to know you, bro! 💪")
        st.markdown("Help me build your perfect program.")
        col1, col2 = st.columns(2)
        with col1:
            goals = st.multiselect("What are your main goals?", ["Build muscle", "Lose fat", "Get stronger", "Improve endurance", "Tone up", "General fitness"], default=["Build muscle"])
            experience = st.selectbox("Experience level", ["Beginner", "Intermediate", "Advanced"])
            days_per_week = st.slider("How many days can you train per week?", 2, 6, 4)
        with col2:
            focus_areas = st.multiselect("Any areas you want to focus on?", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Overall"], default=["Overall"])
            time_per_session = st.selectbox("How long can you train per session?", ["30 min", "45 min", "60 min", "75 min", "90 min"], index=2)
        if st.form_submit_button("🚀 Create My Program", type="primary"):
            gym_bro.setup_profile(goals, experience, days_per_week, focus_areas, time_per_session)
            gym_bro.generate_program()
            st.session_state.show_intro = False
            st.rerun()
    st.stop()

# Intro screen after profile setup (first time)
if st.session_state.get("show_intro", False):
    with st.chat_message("assistant", avatar="💪"):
        greetings = [
            f"Yo {username}! Your program is ready! Let's crush those {', '.join(gym_bro.profile['goals'])} goals! 💪",
            f"Brooo! Welcome, {username}. I've crafted a {gym_bro.profile['days_per_week']}-day split for you. Ready to dominate? 🔥",
        ]
        st.markdown(f"### {random.choice(greetings)}")
    if st.button("Let's Go! 🚀", use_container_width=True, type="primary"):
        st.session_state.show_intro = False
        st.rerun()
    st.stop()

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Calendar", "💪 Log Workout", "📊 Progress", "🎯 My Program", "🤖 AI Chat"])

# --- TAB 1: CALENDAR & STREAKS ---
with tab1:
    st.header("Your Training Calendar")
    streak_info = gym_bro.get_streak_info()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="streak-card"><h3 style="margin:0">🔥 {streak_info["current_streak"]}</h3><small>Current Streak</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="streak-card"><h3 style="margin:0">👑 {streak_info["longest_streak"]}</h3><small>Longest Streak</small></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="streak-card"><h3 style="margin:0">📅 {streak_info["weekly_consistency"]}/7</h3><small>This Week</small></div>', unsafe_allow_html=True)

    st.markdown("---")
    # Weekly calendar view
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    cols = st.columns(7)
    workout_dates = {datetime.fromisoformat(w["date"]).date() for w in gym_bro.workouts}
    # Determine planned days from program
    planned_days = set()
    if gym_bro.current_program:
        for d in gym_bro.current_program["days"]:
            day_name = d["day"]
            day_idx = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].index(day_name)
            planned_days.add(week_start + timedelta(days=day_idx))

    for i, col in enumerate(cols):
        day = week_start + timedelta(days=i)
        is_trained = day in workout_dates
        is_planned = day in planned_days
        class_name = "calendar-day"
        if is_trained:
            class_name += " trained"
        elif is_planned and day >= today:
            class_name += " planned"
        with col:
            st.markdown(f'<div class="{class_name}"><strong>{days_of_week[i]}</strong><br>{day.day}<br>{"✅" if is_trained else "📋" if is_planned and day >= today else ""}</div>', unsafe_allow_html=True)
    st.caption("✅ = Trained   📋 = Planned")

    # Today's session
    st.markdown("---")
    st.subheader("Today's Planned Session")
    if gym_bro.current_program:
        today_name = today.strftime("%A")
        today_program = next((d for d in gym_bro.current_program["days"] if d["day"] == today_name), None)
        if today_program:
            st.success(f"🎯 **{today_program['focus']}** day!")
            for ex in today_program["exercises"]:
                sets = ex.get('sets', '?')
		reps = ex.get('reps', '?')
		notes = ex.get('notes', '')
		notes_str = f" ({notes})" if notes else ""
		st.write(f"• **{ex.get('name', 'Unknown')}** – {sets}×{reps}{notes_str}")
            if st.button("Log This Workout", type="primary"):
                # Pre-fill the workout tab
                st.session_state.current_exercises = []
                for ex in today_program["exercises"]:
                    sets = [{"weight": 20.0, "reps": 10, "notes": ex['notes']} for _ in range(ex['sets'])]
                    st.session_state.current_exercises.append({"name": ex['name'], "sets": sets})
                st.rerun()
        else:
            st.info("Rest day or no workout planned. Enjoy the recovery, bro! 🛌")
    else:
        st.info("No program generated yet. Go to 'My Program' tab to create one.")

# --- TAB 2: LOG WORKOUT ---
with tab2:
    st.header("Log Today's Workout")
    col1, col2, col3 = st.columns(3)
    with col1:
        energy = st.slider("⚡ Energy", 1,10,7)
    with col2:
        sleep = st.slider("😴 Sleep", 1,10,7)
    with col3:
        duration = st.number_input("⏱️ Minutes", 15,180,45)

    st.markdown("---")
    st.subheader("Add Exercise")

    common_exercises = [
        "Barbell Squat", "Deadlift", "Bench Press", "Overhead Press",
        "Barbell Row", "Pull-ups", "Lat Pulldowns", "Dumbbell Press",
        "Lateral Raises", "Bicep Curls", "Tricep Pushdowns", "Leg Press",
        "Romanian Deadlift", "Face Pulls", "Planks", "Lunges",
        "Calf Raises", "Dips", "Push-ups"
    ]
    all_exercises = common_exercises + gym_bro.custom_exercises
    exercise_mode = st.radio("Select or type your own", ["📋 Choose from list", "✏️ Type custom"], horizontal=True)
    if exercise_mode.startswith("📋"):
        exercise_name = st.selectbox("Pick exercise", all_exercises)
    else:
        exercise_name = st.text_input("Exercise name", placeholder="e.g., Bulgarian Split Squat")
        if exercise_name and exercise_name not in gym_bro.custom_exercises:
            if st.button("➕ Save custom exercise"):
                gym_bro.custom_exercises.append(exercise_name)
                gym_bro._save_json("custom_exercises.json", gym_bro.custom_exercises)
                st.success(f"'{exercise_name}' saved!")

    num_sets = st.selectbox("Number of sets", [1,2,3,4,5], index=2)
    sets_data = []

    # Set 1
    col1, col2, col3 = st.columns(3)
    with col1:
        w0 = st.number_input("Set 1 Weight (kg)", 0.0, 500.0, st.session_state.w_0, key="w_0")
    with col2:
        r0 = st.number_input("Set 1 Reps", 1, 30, st.session_state.r_0, key="r_0")
    with col3:
        n0 = st.text_input("Set 1 Notes", st.session_state.n_0, key="n_0")
    sets_data.append({"weight": w0, "reps": r0, "notes": n0})

    if num_sets > 1:
        if st.button("⬇️ Apply Set 1 values to all other sets", use_container_width=True):
            for i in range(1, num_sets):
                st.session_state[f"w_{i}"] = w0
                st.session_state[f"r_{i}"] = r0
                st.session_state[f"n_{i}"] = n0
            st.rerun()

    for i in range(1, num_sets):
        col1, col2, col3 = st.columns(3)
        with col1:
            weight = st.number_input(f"Set {i+1} Weight (kg)", 0.0, 500.0, st.session_state[f"w_{i}"], key=f"w_{i}")
        with col2:
            reps = st.number_input(f"Set {i+1} Reps", 1, 30, st.session_state[f"r_{i}"], key=f"r_{i}")
        with col3:
            notes = st.text_input(f"Set {i+1} Notes", st.session_state[f"n_{i}"], key=f"n_{i}")
        sets_data.append({"weight": weight, "reps": reps, "notes": notes})

    if st.button("➕ Add to workout", use_container_width=True):
        st.session_state.current_exercises.append({"name": exercise_name, "sets": sets_data})
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
                    for j, s in enumerate(ex["sets"]):
                        notes_str = f" ({s['notes']})" if s['notes'] else ""
                        st.caption(f"Set {j+1}: {s['weight']}kg × {s['reps']}{notes_str}")
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
                    st.markdown("### 🏆 NEW PRs!")
                    for pr in result["new_prs"]:
                        st.markdown(f"- {pr['exercise']}: +{pr['improvement']}% ({pr['old_est_1rm']} → {pr['new_est_1rm']}kg)")

# --- TAB 3: PROGRESS ---
with tab3:
    st.header("Your Progress")
    progress = gym_bro.get_progress()
    if not progress:
        st.info("Log some exercises to see your numbers!")
    else:
        for exercise, data in progress.items():
            with st.expander(f"📈 {exercise} ({data['sessions']} sessions)"):
                col1,col2,col3 = st.columns(3)
                col1.metric("Best 1RM", f"{data['current_1rm']}kg")
                col2.metric("First 1RM", f"{data['first_1rm']}kg")
                col3.metric("Change", f"{data['change_percent']}%", data['trend'])
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
        st.subheader(prog["program_name"])
        for d in prog["days"]:
            with st.expander(f"📅 {d['day']} – {d['focus']}"):
                for ex in d["exercises"]:
                    st.write(f"• **{ex['name']}** – {ex['sets']}×{ex['reps']} {('('+ex['notes']+')') if ex.get('notes') else ''}")
        if st.button("🔄 Regenerate Program"):
            gym_bro.generate_program()
            st.rerun()

# --- TAB 5: AI CHAT (UPDATED) ---
with tab5:
    st.header("💬 Chat with Gym Bro AI")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": f"Yo {username}! What's on your mind, bro? 💪"}
        ]

    # Display chat history
    for idx, msg in enumerate(st.session_state.chat_messages):
        with st.chat_message(msg["role"], avatar="💪" if msg["role"]=="assistant" else None):
            st.write(msg["content"])

    # Check if last assistant message contains a program JSON
    last_assistant_msg = None
    for msg in reversed(st.session_state.chat_messages):
        if msg["role"] == "assistant":
            last_assistant_msg = msg["content"]
            break

    program_json = None
    if last_assistant_msg:
        match = re.search(r'```json\s*(\{.*?\})\s*```', last_assistant_msg, re.DOTALL)
        if match:
            try:
                program_json = json.loads(match.group(1))
                if "program_name" not in program_json or "days" not in program_json:
                    program_json = None
            except:
                program_json = None

    if program_json:
        st.markdown("---")
        st.success("I see a program in my last message! Want to apply it?")
        if st.button("✅ Apply This Program to My Calendar", type="primary"):
            gym_bro.current_program = program_json
            gym_bro._save_json("current_program.json", program_json)
            st.rerun()

    if prompt := st.chat_input("Ask Gym Bro..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.spinner("Gym Bro is thinking..."):
            reply = gym_bro.ai_chat(prompt, st.session_state.chat_messages)
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()

st.markdown("---")
st.caption(f"Gym Bro v4.1 | User: {username} | We go jim! 🏋️")