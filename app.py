# app.py – Gym Bro v9.3 (max() error completely fixed, safer workout logging)

import streamlit as st
import json
import random
import os
import shutil
import re
from datetime import datetime, timedelta, date
from typing import Dict, List
import plotly.graph_objects as go
from openai import OpenAI
from tools import search_exercises, analyze_form, parse_program_payload, normalize_exercises
from gym_knowledge import get_knowledge_text

# ============================================
# GYM BRO CLASS (with self‑learning and memory)
# ============================================

class GymBro:
    def __init__(self, username="default"):
        self.username = username
        self.data_dir = f"user_data/{username}"
        os.makedirs(self.data_dir, exist_ok=True)

        # Migration of old root files
        old_files = [
            "workouts.json", "progress.json", "achievements.json",
            "custom_exercises.json", "user_profile.json",
            "current_program.json", "body_measurements.json",
            "chat_history.json", "learned_knowledge.json"
        ]
        for fname in old_files:
            old_path = fname
            new_path = os.path.join(self.data_dir, fname)
            if os.path.exists(old_path) and not os.path.exists(new_path):
                shutil.move(old_path, new_path)

        self.workouts = self._load_json("workouts.json", [])
        self.exercise_progress = self._load_json("progress.json", {})
        self.achievements = self._load_json("achievements.json", [])
        self.custom_exercises = self._load_json("custom_exercises.json", [])
        self.profile = self._load_json("user_profile.json", {})
        self.current_program = self._load_json("current_program.json", None)
        self.body_measurements = self._load_json("body_measurements.json", [])
        self.chat_history = self._load_json("chat_history.json", [])
        self.learned_knowledge = self._load_json("learned_knowledge.json", [])

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

    def setup_profile(self, profile_data: dict):
        self.profile = {
            **profile_data,
            "created": self.profile.get("created", datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat()
        }
        self._save_json("user_profile.json", self.profile)

    def add_body_measurement(self, weight, body_fat=None, notes=""):
        entry = {"date": datetime.now().isoformat(), "weight": weight, "body_fat": body_fat, "notes": notes}
        self.body_measurements.append(entry)
        self._save_json("body_measurements.json", self.body_measurements)

    def get_profile_context(self) -> str:
        if not self.profile:
            return "No profile set up yet."
        p = self.profile
        lines = []
        if p.get("age"):
            lines.append(f"Age: {p['age']}")
        if p.get("gender"):
            lines.append(f"Gender: {p['gender']}")
        if p.get("height"):
            lines.append(f"Height: {p['height']} cm")
        if self.body_measurements:
            latest = self.body_measurements[-1]
            lines.append(f"Current weight: {latest['weight']} kg")
            if latest.get("body_fat") is not None:
                lines.append(f"Body fat: {latest['body_fat']}%")
        lines.append(f"Experience: {p.get('experience', 'Not set')}")
        lines.append(f"Training days/week: {p.get('training_days', 'Not set')}")
        lines.append(f"Session length: {p.get('session_length', 'Not set')}")
        if p.get("resting_heart_rate"):
            lines.append(f"Resting HR: {p['resting_heart_rate']} bpm")
        if p.get("primary_goal"):
            lines.append(f"Primary goal: {p['primary_goal']}")
        if p.get("target_weight"):
            lines.append(f"Target weight: {p['target_weight']} kg")
        if p.get("strength_goals"):
            lines.append(f"Strength goals: {p['strength_goals']}")
        if p.get("diet_type"):
            lines.append(f"Diet: {p['diet_type']}")
        if p.get("allergies"):
            lines.append(f"Allergies: {p['allergies']}")
        if p.get("meals_per_day"):
            lines.append(f"Meals per day: {p['meals_per_day']}")
        if p.get("sleep_hours"):
            lines.append(f"Sleep: {p['sleep_hours']} hrs/night")
        if p.get("job_activity"):
            lines.append(f"Job activity: {p['job_activity']}")
        if p.get("stress_level"):
            lines.append(f"Stress: {p['stress_level']}/10")
        if p.get("equipment"):
            lines.append(f"Equipment: {', '.join(p['equipment'])}")
        if p.get("injuries"):
            lines.append(f"Injuries/limitations: {p['injuries']}")
        return "\n".join(lines)

    def generate_program(self):
        if not self.profile:
            return None
        try:
            from openai import OpenAI
            if "OPENAI_API_KEY" in st.secrets:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                profile_text = self.get_profile_context()
                knowledge_text = get_knowledge_text()
                prompt = f"""Create a {self.profile.get('training_days', 4)}-day gym workout plan based on this user profile and knowledge base.
Profile:
{profile_text}

Knowledge base:
{knowledge_text}

Return ONLY a valid JSON object with structure: {{"program_name": "...", "days": [{{"day": "Monday", "focus": "...", "exercises": [{{"name": "...", "sets": 3, "reps": "8-10", "notes": "..."}}]}}]}}
Consider their experience, equipment, injuries, and goals."""
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1500
                )
                prog, _ = parse_program_payload(response.choices[0].message.content)
                if prog:
                    self.current_program = prog
                    self._save_json("current_program.json", prog)
                    return prog
        except:
            pass
        # Offline fallback
        days = self.profile.get('training_days', 4)
        days_map = {2: ["Monday", "Thursday"], 3: ["Monday", "Wednesday", "Friday"],
                    4: ["Monday", "Tuesday", "Thursday", "Friday"],
                    5: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}
        day_names = days_map.get(days, ["Monday", "Wednesday", "Friday"])
        program = {"program_name": "Custom Plan", "days": []}
        for i, d in enumerate(day_names):
            if i % 2 == 0:
                focus = "Upper Body"
                exercises = [
                    {"name": "Bench Press", "sets": 3, "reps": "8-10", "notes": "Focus on control"},
                    {"name": "Barbell Row", "sets": 3, "reps": "8-10", "notes": "Squeeze at top"},
                    {"name": "Overhead Press", "sets": 3, "reps": "10-12", "notes": ""},
                    {"name": "Face Pulls", "sets": 3, "reps": "15-20", "notes": "Light, perfect form"}
                ]
            else:
                focus = "Lower Body"
                exercises = [
                    {"name": "Barbell Squat", "sets": 3, "reps": "8-10", "notes": "Depth over weight"},
                    {"name": "Romanian Deadlift", "sets": 3, "reps": "10-12", "notes": "Hamstring stretch"},
                    {"name": "Leg Press", "sets": 3, "reps": "12-15", "notes": "Constant tension"},
                    {"name": "Calf Raises", "sets": 4, "reps": "15-20", "notes": ""}
                ]
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
            name = ex.get("name", "Unknown Exercise")
            sets = ex.get("sets", [])
            # Filter only valid set dicts with positive weight/reps
            valid_sets = [s for s in sets if isinstance(s, dict) and s.get("weight", 0) > 0 and s.get("reps", 0) > 0]
            if not valid_sets:
                # Skip exercises with no valid sets – nothing to log
                continue

            if name not in self.exercise_progress:
                self.exercise_progress[name] = []

            total_volume = sum(s.get("weight", 0) * s.get("reps", 0) for s in valid_sets)
            best_set = max(valid_sets, key=lambda s: s.get("weight", 0) * (1 + s.get("reps", 0)/30))
            estimated_1rm = best_set.get("weight", 0) * (1 + best_set.get("reps", 0)/30)

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
            name = ex.get("name")
            if not name or name not in self.exercise_progress or len(self.exercise_progress[name]) < 2:
                continue
            sets = ex.get("sets", [])
            valid_sets = [s for s in sets if isinstance(s, dict) and s.get("weight", 0) > 0]
            if not valid_sets:
                continue
            current = max(s.get("weight", 0) * (1 + s.get("reps", 0)/30) for s in valid_sets)
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
        total_volume = sum(
            sum(s.get("weight", 0) * s.get("reps", 0) for s in ex.get("sets", []) if isinstance(s, dict))
            for ex in workout["exercises"]
        )
        fb = []
        if total_volume > 10000:
            fb.append("Bro, you moved some SERIOUS weight today! 💪")
        elif total_volume > 5000:
            fb.append("Solid volume bro! Building that foundation! 🏗️")
        else:
            fb.append("Good work bro! Every rep counts! 🎯")
        if workout.get("energy_level", 0) >= 8:
            fb.append("Energy was HIGH today! ⚡")
        elif workout.get("energy_level", 0) >= 5:
            fb.append("Good energy bro! 👊")
        else:
            fb.append("You showed up despite low energy – mental toughness! 🧠")
        if workout.get("sleep_quality", 0) <= 5:
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

    def get_weight_progress(self):
        if not self.body_measurements:
            return None
        return {
            "dates": [m["date"][:10] for m in self.body_measurements],
            "weights": [m["weight"] for m in self.body_measurements],
            "body_fats": [m.get("body_fat") for m in self.body_measurements]
        }

    def save_chat_message(self, role, content):
        self.chat_history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        self._save_json("chat_history.json", self.chat_history)

    def add_learned_knowledge(self, fact: str):
        self.learned_knowledge.append({"fact": fact, "timestamp": datetime.now().isoformat()})
        self._save_json("learned_knowledge.json", self.learned_knowledge)

    def get_learned_knowledge_text(self) -> str:
        if not self.learned_knowledge:
            return ""
        return "Learned knowledge:\n" + "\n".join([f"- {k['fact']}" for k in self.learned_knowledge[-20:]])

