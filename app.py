# app.py - Your Gym Bro App

import streamlit as st
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List
import os

# ============================================
# GYM BRO'S BRAIN
# ============================================

class GymBro:
    """Your personal AI coach - Gym Bro"""

    def __init__(self):
        self.name = "Gym Bro"
        self.user_name = None
        self.relationship_level = 1
        self.nickname_for_you = None

        # Load or initialize data
        self.workouts = self._load_data("workouts.json", [])
        self.exercise_progress = self._load_data("progress.json", {})
        self.achievements = self._load_data("achievements.json", [])

    def _load_data(self, filename, default):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            return default

    def _save_data(self, filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def introduce_yourself(self):
        """Gym Bro introduces himself"""
        hour = datetime.now().hour
        if hour < 12:
            time_greeting = "Morning"
        elif hour < 17:
            time_greeting = "Afternoon"
        else:
            time_greeting = "Evening"

        greetings = [
            f"Yo! {time_greeting}! Gym Bro here, ready to get these gains with you! 💪",
            f"What's good! {time_greeting} session about to be legendary! Gym Bro's got your back! 🔥",
            f"Bro! Perfect {time_greeting.lower()} to hit the gym! You ready to put in work? Let's go! 🏋️",
        ]
        return random.choice(greetings)

    def log_workout(self, exercises_data: List[Dict], energy: int, sleep: int, duration: int):
        """Log a complete workout session"""
        workout = {
            "date": datetime.now().isoformat(),
            "exercises": exercises_data,
            "energy_level": energy,
            "sleep_quality": sleep,
            "duration_minutes": duration
        }

        self.workouts.append(workout)
        self._save_data("workouts.json", self.workouts)

        # Update progress for each exercise
        for ex in exercises_data:
            name = ex["name"]
            if name not in self.exercise_progress:
                self.exercise_progress[name] = []

            # Calculate volume and estimated 1RM
            total_volume = sum(s["weight"] * s["reps"] for s in ex["sets"] if s["weight"] > 0)
            best_set = max(ex["sets"], key=lambda s: s["weight"] * (1 + s["reps"]/30)) if ex["sets"] else None

            if best_set and best_set["weight"] > 0:
                estimated_1rm = best_set["weight"] * (1 + best_set["reps"]/30)
            else:
                estimated_1rm = 0

            self.exercise_progress[name].append({
                "date": datetime.now().isoformat(),
                "volume": total_volume,
                "estimated_1rm": round(estimated_1rm, 1)
            })

        self._save_data("progress.json", self.exercise_progress)

        # Check for PRs
        new_prs = self._check_for_prs(exercises_data)

        # Update relationship
        self.relationship_level = min(10, len(self.workouts) / 5)

        # Give nickname after 10 workouts
        if len(self.workouts) >= 10 and not self.nickname_for_you:
            nicknames = ["Beast", "Champ", "Warrior", "Machine", "Legend", "Titan", "Savage", "King"]
            self.nickname_for_you = random.choice(nicknames)

        return {
            "feedback": self._generate_feedback(workout),
            "new_prs": new_prs,
            "total_workouts": len(self.workouts)
        }

    def _check_for_prs(self, exercises_data: List[Dict]) -> List[Dict]:
        """Check if any exercises hit a new PR"""
        new_prs = []

        for ex in exercises_data:
            name = ex["name"]
            if name in self.exercise_progress and len(self.exercise_progress[name]) >= 2:
                current = max(s["weight"] * (1 + s["reps"]/30) for s in ex["sets"] if s["weight"] > 0)
                previous = max(
                    entry["estimated_1rm"] for entry in self.exercise_progress[name][:-1]
                ) if len(self.exercise_progress[name]) > 1 else 0

                if current > previous * 1.01 and previous > 0:  # 1% improvement
                    improvement = round((current - previous) / previous * 100, 1)
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

        self._save_data("achievements.json", self.achievements)
        return new_prs

    def _generate_feedback(self, workout: Dict) -> str:
        """Generate Gym Bro style feedback"""
        total_volume = sum(
            sum(s["weight"] * s["reps"] for s in ex["sets"])
            for ex in workout["exercises"]
        )

        feedbacks = []

        if total_volume > 10000:
            feedbacks.append("Bro, you moved some SERIOUS weight today! 💪")
        elif total_volume > 5000:
            feedbacks.append("Solid volume bro! Building that foundation! 🏗️")
        else:
            feedbacks.append("Good work bro! Every rep counts! 🎯")

        if workout["energy_level"] >= 8:
            feedbacks.append("Energy was HIGH today! Love to see it! ⚡")
        elif workout["energy_level"] >= 5:
            feedbacks.append("Good energy bro! You pushed through! 👊")
        else:
            feedbacks.append("Low energy but you still showed up. That's mental toughness bro! 🧠")

        if workout["sleep_quality"] <= 5:
            feedbacks.append("Try to get more sleep tonight bro, recovery is key! 😴")

        return " ".join(feedbacks)

    def get_next_session_recommendation(self) -> Dict:
        """Tell you what to do in your next session"""
        if not self.workouts:
            return {
                "message": "No workouts yet bro! Let's start with a full body session to see where you're at!",
                "suggested_exercises": [
                    {"name": "Barbell Squat", "sets": 3, "reps": "8-10", "weight_suggestion": "Moderate"},
                    {"name": "Bench Press", "sets": 3, "reps": "8-10", "weight_suggestion": "Moderate"},
                    {"name": "Deadlift", "sets": 3, "reps": "6-8", "weight_suggestion": "Moderate"},
                    {"name": "Pull-ups or Lat Pulldowns", "sets": 3, "reps": "8-10", "weight_suggestion": "Bodyweight/Moderate"},
                    {"name": "Planks", "sets": 3, "reps": "30-60 sec", "weight_suggestion": "Bodyweight"}
                ]
            }

        last_workout = self.workouts[-1]
        last_exercises = [ex["name"] for ex in last_workout["exercises"]]

        if "Barbell Squat" in last_exercises:
            focus = "Upper Body Focus"
            exercises = [
                {"name": "Bench Press", "sets": 4, "reps": "6-8", "weight_suggestion": "Try adding 2.5kg from last time"},
                {"name": "Barbell Row", "sets": 4, "reps": "8-10", "weight_suggestion": "Moderate-Heavy"},
                {"name": "Overhead Press", "sets": 3, "reps": "8-10", "weight_suggestion": "Moderate"},
                {"name": "Pull-ups", "sets": 3, "reps": "Max reps", "weight_suggestion": "Bodyweight"},
                {"name": "Face Pulls", "sets": 3, "reps": "12-15", "weight_suggestion": "Light, focus on form"}
            ]
        else:
            focus = "Lower Body Focus"
            exercises = [
                {"name": "Barbell Squat", "sets": 4, "reps": "6-8", "weight_suggestion": "Try adding 2.5-5kg from last time"},
                {"name": "Romanian Deadlift", "sets": 3, "reps": "8-10", "weight_suggestion": "Moderate"},
                {"name": "Leg Press", "sets": 3, "reps": "10-12", "weight_suggestion": "Moderate-Heavy"},
                {"name": "Walking Lunges", "sets": 3, "reps": "12 each leg", "weight_suggestion": "Moderate"},
                {"name": "Calf Raises", "sets": 4, "reps": "15-20", "weight_suggestion": "Moderate"}
            ]

        return {
            "focus": focus,
            "message": f"Bro, let's hit {focus.lower()} today! You killed it last session, let's keep that momentum! 🔥",
            "suggested_exercises": exercises,
            "workout_count": len(self.workouts)
        }

    def get_progress_summary(self) -> Dict:
        """Get overall progress summary"""
        if not self.exercise_progress:
            return {"message": "No data yet bro! Log some workouts and I'll show you the gains! 📊"}

        summary = {}
        for exercise, history in self.exercise_progress.items():
            if len(history) >= 2:
                first = history[0]["estimated_1rm"]
                last = history[-1]["estimated_1rm"]
                if first > 0:
                    change = round((last - first) / first * 100, 1)
                    summary[exercise] = {
                        "first_1rm": round(first, 1),
                        "current_1rm": round(last, 1),
                        "change_percent": change,
                        "trend": "📈 Up" if change > 0 else "📉 Down" if change < 0 else "➡️ Same"
                    }

        return summary

# Add chat response method to GymBro class
def _generate_chat_response(self, message: str) -> str:
    """Generate a Gym Bro style response"""
    message_lower = message.lower()

    if "squat" in message_lower and ("form" in message_lower or "improve" in message_lower):
        return """Bro! Great question about squats! Here's what you need to focus on:

1. **Feet shoulder-width**, toes slightly out
2. **Chest up, back tight** - like you're holding a pencil between your shoulder blades
3. **Break at the knees AND hips** simultaneously
4. **Knees track over toes** - don't let them cave in!
5. **Go deep** - hip crease below knee
6. **Drive through your heels** on the way up

Start with just the bar bro. Perfect form > heavy weight. We'll add plates when the movement is clean! 💪

Want me to show you some drills to help? 🤔"""

    elif "progress" in message_lower:
        if len(self.workouts) == 0:
            return "Bro, we haven't started yet! Log your first workout and I'll track everything for you! 📊"
        else:
            return f"You've done {len(self.workouts)} workouts so far bro! Check the Progress tab to see your strength gains. Keep showing up and those numbers will keep climbing! 📈💪"

    elif "eat" in message_lower or "nutrition" in message_lower or "food" in message_lower:
        return """Bro, nutrition is KEY! Here's the simple version:

**Pre-workout (1-2 hours before):**
- Carbs for energy (banana, oatmeal, rice)
- Some protein (chicken, eggs, shake)

**Post-workout (within 2 hours):**
- Protein for muscle repair (25-40g)
- Carbs to replenish energy

**General tips:**
- Eat 1.6-2.2g protein per kg of bodyweight
- Stay hydrated! (3-4 liters water daily)
- Don't train on empty if you want performance

Simple, right? No need to overcomplicate it bro! 🍗🥗"""

    elif "plateau" in message_lower or "stuck" in message_lower:
        return """Ah bro, plateaus happen to everyone! Here's how we break through:

1. **Eat more** - You might need more fuel
2. **Sleep more** - Recovery is when you grow
3. **Change rep ranges** - If you've been doing 8-12, try 4-6 for strength
4. **Add volume** - 1-2 more sets per exercise
5. **Deload week** - Sometimes you need to step back to leap forward
6. **Check form** - Better technique = more strength

Which lift are you stuck on? Let me give you specific tips! 🎯"""

    elif "sore" in message_lower:
        return """Being sore is normal bro, especially when you're new or trying new exercises!

**Can you train?**
- If it's mild soreness → Go for it, just warm up well
- If you're really struggling to move → Rest or train a different muscle group
- If it's sharp pain → That's injury, not soreness. Rest!

**Recovery tips:**
- Light movement (walking, stretching)
- Stay hydrated
- Get that protein in
- Sleep is your best recovery tool

Listen to your body bro. There's a difference between pushing through and being stupid about it! 🧠💪"""

    elif "motivation" in message_lower or "motivate" in message_lower:
        return """BRO! Let me remind you who you are! 🔥

You're someone who SHOWS UP. Someone who puts in the WORK. Every rep, every set, every session - you're building a stronger version of yourself!

Remember:
- The you from last year would be PROUD
- The you from next year is COUNTING ON YOU
- Everyone starts somewhere
- The only bad workout is the one you skipped

Now get in there and CRUSH IT! I believe in you bro! 💪🔥

*We go jim!* 🏋️"""

    elif "hello" in message_lower or "hey" in message_lower or "hi" in message_lower:
        return self.introduce_yourself()

    else:
        responses = [
            "Bro, that's a great question! I'm still learning new things every day. Want me to help you with something specific about training? 💪",
            f"Interesting! You know, the more we train together, the better I'll understand your needs. For now, ask me about exercises, form, nutrition, or your progress! 🎯",
            "Good question! I'm here to help with your training journey. Try asking me about specific exercises, your progress, or what to do next! 🏋️",
        ]
        return random.choice(responses)

# Attach the method
GymBro._generate_chat_response = _generate_chat_response

# ============================================
# STREAMLIT APP
# ============================================

# Initialize Gym Bro
if 'gym_bro' not in st.session_state:
    st.session_state.gym_bro = GymBro()
    st.session_state.show_intro = True

gym_bro = st.session_state.gym_bro

# Page config
st.set_page_config(
    page_title="Gym Bro - Your AI Coach",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better look
st.markdown("""
<style>
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
    .pr-badge {
        background-color: #ffd700;
        padding: 10px;
        border-radius: 10px;
        margin: 5px;
    }
    .coach-message {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("Gym Bro 💪")

    # Stats
    workouts_count = len(gym_bro.workouts)
    st.metric("Total Workouts", workouts_count)

    if gym_bro.nickname_for_you:
        st.info(f"Gym Bro calls you: **{gym_bro.nickname_for_you}**")

    st.markdown("---")

    st.markdown("### Quick Actions")
    if st.button("🆕 New Workout", use_container_width=True):
        st.session_state.current_tab = "Workout"
        st.rerun()

    st.markdown("---")
    st.caption("Gym Bro learns from every workout. The more you train, the smarter he gets! 🧠")

# Main Content
st.title("🏋️‍♂️ Gym Bro - Your AI Training Partner")

# Gym Bro's greeting
if st.session_state.get('show_intro', True):
    with st.chat_message("assistant", avatar="💪"):
        st.markdown(f"### **{gym_bro.introduce_yourself()}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Let's Start Training! 🏋️", use_container_width=True, type="primary"):
                st.session_state.show_intro = False
                st.session_state.current_tab = "Workout"
                st.rerun()
        with col2:
            if st.button("Tell Me More 🤔", use_container_width=True):
                with st.expander("About Gym Bro", expanded=True):
                    st.write("""
                    **Yo! I'm Gym Bro!** 🎉

                    I'm your personal AI coach who:
                    - 📝 Logs all your workouts
                    - 📈 Tracks your progress
                    - 🎯 Tells you what to do next
                    - 🏆 Celebrates your PRs
                    - 💪 Keeps you motivated

                    Just show up, log your workouts, and I'll handle the rest!

                    **Let's get these gains! 🚀**
                    """)

# Main tabs
if not st.session_state.get('show_intro', False):
    tab1, tab2, tab3, tab4 = st.tabs(["💪 Workout", "📊 Progress", "🎯 Next Session", "💬 Chat"])

    # TAB 1: WORKOUT LOGGING
    with tab1:
        st.header("Log Your Workout")

        # Session info
        col1, col2, col3 = st.columns(3)
        with col1:
            energy = st.slider("⚡ Energy Level", 1, 10, 7, help="How energetic do you feel?")
        with col2:
            sleep = st.slider("😴 Sleep Quality", 1, 10, 7, help="How well did you sleep?")
        with col3:
            duration = st.number_input("⏱️ Duration (min)", 15, 180, 45)

        st.markdown("---")

        # Exercise input
        st.subheader("Add Exercises")

        # Exercise selection
        common_exercises = [
            "Barbell Squat", "Deadlift", "Bench Press", "Overhead Press",
            "Barbell Row", "Pull-ups", "Lat Pulldowns", "Dumbbell Press",
            "Lateral Raises", "Bicep Curls", "Tricep Pushdowns", "Leg Press",
            "Romanian Deadlift", "Face Pulls", "Planks", "Lunges",
            "Calf Raises", "Dips", "Push-ups", "Custom..."
        ]

        if 'current_exercises' not in st.session_state:
            st.session_state.current_exercises = []

        # Add new exercise
        with st.form("add_exercise", clear_on_submit=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                exercise_choice = st.selectbox("Exercise", common_exercises)
            with col2:
                num_sets = st.selectbox("Sets", [1, 2, 3, 4, 5], index=2)

            sets_data = []
            for i in range(num_sets):
                cols = st.columns(3)
                with cols[0]:
                    weight = st.number_input(f"Set {i+1} Weight (kg)", 0.0, 500.0, 20.0, key=f"weight_{i}_{len(st.session_state.current_exercises)}")
                with cols[1]:
                    reps = st.number_input(f"Set {i+1} Reps", 1, 30, 10, key=f"reps_{i}_{len(st.session_state.current_exercises)}")
                with cols[2]:
                    notes = st.text_input(f"Set {i+1} Notes", "", key=f"notes_{i}_{len(st.session_state.current_exercises)}")

                sets_data.append({"weight": weight, "reps": reps, "notes": notes})

            if st.form_submit_button("➕ Add Exercise", use_container_width=True):
                exercise_name = st.text_input("Custom name", exercise_choice) if exercise_choice == "Custom..." else exercise_choice
                st.session_state.current_exercises.append({
                    "name": exercise_name,
                    "sets": sets_data
                })
                st.rerun()

        # Show current exercises
        if st.session_state.current_exercises:
            st.markdown("---")
            st.subheader("Today's Exercises")

            for i, ex in enumerate(st.session_state.current_exercises):
                with st.container():
                    cols = st.columns([3, 1])
                    with cols[0]:
                        st.markdown(f"**{ex['name']}**")
                        for j, s in enumerate(ex["sets"]):
                            st.caption(f"Set {j+1}: {s['weight']}kg × {s['reps']} reps {f'({s[\"notes\"]})' if s['notes'] else ''}")
                    with cols[1]:
                        if st.button("🗑️", key=f"remove_{i}"):
                            st.session_state.current_exercises.pop(i)
                            st.rerun()

            st.markdown("---")

            if st.button("✅ Complete Workout", type="primary", use_container_width=True):
                result = gym_bro.log_workout(
                    exercises_data=st.session_state.current_exercises,
                    energy=energy,
                    sleep=sleep,
                    duration=duration
                )

                # Clear current exercises
                st.session_state.current_exercises = []

                # Show celebration
                st.balloons()

                # Show feedback
                st.success("Workout logged! 💪")

                with st.expander("📋 Workout Summary", expanded=True):
                    st.write(f"**Gym Bro says:** {result['feedback']}")
                    st.write(f"Total workouts logged: **{result['total_workouts']}**")

                    if result["new_prs"]:
                        st.markdown("### 🏆 NEW PERSONAL RECORDS!")
                        for pr in result["new_prs"]:
                            st.markdown(f"""
                            <div class="pr-badge">
                                <strong>{pr['exercise']}</strong>: +{pr['improvement']}% 
                                ({pr['old_est_1rm']}kg → {pr['new_est_1rm']}kg)
                            </div>
                            """, unsafe_allow_html=True)

                if gym_bro.nickname_for_you:
                    st.info(f"💪 Gym Bro now calls you: **{gym_bro.nickname_for_you}**!")

    # TAB 2: PROGRESS
    with tab2:
        st.header("Your Progress")

        progress = gym_bro.get_progress_summary()

        if isinstance(progress, dict) and "message" in progress:
            st.info(progress["message"])
        else:
            import plotly.graph_objects as go

            # Show progress for each exercise
            for exercise, data in progress.items():
                with st.expander(f"📈 {exercise}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Starting 1RM", f"{data['first_1rm']}kg")
                    with col2:
                        st.metric("Current 1RM", f"{data['current_1rm']}kg")
                    with col3:
                        st.metric("Change", f"{data['change_percent']}%", data['trend'])

                    # Progress chart
                    if exercise in gym_bro.exercise_progress:
                        history = gym_bro.exercise_progress[exercise]
                        dates = [h["date"][:10] for h in history]
                        rms = [h["estimated_1rm"] for h in history]

                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=dates, y=rms, mode='lines+markers', name='Est. 1RM'))
                        fig.update_layout(
                            title=f"{exercise} Progression",
                            xaxis_title="Date",
                            yaxis_title="Estimated 1RM (kg)",
                            height=300
                        )
                        st.plotly_chart(fig, use_container_width=True)

            # Achievements
            if gym_bro.achievements:
                st.markdown("---")
                st.subheader("🏆 Achievements")
                prs = [a for a in gym_bro.achievements if a["type"] == "PR"]
                if prs:
                    for pr in prs[-5:]:
                        st.write(f"• {pr['exercise']}: +{pr['improvement']}% on {pr['date'][:10]}")

    # TAB 3: NEXT SESSION
    with tab3:
        st.header("What's Next?")

        recommendation = gym_bro.get_next_session_recommendation()

        st.info(f"**Gym Bro says:** {recommendation['message']}")

        if "focus" in recommendation:
            st.subheader(f"🎯 {recommendation['focus']}")

        if "suggested_exercises" in recommendation:
            st.subheader("Suggested Workout:")

            for ex in recommendation["suggested_exercises"]:
                with st.container():
                    cols = st.columns([3, 1, 1, 1])
                    with cols[0]:
                        st.markdown(f"**{ex['name']}**")
                    with cols[1]:
                        st.caption(f"Sets: {ex['sets']}")
                    with cols[2]:
                        st.caption(f"Reps: {ex['reps']}")
                    with cols[3]:
                        st.caption(f"💡 {ex['weight_suggestion']}")

        if st.button("Start This Workout →", type="primary"):
            st.session_state.current_tab = "Workout"
            st.rerun()

    # TAB 4: CHAT WITH GYM BRO
    with tab4:
        st.header("Chat with Gym Bro")

        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        # Display chat
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"], avatar="💪" if msg["role"] == "assistant" else None):
                st.markdown(msg["content"])

        # Quick questions
        st.caption("Quick questions you can ask:")
        quick_questions = [
            "How do I improve my squat form?",
            "Am I making progress?",
            "What should I eat before a workout?",
            "How do I break through a plateau?",
            "Should I train if I'm sore?"
        ]

        cols = st.columns(len(quick_questions))
        for i, question in enumerate(quick_questions):
            with cols[i]:
                if st.button(question, key=f"q_{i}"):
                    st.session_state.chat_messages.append({"role": "user", "content": question})
                    response = gym_bro._generate_chat_response(question)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    st.rerun()

        # Chat input
        if prompt := st.chat_input("Ask Gym Bro anything..."):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            response = gym_bro._generate_chat_response(prompt)
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            st.rerun()

# Footer
st.markdown("---")
st.caption("💪 Gym Bro - Your AI Training Partner | We Go Jim! 🏋️")