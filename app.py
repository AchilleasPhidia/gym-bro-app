# app.py - Gym Bro v3.0 (Fixed deletion + smart auto-fill sets)

import streamlit as st
import json
import random
import os
import shutil
from datetime import datetime
from typing import Dict, List

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

    def get_next_session(self):
        if not self.workouts:
            return {
                "message": "No workouts yet bro! Let's start with a full body session!",
                "suggested_exercises": [
                    {"name": "Barbell Squat", "sets": 3, "reps": "8-10", "suggestion": "Moderate"},
                    {"name": "Bench Press", "sets": 3, "reps": "8-10", "suggestion": "Moderate"},
                    {"name": "Deadlift", "sets": 3, "reps": "6-8", "suggestion": "Moderate"},
                ]
            }
        last = self.workouts[-1]
        last_ex = [e["name"] for e in last["exercises"]]
        if "Barbell Squat" in last_ex:
            focus = "Upper Body"
            exercises = [
                {"name": "Bench Press", "sets": 4, "reps": "6-8", "suggestion": "Add 2.5kg from last time"},
                {"name": "Barbell Row", "sets": 4, "reps": "8-10", "suggestion": "Moderate-Heavy"},
            ]
        else:
            focus = "Lower Body"
            exercises = [
                {"name": "Barbell Squat", "sets": 4, "reps": "6-8", "suggestion": "Add 2.5kg from last time"},
                {"name": "Romanian Deadlift", "sets": 3, "reps": "8-10", "suggestion": "Moderate"},
            ]
        return {
            "focus": focus,
            "message": f"Bro, let's hit {focus.lower()} today! 🔥",
            "suggested_exercises": exercises,
            "workout_count": len(self.workouts)
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
                system_prompt = f"""You are Gym Bro, a supportive and knowledgeable gym coach. 
You give advice on exercises, form, nutrition, motivation, and programming.
Speak like a friendly bro: use 'bro', emojis, and hype.
Be encouraging but honest. Keep responses under 150 words.
{last_workout_context}"""
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(conversation_history[-6:])
                messages.append({"role": "user", "content": user_message})
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=200
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
# STREAMLIT UI
# ============================================

st.set_page_config(page_title="Gym Bro", page_icon="💪", layout="wide")

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
    user_option = st.sidebar.radio("Select or new user", ["Existing user", "New user"])
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
        for i in range(5):  # max 5 sets
            if f"w_{i}" not in st.session_state:
                st.session_state[f"w_{i}"] = 20.0
            if f"r_{i}" not in st.session_state:
                st.session_state[f"r_{i}"] = 10
            if f"n_{i}" not in st.session_state:
                st.session_state[f"n_{i}"] = ""

gym_bro = st.session_state.gym_bro

st.sidebar.markdown("---")
st.sidebar.metric("Total Workouts", len(gym_bro.workouts))
if gym_bro.achievements:
    st.sidebar.write(f"🏆 {len(gym_bro.achievements)} Achievements")

# --- Delete user section (fixed) ---
st.sidebar.markdown("---")
if "delete_mode" not in st.session_state:
    st.session_state.delete_mode = False

if not st.session_state.delete_mode:
    if st.sidebar.button("🗑️ Delete this user", help="Permanently delete all data for this user"):
        st.session_state.delete_mode = True
        st.rerun()
else:
    st.sidebar.warning(f"Are you sure you want to delete '{username}'? All data will be lost.")
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
            else:
                st.sidebar.error("Could not delete user.")
                st.session_state.delete_mode = False
    with col2:
        if st.button("Cancel"):
            st.session_state.delete_mode = False
            st.rerun()

# --- Main Content ---
st.title("🏋️‍♂️ Gym Bro – Your AI Training Partner")

if st.session_state.get("show_intro", False):
    with st.chat_message("assistant", avatar="💪"):
        greetings = [
            f"Yo {username}! Gym Bro here! Ready to crush it? 💪",
            f"What's up {username}! Let's get these gains together! 🔥",
            f"Brooo! Welcome, {username}. Time to put in work! 🏋️"
        ]
        st.markdown(f"### {random.choice(greetings)}")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Let's Go! 🚀", use_container_width=True, type="primary"):
            st.session_state.show_intro = False
            st.rerun()
    with col2:
        if st.button("Tell Me More 🤔", use_container_width=True):
            with st.expander("About Gym Bro", expanded=True):
                st.write("""
                **I'm Gym Bro!** Your personal AI coach:
                - 📝 Log workouts
                - 📈 Track progress
                - 🤖 AI chat for advice
                - 🏆 Celebrate PRs
                - 👥 Multi-user with auto‑fill
                """)
else:
    tab1, tab2, tab3, tab4 = st.tabs(["💪 Log Workout", "📊 Progress", "🎯 Next Session", "🤖 AI Chat"])

    with tab1:
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

        # Set 1 (with Apply button for the rest)
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

        # Sets 2+
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
            # Reset the set session state so the next exercise starts fresh (optional)
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

    with tab2:
        st.header("Your Progress")
        progress = gym_bro.get_progress()
        if not progress:
            st.info("Log some exercises to see your numbers! (They'll appear here once you've added a workout.)")
        else:
            for exercise, data in progress.items():
                with st.expander(f"📈 {exercise} ({data['sessions']} sessions)"):
                    col1,col2,col3 = st.columns(3)
                    col1.metric("Best 1RM", f"{data['current_1rm']}kg")
                    col2.metric("First 1RM", f"{data['first_1rm']}kg")
                    col3.metric("Change", f"{data['change_percent']}%", data['trend'])
                    if exercise in gym_bro.exercise_progress:
                        import plotly.graph_objects as go
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

    with tab3:
        st.header("What's Next?")
        recommendation = gym_bro.get_next_session()
        st.info(recommendation["message"])
        if "focus" in recommendation:
            st.subheader(f"🎯 {recommendation['focus']} Focus")
        for ex in recommendation["suggested_exercises"]:
            cols = st.columns([3,1,1,1])
            cols[0].markdown(f"**{ex['name']}**")
            cols[1].caption(f"Sets: {ex['sets']}")
            cols[2].caption(f"Reps: {ex['reps']}")
            cols[3].caption(f"💡 {ex['suggestion']}")
        if st.button("Start This Workout →"):
            st.session_state.current_exercises = []
            st.rerun()

    with tab4:
        st.header("💬 Chat with Gym Bro AI")
        st.caption("Ask me anything about training, form, nutrition, or motivation! (I can see your last workout 😉)")
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = [
                {"role": "assistant", "content": f"Yo {username}! What's on your mind, bro? 💪"}
            ]
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"], avatar="💪" if msg["role"]=="assistant" else None):
                st.write(msg["content"])
        if prompt := st.chat_input("Ask Gym Bro..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.spinner("Gym Bro is thinking..."):
                reply = gym_bro.ai_chat(prompt, st.session_state.chat_messages)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            st.rerun()

st.markdown("---")
st.caption(f"Gym Bro v3.0 | User: {username} | We go jim! 🏋️")