# ============================================
# STREAMLIT UI
# ============================================

st.set_page_config(page_title="Gym Bro", page_icon="💪", layout="wide")

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
    .profile-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border-radius: 18px; padding: 1.5rem; margin: 1rem 0;
        border: 1px solid var(--border);
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

st.markdown('<div class="hero-box"><h1>🏋️‍♂️ Gym Bro</h1><p>Your self‑learning AI coach</p></div>', unsafe_allow_html=True)

# Profile setup wizard
if not gym_bro.profile:
    st.subheader("Let's build your profile, bro! 💪")
    st.markdown("The more you tell me, the better I can coach you.")
    
    with st.form("comprehensive_profile"):
        st.markdown("### 📏 Body & Demographics")
        col1, col2, col3 = st.columns(3)
        with col1:
            age = st.number_input("Age", 10, 100, 25)
        with col2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
        with col3:
            height = st.number_input("Height (cm)", 100, 250, 175)
        
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Current weight (kg)", 30.0, 300.0, 75.0)
        with col2:
            body_fat = st.number_input("Body fat % (optional)", 0.0, 60.0, 0.0, step=0.1)

        st.markdown("---")
        st.markdown("### 🏃 Fitness & Training")
        col1, col2 = st.columns(2)
        with col1:
            experience = st.selectbox("Experience level", ["Beginner", "Intermediate", "Advanced"])
            training_days = st.slider("Training days per week", 1, 7, 4)
        with col2:
            session_length = st.selectbox("Session length", ["30 min", "45 min", "60 min", "75 min", "90 min"], index=2)
            include_hr = st.checkbox("I know my resting heart rate")
            resting_hr = None
            if include_hr:
                resting_hr = st.number_input("Resting heart rate (bpm)", 30, 120, 60)

        st.markdown("---")
        st.markdown("### 🎯 Goals")
        col1, col2 = st.columns(2)
        with col1:
            primary_goal = st.selectbox("Primary goal", [
                "Build muscle", "Lose fat", "Get stronger", 
                "Improve endurance", "Tone up", "General fitness",
                "Sport-specific performance", "Rehabilitation"
            ])
            target_weight = st.number_input("Target weight (kg, optional)", 0.0, 300.0, 0.0)
        with col2:
            strength_goals = st.text_area("Specific strength goals", placeholder="e.g., Bench 100kg, Squat 140kg, 10 pull-ups")
            timeline = st.selectbox("Goal timeline", ["No rush", "3 months", "6 months", "1 year"])

        st.markdown("---")
        st.markdown("### 🥗 Nutrition")
        col1, col2, col3 = st.columns(3)
        with col1:
            diet_type = st.selectbox("Diet type", ["No special diet", "Vegan", "Vegetarian", "Keto", "Paleo", "Mediterranean", "High protein", "Intermittent fasting"])
        with col2:
            allergies = st.text_input("Food allergies/restrictions", placeholder="e.g., nuts, dairy")
        with col3:
            meals_per_day = st.selectbox("Meals per day", [2, 3, 4, 5, 6], index=1)

        st.markdown("---")
        st.markdown("### 🌙 Lifestyle")
        col1, col2, col3 = st.columns(3)
        with col1:
            sleep_hours = st.number_input("Avg sleep (hours)", 3.0, 12.0, 7.0, 0.5)
        with col2:
            job_activity = st.selectbox("Daily activity level", ["Sedentary (desk job)", "Lightly active", "Moderately active", "Very active (physical job)"])
        with col3:
            stress_level = st.slider("Stress level", 1, 10, 5)

        st.markdown("---")
        st.markdown("### 🏋️ Equipment & Health")
        col1, col2 = st.columns(2)
        with col1:
            equipment = st.multiselect("Available equipment", [
                "Full gym", "Barbell", "Dumbbells", "Cables", "Machines",
                "Bodyweight only", "Resistance bands", "Kettlebells",
                "Pull-up bar", "Bench", "Squat rack"
            ], default=["Full gym"])
        with col2:
            injuries = st.text_area("Injuries / limitations", placeholder="e.g., Lower back pain, knee issues, shoulder impingement")
            focus_areas = st.multiselect("Areas to focus on", [
                "Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Overall"
            ], default=["Overall"])

        if st.form_submit_button("🚀 Create My Profile & Program", type="primary"):
            profile_data = {
                "age": age, "gender": gender, "height": height,
                "experience": experience, "training_days": training_days,
                "session_length": session_length, "resting_heart_rate": resting_hr,
                "primary_goal": primary_goal,
                "target_weight": target_weight if target_weight > 0 else None,
                "strength_goals": strength_goals if strength_goals else None,
                "timeline": timeline,
                "diet_type": diet_type,
                "allergies": allergies if allergies else None,
                "meals_per_day": meals_per_day,
                "sleep_hours": sleep_hours, "job_activity": job_activity,
                "stress_level": stress_level,
                "equipment": equipment,
                "injuries": injuries if injuries else None,
                "focus_areas": focus_areas
            }
            gym_bro.setup_profile(profile_data)
            if weight > 0:
                gym_bro.add_body_measurement(weight, body_fat if body_fat > 0 else None, "Initial measurement")
            gym_bro.generate_program()
            st.session_state.show_intro = False
            st.rerun()
    st.stop()

if st.session_state.get("show_intro", False):
    with st.chat_message("assistant", avatar="💪"):
        st.markdown(f"### Yo {username}! I know everything about your goals. Let's crush it! 💪")
    if st.button("Let's Go! 🚀", use_container_width=True, type="primary"):
        st.session_state.show_intro = False
        st.rerun()
    st.stop()

# Tabs
tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "👤 Profile", "📅 Calendar", "💪 Log Workout", 
    "📊 Progress", "🎯 My Program", "🤖 AI Chat", "📸 Form Check"
])

# --- TAB 0: PROFILE (fully editable) ---
with tab0:
    st.header("Your Profile")
    if not gym_bro.profile:
        st.info("No profile yet.")
    else:
        p = gym_bro.profile
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="profile-card"><h3>📏 Body</h3>'
                       f'<p>Age: {p.get("age", "N/A")}<br>'
                       f'Gender: {p.get("gender", "N/A")}<br>'
                       f'Height: {p.get("height", "N/A")} cm<br>'
                       f'Weight: {gym_bro.body_measurements[-1]["weight"] if gym_bro.body_measurements else "N/A"} kg</p></div>',
                       unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="profile-card"><h3>🎯 Goals</h3>'
                       f'<p>Primary: {p.get("primary_goal", "N/A")}<br>'
                       f'Target weight: {p.get("target_weight", "N/A")} kg<br>'
                       f'Timeline: {p.get("timeline", "N/A")}</p></div>',
                       unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="profile-card"><h3>🏋️ Training</h3>'
                       f'<p>Experience: {p.get("experience", "N/A")}<br>'
                       f'Days/week: {p.get("training_days", "N/A")}<br>'
                       f'Session: {p.get("session_length", "N/A")}</p></div>',
                       unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="profile-card"><h3>🥗 Nutrition</h3>'
                       f'<p>Diet: {p.get("diet_type", "N/A")}<br>'
                       f'Allergies: {p.get("allergies", "None")}<br>'
                       f'Meals/day: {p.get("meals_per_day", "N/A")}</p></div>',
                       unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="profile-card"><h3>🌙 Lifestyle</h3>'
                       f'<p>Sleep: {p.get("sleep_hours", "N/A")} hrs<br>'
                       f'Activity: {p.get("job_activity", "N/A")}<br>'
                       f'Stress: {p.get("stress_level", "N/A")}/10</p></div>',
                       unsafe_allow_html=True)
        with col3:
            equipment_list = p.get("equipment", [])
            st.markdown(f'<div class="profile-card"><h3>🔧 Equipment & Health</h3>'
                       f'<p>Equipment: {", ".join(equipment_list) if equipment_list else "N/A"}<br>'
                       f'Injuries: {p.get("injuries", "None")}</p></div>',
                       unsafe_allow_html=True)

        if st.button("✏️ Edit Full Profile"):
            st.session_state.edit_profile = True

        if st.session_state.get("edit_profile"):
            with st.form("full_profile_edit"):
                st.subheader("Edit Your Full Profile")
                age = st.number_input("Age", 10, 100, p.get("age", 25))
                gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"],
                                      index=["Male","Female","Other","Prefer not to say"].index(p.get("gender","Male")))
                height = st.number_input("Height (cm)", 100, 250, p.get("height", 175))
                if gym_bro.body_measurements:
                    latest_weight = gym_bro.body_measurements[-1]["weight"]
                    latest_bf = gym_bro.body_measurements[-1].get("body_fat") or 0.0
                else:
                    latest_weight = 75.0
                    latest_bf = 0.0
                weight = st.number_input("Current weight (kg)", 30.0, 300.0, latest_weight)
                body_fat = st.number_input("Body fat % (optional)", 0.0, 60.0, latest_bf, step=0.1)

                experience = st.selectbox("Experience level", ["Beginner", "Intermediate", "Advanced"],
                                          index=["Beginner","Intermediate","Advanced"].index(p.get("experience","Beginner")))
                training_days = st.slider("Training days per week", 1, 7, p.get("training_days", 4))
                session_length = st.selectbox("Session length", ["30 min", "45 min", "60 min", "75 min", "90 min"],
                                              index=["30 min","45 min","60 min","75 min","90 min"].index(p.get("session_length","60 min")))
                include_hr = st.checkbox("I know my resting heart rate", value=bool(p.get("resting_heart_rate")))
                resting_hr = None
                if include_hr:
                    resting_hr = st.number_input("Resting heart rate (bpm)", 30, 120, p.get("resting_heart_rate") or 60)

                primary_goal = st.selectbox("Primary goal", [
                    "Build muscle", "Lose fat", "Get stronger", 
                    "Improve endurance", "Tone up", "General fitness",
                    "Sport-specific performance", "Rehabilitation"
                ], index=["Build muscle","Lose fat","Get stronger","Improve endurance","Tone up","General fitness","Sport-specific performance","Rehabilitation"].index(p.get("primary_goal","Build muscle")))
                target_weight = st.number_input("Target weight (kg, optional)", 0.0, 300.0, p.get("target_weight") or 0.0)
                strength_goals = st.text_area("Specific strength goals", value=p.get("strength_goals") or "")
                timeline = st.selectbox("Goal timeline", ["No rush", "3 months", "6 months", "1 year"],
                                        index=["No rush","3 months","6 months","1 year"].index(p.get("timeline","No rush")))

                diet_type = st.selectbox("Diet type", ["No special diet", "Vegan", "Vegetarian", "Keto", "Paleo", "Mediterranean", "High protein", "Intermittent fasting"],
                                         index=["No special diet","Vegan","Vegetarian","Keto","Paleo","Mediterranean","High protein","Intermittent fasting"].index(p.get("diet_type","No special diet")))
                allergies = st.text_input("Food allergies/restrictions", value=p.get("allergies") or "")
                meals_per_day = st.selectbox("Meals per day", [2,3,4,5,6], index=[2,3,4,5,6].index(p.get("meals_per_day",3)))

                sleep_hours = st.number_input("Avg sleep (hours)", 3.0, 12.0, p.get("sleep_hours", 7.0), 0.5)
                job_activity = st.selectbox("Daily activity level", ["Sedentary (desk job)", "Lightly active", "Moderately active", "Very active (physical job)"],
                                            index=["Sedentary (desk job)","Lightly active","Moderately active","Very active (physical job)"].index(p.get("job_activity","Sedentary (desk job)")))
                stress_level = st.slider("Stress level", 1, 10, p.get("stress_level", 5))

                equipment = st.multiselect("Available equipment", [
                    "Full gym", "Barbell", "Dumbbells", "Cables", "Machines",
                    "Bodyweight only", "Resistance bands", "Kettlebells",
                    "Pull-up bar", "Bench", "Squat rack"
                ], default=p.get("equipment", ["Full gym"]))
                injuries = st.text_area("Injuries / limitations", value=p.get("injuries") or "")
                focus_areas = st.multiselect("Areas to focus on", [
                    "Chest", "Back", "Legs", "Shoulders", "Arms", "Core", "Overall"
                ], default=p.get("focus_areas", ["Overall"]))

                if st.form_submit_button("💾 Save Full Profile", type="primary"):
                    new_profile = {
                        "age": age, "gender": gender, "height": height,
                        "experience": experience, "training_days": training_days,
                        "session_length": session_length, "resting_heart_rate": resting_hr,
                        "primary_goal": primary_goal,
                        "target_weight": target_weight if target_weight > 0 else None,
                        "strength_goals": strength_goals if strength_goals else None,
                        "timeline": timeline,
                        "diet_type": diet_type,
                        "allergies": allergies if allergies else None,
                        "meals_per_day": meals_per_day,
                        "sleep_hours": sleep_hours, "job_activity": job_activity,
                        "stress_level": stress_level,
                        "equipment": equipment,
                        "injuries": injuries if injuries else None,
                        "focus_areas": focus_areas
                    }
                    gym_bro.setup_profile(new_profile)
                    gym_bro.add_body_measurement(weight, body_fat if body_fat > 0 else None, "Profile update")
                    gym_bro.generate_program()
                    st.session_state.edit_profile = False
                    st.rerun()

        if len(gym_bro.body_measurements) > 1:
            st.markdown("---")
            st.subheader("📉 Weight Progress")
            weight_data = gym_bro.get_weight_progress()
            if weight_data:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=weight_data["dates"], y=weight_data["weights"], 
                                        mode='lines+markers', name='Weight (kg)'))
                if any(bf is not None for bf in weight_data["body_fats"]):
                    fig.add_trace(go.Scatter(x=weight_data["dates"], y=weight_data["body_fats"], 
                                            mode='lines+markers', name='Body Fat %', yaxis='y2'))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True, key="weight_progress_chart")

# --- TAB 1: CALENDAR (with safe day lookup) ---
with tab1:
    st.header("Your Training Calendar")
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    days_of_week = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    cols = st.columns(7)
    workout_dates = {datetime.fromisoformat(w["date"]).date() for w in gym_bro.workouts}
    planned_days = set()
    if gym_bro.current_program:
        for d in gym_bro.current_program["days"]:
            day_name = d.get("day", "").strip().title()
            if day_name in days_of_week:
                idx = days_of_week.index(day_name)
                planned_days.add(week_start + timedelta(days=idx))
    for i, col in enumerate(cols):
        day = week_start + timedelta(days=i)
        is_trained = day in workout_dates
        is_planned = day in planned_days
        class_name = "calendar-day"
        if is_trained: class_name += " trained"
        elif is_planned and day >= today: class_name += " planned"
        with col:
            st.markdown(f'<div class="{class_name}"><strong>{days_of_week[i][:3]}</strong><span>{day.day}</span><br>{"✅" if is_trained else "📋" if is_planned and day >= today else ""}</div>', unsafe_allow_html=True)
    st.caption("✅ Trained   📋 Planned")
    st.markdown("---")
    st.subheader("Today's Session")
    if gym_bro.current_program:
        today_name = today.strftime("%A")
        today_prog = next((d for d in gym_bro.current_program["days"] if d["day"].strip().title() == today_name), None)
        if today_prog:
            st.success(f"🎯 **{today_prog.get('focus','')}** day!")
            for ex in today_prog.get("exercises", []):
                st.write(f"• **{ex.get('name','')}** – {ex.get('sets','?')}×{ex.get('reps','?')} {('('+ex.get('notes','')+')') if ex.get('notes') else ''}")
            if st.button("Log This Workout", type="primary"):
                st.session_state.current_exercises = []
                for ex in today_prog.get("exercises", []):
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

# --- TAB 3: PROGRESS (fixed duplicate chart keys) ---
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
                    st.plotly_chart(fig, use_container_width=True, key=f"progress_chart_{exercise}")
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
        for d in prog.get("days", []):
            day_name = d.get("day", "Unknown").strip().title()
            focus = d.get("focus", "General")
            with st.expander(f"📅 {day_name} – {focus}"):
                for ex in d.get("exercises", []):
                    n = ex.get("notes","")
                    st.write(f"• **{ex.get('name','')}** – {ex.get('sets','?')}×{ex.get('reps','?')} {f'({n})' if n else ''}")
        if st.button("🔄 Regenerate Program"):
            gym_bro.generate_program()
            st.rerun()

# --- TAB 5: AI CHAT (self‑learning, memory, knowledge, FIXED workout logging) ---
with tab5:
    st.header("💬 Chat with Gym Bro AI")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        # Load last 10 messages from saved history
        if gym_bro.chat_history:
            for msg in gym_bro.chat_history[-10:]:
                st.session_state.chat_messages.append({"role": msg["role"], "content": msg["content"]})

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="💪" if msg["role"]=="assistant" else None):
            st.markdown(msg["content"])

    # Build knowledge-rich system prompt
    base_knowledge = get_knowledge_text()
    learned = gym_bro.get_learned_knowledge_text()
    profile_text = gym_bro.get_profile_context()
    program_text = json.dumps(gym_bro.current_program) if gym_bro.current_program else "None"

    system_prompt = f"""You are Gym Bro, an elite AI gym coach with encyclopedic knowledge of exercises, biomechanics, program design, and nutrition.
You have access to a knowledge base, the user's profile, their current program, and you can research new information on the web.

Knowledge base:
{base_knowledge}

{learned}

User Profile:
{profile_text}

Current Program:
{program_text}

You can use these tools:
- search_web(query) – to find the latest exercise science or tips
- create_program(program_json) – to create or update the user's workout plan
- log_todays_workout(exercises) – to log a completed workout. The exercises argument MUST be a valid JSON list of objects. Each object must have a "name" (string) and a "sets" array. Each set must be an object with "weight" (number, >0), "reps" (number, >0), and optional "notes". All strings must have properly escaped double quotes. Example: [{{\"name\":\"Squat\",\"sets\":[{{\"weight\":100,\"reps\":5,\"notes\":\"felt strong\"}}]}}]
- save_learned_knowledge(fact) – to store a new fact permanently

Always be encouraging, use 'bro', emojis, and hype. When returning JSON strings, escape double quotes with backslashes. When you learn something useful from a web search or from the user, save it with save_learned_knowledge so you remember it forever. If you don't know something, search the web proactively!"""

    functions = [
        {
            "name": "create_program",
            "description": "Create or update the user's workout program. Provide the complete program as a JSON string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "program_json": {"type": "string", "description": "Full program JSON string with escaped quotes"}
                },
                "required": ["program_json"]
            }
        },
        {
            "name": "log_todays_workout",
            "description": "Log a completed workout for the current day. Provide a JSON list of exercises with properly escaped quotes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exercises": {
                        "type": "string",
                        "description": "JSON list of exercises. Each exercise must have a 'name' and a 'sets' array. Each set must have 'weight' (>0), 'reps' (>0), and optional 'notes'. Example: [{\"name\":\"Squat\",\"sets\":[{\"weight\":100,\"reps\":5,\"notes\":\"\"}]}]"
                    }
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
        },
        {
            "name": "save_learned_knowledge",
            "description": "Save a new fact or piece of information into long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact to remember, e.g. 'New study shows drop sets increase hypertrophy by 20%'"}
                },
                "required": ["fact"]
            }
        }
    ]

    if prompt := st.chat_input("Ask Gym Bro..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        gym_bro.save_chat_message("user", prompt)

        with st.spinner("Gym Bro is thinking..."):
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(st.session_state.chat_messages[-6:])  # last 6 for immediate context

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
                    raw_args = reply_msg.function_call.arguments
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        repaired = re.sub(r'(?<!\\)"', r'\\"', raw_args)
                        try:
                            args = json.loads(repaired)
                        except:
                            st.session_state.chat_messages.append({"role": "assistant", "content": f"Error: Could not parse function arguments. Raw: {raw_args}"})
                            st.rerun()
                    if args:
                        if func_name == "create_program":
                            prog, err = parse_program_payload(args["program_json"])
                            if prog:
                                gym_bro.current_program = prog
                                gym_bro._save_json("current_program.json", prog)
                                reply = "✅ Program updated! Check your calendar."
                            else:
                                reply = f"Couldn't update program: {err}"
                        elif func_name == "log_todays_workout":
                            try:
                                raw_exercises = args["exercises"]
                                # Parse with repair if needed
                                try:
                                    exercises = json.loads(raw_exercises)
                                except json.JSONDecodeError:
                                    repaired = raw_exercises
                                    repaired = re.sub(r'(?<!\\)"', r'\\"', repaired)
                                    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
                                    exercises = json.loads(repaired)

                                if not isinstance(exercises, list):
                                    raise ValueError("Exercises must be a list")

                                # Clean and validate each exercise
                                clean_exercises = []
                                for ex in exercises:
                                    if not isinstance(ex, dict):
                                        continue
                                    name = ex.get("name", "Unknown")
                                    sets = ex.get("sets", [])
                                    if not isinstance(sets, list):
                                        sets = []
                                    # Keep only valid sets
                                    valid_sets = [s for s in sets if isinstance(s, dict) and s.get("weight", 0) > 0]
                                    if not valid_sets:
                                        continue  # skip exercises with no valid sets
                                    clean_exercises.append({"name": name, "sets": valid_sets})

                                if not clean_exercises:
                                    raise ValueError("No valid exercises found")

                                result = gym_bro.log_workout(clean_exercises, 7, 7, 60)
                                reply = f"Workout logged! {result['feedback']}"
                            except Exception as e:
                                reply = f"Couldn't log workout: {e}"
                        elif func_name == "search_web":
                            results = search_exercises(args["query"])
                            reply = f"Search results:\n{results}"
                            if results and "Link:" in results:
                                gym_bro.add_learned_knowledge(f"From web search '{args['query']}': {results[:200]}")
                        elif func_name == "save_learned_knowledge":
                            gym_bro.add_learned_knowledge(args["fact"])
                            reply = f"🧠 Learned and saved: {args['fact']}"
                        else:
                            reply = "Function not implemented."
                        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                        gym_bro.save_chat_message("assistant", reply)
                    else:
                        st.session_state.chat_messages.append({"role": "assistant", "content": "Error: Could not parse function arguments."})
                else:
                    reply = reply_msg.content
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                    gym_bro.save_chat_message("assistant", reply)
            except Exception as e:
                st.session_state.chat_messages.append({"role": "assistant", "content": f"Error: {e}"})
            st.rerun()

# --- TAB 6: FORM CHECK (unchanged) ---
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
st.caption(f"Gym Bro v9.3 | User: {username} | We go jim! 🏋️")