# app.py – Gym Bro X Final (Complete, robust AI, sticky nav, full edit)

import streamlit as st
import json, random, os, shutil, re
from datetime import datetime, timedelta, date
from typing import Dict, List
import plotly.graph_objects as go
from openai import OpenAI
from tools import search_exercises, analyze_form, parse_program_payload, normalize_exercises
from gym_knowledge import get_knowledge_text

# ============================================
# HELPERS
# ============================================
def get_existing_users():
    if not os.path.exists("user_data"): return []
    return sorted([d for d in os.listdir("user_data") if os.path.isdir(os.path.join("user_data", d))])

def delete_user_folder(username):
    folder = os.path.join("user_data", username)
    if os.path.exists(folder):
        shutil.rmtree(folder)
        return True
    return False

def init_set_state():
    for i in range(5):
        for prefix in ["w_", "r_", "n_"]:
            key = f"{prefix}{i}"
            if key not in st.session_state:
                if prefix == "w_": st.session_state[key] = 20.0
                elif prefix == "r_": st.session_state[key] = 10
                else: st.session_state[key] = ""

# ============================================
# GYM BRO CLASS (full power, memory, learning)
# ============================================
class GymBro:
    def __init__(self, username="default"):
        self.username = username
        self.data_dir = f"user_data/{username}"
        os.makedirs(self.data_dir, exist_ok=True)

        for fname in ["workouts.json","progress.json","achievements.json",
                      "custom_exercises.json","user_profile.json",
                      "current_program.json","body_measurements.json",
                      "chat_history.json","learned_knowledge.json"]:
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
            with open(path, 'r') as f: return json.load(f)
        except: return default

    def _save_json(self, filename, data):
        path = os.path.join(self.data_dir, filename)
        with open(path, 'w') as f: json.dump(data, f, indent=2, default=str)

    # ---------- Profile ----------
    def setup_profile(self, data):
        self.profile = {**data,
            "created": self.profile.get("created", datetime.now().isoformat()),
            "last_updated": datetime.now().isoformat()}
        self._save_json("user_profile.json", self.profile)

    def add_body_measurement(self, weight, body_fat=None, notes=""):
        self.body_measurements.append({
            "date": datetime.now().isoformat(), "weight": weight,
            "body_fat": body_fat, "notes": notes})
        self._save_json("body_measurements.json", self.body_measurements)

    def get_profile_context(self) -> str:
        if not self.profile: return "No profile."
        p = self.profile
        ctx = []
        if p.get("age"): ctx.append(f"Age: {p['age']}")
        if p.get("gender"): ctx.append(f"Gender: {p['gender']}")
        if p.get("height"): ctx.append(f"Height: {p['height']}cm")
        if self.body_measurements:
            w = self.body_measurements[-1]["weight"]
            ctx.append(f"Weight: {w}kg")
            if self.body_measurements[-1].get("body_fat"):
                ctx.append(f"Body fat: {self.body_measurements[-1]['body_fat']}%")
        ctx.append(f"Experience: {p.get('experience','?')} | Days/week: {p.get('training_days','?')} | Session: {p.get('session_length','?')}")
        if p.get("resting_heart_rate"): ctx.append(f"Resting HR: {p['resting_heart_rate']}")
        if p.get("primary_goal"): ctx.append(f"Goal: {p['primary_goal']}")
        if p.get("target_weight"): ctx.append(f"Target weight: {p['target_weight']}kg")
        if p.get("strength_goals"): ctx.append(f"Strength goals: {p['strength_goals']}")
        if p.get("diet_type"): ctx.append(f"Diet: {p['diet_type']}")
        if p.get("allergies"): ctx.append(f"Allergies: {p['allergies']}")
        if p.get("meals_per_day"): ctx.append(f"Meals/day: {p['meals_per_day']}")
        if p.get("sleep_hours"): ctx.append(f"Sleep: {p['sleep_hours']}h")
        if p.get("job_activity"): ctx.append(f"Activity: {p['job_activity']}")
        if p.get("stress_level"): ctx.append(f"Stress: {p['stress_level']}/10")
        if p.get("equipment"): ctx.append(f"Equipment: {', '.join(p['equipment'])}")
        if p.get("injuries"): ctx.append(f"Injuries: {p['injuries']}")
        return "\n".join(ctx)

    def get_recent_workouts_context(self, n=5):
        if not self.workouts: return "No workouts yet."
        recent = self.workouts[-n:]
        lines = []
        for w in recent:
            date = w["date"][:10]
            exs = ", ".join([f"{e['name']} ({len(e['sets'])}x)" for e in w["exercises"]])
            lines.append(f"{date}: {exs}")
        return "\n".join(lines)

    # ---------- Program Generation ----------
    def generate_program(self, use_openai=True):
        if not self.profile: return None
        if use_openai:
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
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.7, max_tokens=1500
                    )
                    prog, _ = parse_program_payload(response.choices[0].message.content)
                    if prog:
                        self.current_program = prog
                        self._save_json("current_program.json", prog)
                        return prog
            except: pass

        # Offline fallback
        days = self.profile.get('training_days', 4)
        days_map = {2: ["Monday","Thursday"], 3: ["Monday","Wednesday","Friday"],
                    4: ["Monday","Tuesday","Thursday","Friday"],
                    5: ["Monday","Tuesday","Wednesday","Thursday","Friday"]}
        day_names = days_map.get(days, ["Monday","Wednesday","Friday"])
        program = {"program_name":"Custom Plan","days":[]}
        for i,d in enumerate(day_names):
            if i%2==0:
                focus="Upper Body"
                exercises=[{"name":"Bench Press","sets":3,"reps":"8-10","notes":"Focus on control"},
                           {"name":"Barbell Row","sets":3,"reps":"8-10","notes":"Squeeze at top"},
                           {"name":"Overhead Press","sets":3,"reps":"10-12","notes":""},
                           {"name":"Face Pulls","sets":3,"reps":"15-20","notes":"Light, perfect form"}]
            else:
                focus="Lower Body"
                exercises=[{"name":"Barbell Squat","sets":3,"reps":"8-10","notes":"Depth over weight"},
                           {"name":"Romanian Deadlift","sets":3,"reps":"10-12","notes":"Hamstring stretch"},
                           {"name":"Leg Press","sets":3,"reps":"12-15","notes":"Constant tension"},
                           {"name":"Calf Raises","sets":4,"reps":"15-20","notes":""}]
            program["days"].append({"day":d,"focus":focus,"exercises":exercises})
        self.current_program = program
        self._save_json("current_program.json", program)
        return program

    # ---------- Workout Logging ----------
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
            name = ex.get("name","?")
            sets = ex.get("sets",[])
            valid = [s for s in sets if isinstance(s,dict) and s.get("weight",0)>0 and s.get("reps",0)>0]
            if not valid: continue
            if name not in self.exercise_progress:
                self.exercise_progress[name] = []
            vol = sum(s["weight"]*s["reps"] for s in valid)
            best = max(valid, key=lambda s: s["weight"]*(1+s["reps"]/30))
            est1rm = best["weight"]*(1+best["reps"]/30)
            self.exercise_progress[name].append({
                "date": datetime.now().isoformat(), "volume": vol,
                "estimated_1rm": round(est1rm,1)
            })
        self._save_json("progress.json", self.exercise_progress)
        prs = self._check_prs(exercises_data)
        return {
            "feedback": self._generate_feedback(workout),
            "new_prs": prs,
            "total_workouts": len(self.workouts)
        }

    def _check_prs(self, exercises_data):
        prs = []
        for ex in exercises_data:
            name = ex.get("name")
            if not name or name not in self.exercise_progress or len(self.exercise_progress[name])<2: continue
            sets = ex.get("sets",[])
            valid = [s for s in sets if isinstance(s,dict) and s.get("weight",0)>0]
            if not valid: continue
            cur = max(s["weight"]*(1+s["reps"]/30) for s in valid)
            prev = max(e["estimated_1rm"] for e in self.exercise_progress[name][:-1]) if self.exercise_progress[name][:-1] else 0
            if prev>0 and cur>prev*1.01:
                imp = round((cur-prev)/prev*100,1)
                prs.append({"exercise":name,"old_est_1rm":round(prev,1),"new_est_1rm":round(cur,1),"improvement":imp})
                self.achievements.append({"type":"PR","exercise":name,"date":datetime.now().isoformat(),"improvement":imp})
        self._save_json("achievements.json", self.achievements)
        return prs

    def _generate_feedback(self, workout):
        total_vol = sum(sum(s.get("weight",0)*s.get("reps",0) for s in ex.get("sets",[])) for ex in workout["exercises"])
        fb = []
        if total_vol>10000: fb.append("Bro, you moved SERIOUS weight! 💪")
        elif total_vol>5000: fb.append("Solid volume! 🏗️")
        else: fb.append("Good work, every rep counts! 🎯")
        if workout.get("energy_level",0)>=8: fb.append("Energy was HIGH! ⚡")
        elif workout.get("energy_level",0)>=5: fb.append("Good energy bro! 👊")
        else: fb.append("You showed up – mental toughness! 🧠")
        if workout.get("sleep_quality",0)<=5: fb.append("Get more sleep tonight! 😴")
        return " ".join(fb)

    def get_streak_info(self):
        if not self.workouts: return {"current":0,"longest":0,"week":0}
        wdates = sorted({datetime.fromisoformat(w["date"]).date() for w in self.workouts}, reverse=True)
        today = date.today()
        cur=0
        for d in wdates:
            if d==today-timedelta(days=cur): cur+=1
            else: break
        best=temp=0
        all_d=sorted(wdates)
        for i,d in enumerate(all_d):
            if i==0 or d==all_d[i-1]+timedelta(days=1): temp+=1; best=max(best,temp)
            else: temp=1
        week=sum(1 for d in [today-timedelta(days=i) for i in range(7)] if d in wdates)
        return {"current":cur,"longest":best,"week":week}

    def get_progress(self):
        if not self.exercise_progress: return None
        summary={}
        for ex,hist in self.exercise_progress.items():
            if len(hist)>0:
                last=hist[-1]["estimated_1rm"]
                first=hist[0]["estimated_1rm"] if len(hist)>=2 else last
                change=round((last-first)/first*100,1) if first>0 else 0
                summary[ex]={"first":round(first,1),"current":round(last,1),"sessions":len(hist),"change":change,"trend":"📈" if change>0 else "📉" if change<0 else "➡️"}
        return summary

    def get_weight_progress(self):
        if not self.body_measurements: return None
        return {"dates":[m["date"][:10] for m in self.body_measurements],
                "weights":[m["weight"] for m in self.body_measurements],
                "body_fats":[m.get("body_fat") for m in self.body_measurements]}

    def save_chat_message(self, role, content):
        self.chat_history.append({"role":role,"content":content,"timestamp":datetime.now().isoformat()})
        self._save_json("chat_history.json", self.chat_history)

    def add_learned_knowledge(self, fact):
        self.learned_knowledge.append({"fact":fact,"timestamp":datetime.now().isoformat()})
        self._save_json("learned_knowledge.json", self.learned_knowledge)

    def get_learned_knowledge_text(self):
        if not self.learned_knowledge: return ""
        return "Learned:\n" + "\n".join(f"- {k['fact']}" for k in self.learned_knowledge[-30:])

# ============================================
# LANDING PAGE
# ============================================
st.set_page_config(page_title="Gym Bro X", page_icon="💎", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("💎 Gym Bro X")
    st.subheader("Your AI Personal Trainer")
    existing_users = get_existing_users()
    col1, col2 = st.columns([2,1])
    with col1:
        if existing_users:
            st.write("### Select your profile")
            cols = st.columns(min(len(existing_users), 3))
            for i, user in enumerate(existing_users):
                with cols[i % 3]:
                    if st.button(f"👤 {user}", use_container_width=True, key=f"user_{user}"):
                        st.session_state.selected_user = user
                        st.session_state.gym_bro = GymBro(user)
                        st.session_state.current_user = user
                        st.session_state.show_intro = False
                        st.session_state.current_exercises = []
                        st.session_state.chat_messages = []
                        init_set_state()
                        st.session_state.logged_in = True
                        st.session_state.current_page = "👤 Profile"
                        st.rerun()
        else:
            st.info("No users yet. Create your first profile!")
    with col2:
        st.write("### Or create a new user")
        new_user = st.text_input("Enter username", placeholder="e.g. IronWarrior")
        if st.button("Create profile", use_container_width=True, type="primary"):
            if new_user and new_user not in get_existing_users():
                st.session_state.selected_user = new_user
                st.session_state.gym_bro = GymBro(new_user)
                st.session_state.current_user = new_user
                st.session_state.show_intro = True
                st.session_state.current_exercises = []
                st.session_state.chat_messages = []
                init_set_state()
                st.session_state.logged_in = True
                st.session_state.current_page = "👤 Profile"
                st.rerun()
            elif new_user in get_existing_users():
                st.warning("User already exists. Select from the left.")
    st.stop()

# ============================================
# MAIN APP
# ============================================
gym_bro = st.session_state.gym_bro
username = st.session_state.current_user
init_set_state()

# ---------- Profile Setup ----------
if not gym_bro.profile:
    with st.form("profile_setup"):
        st.subheader("Let's build your profile, bro! 💪")
        col1, col2, col3 = st.columns(3)
        with col1: age = st.number_input("Age",10,100,25)
        with col2: gender = st.selectbox("Gender",["Male","Female","Other","Prefer not to say"])
        with col3: height = st.number_input("Height (cm)",100,250,175)
        col1, col2 = st.columns(2)
        with col1: weight = st.number_input("Weight (kg)",30.0,300.0,75.0)
        with col2: body_fat = st.number_input("Body fat % (optional)",0.0,60.0,0.0,step=0.1)
        st.markdown("---")
        st.markdown("### 🏃 Training")
        col1, col2 = st.columns(2)
        with col1:
            experience = st.selectbox("Experience",["Beginner","Intermediate","Advanced"])
            training_days = st.slider("Days/week",1,7,4)
        with col2:
            session_length = st.selectbox("Session length",["30 min","45 min","60 min","75 min","90 min"],index=2)
            include_hr = st.checkbox("I know my resting HR")
            resting_hr = None
            if include_hr: resting_hr = st.number_input("Resting HR",30,120,60)
        st.markdown("### 🎯 Goals")
        col1, col2 = st.columns(2)
        with col1:
            primary_goal = st.selectbox("Primary goal",["Build muscle","Lose fat","Get stronger","Improve endurance","Tone up","General fitness","Sport-specific","Rehabilitation"])
            target_weight = st.number_input("Target weight (optional)",0.0,300.0,0.0)
        with col2:
            strength_goals = st.text_area("Strength goals",placeholder="Bench 100kg, etc.")
            timeline = st.selectbox("Timeline",["No rush","3 months","6 months","1 year"])
        st.markdown("### 🥗 Nutrition")
        col1, col2, col3 = st.columns(3)
        with col1: diet_type = st.selectbox("Diet",["No special","Vegan","Vegetarian","Keto","Paleo","Mediterranean","High protein","IF"])
        with col2: allergies = st.text_input("Allergies")
        with col3: meals_per_day = st.selectbox("Meals/day",[2,3,4,5,6],index=1)
        st.markdown("### 🌙 Lifestyle")
        col1, col2, col3 = st.columns(3)
        with col1: sleep_hours = st.number_input("Sleep (hours)",3.0,12.0,7.0,0.5)
        with col2: job_activity = st.selectbox("Activity level",["Sedentary","Lightly active","Moderately active","Very active"])
        with col3: stress = st.slider("Stress level",1,10,5)
        st.markdown("### 🏋️ Equipment & Health")
        col1, col2 = st.columns(2)
        with col1: equipment = st.multiselect("Equipment",["Full gym","Barbell","Dumbbells","Cables","Machines","Bodyweight","Bands","Kettlebells","Pull-up bar","Bench","Squat rack"],default=["Full gym"])
        with col2: injuries = st.text_area("Injuries / limitations"); focus_areas = st.multiselect("Focus areas",["Chest","Back","Legs","Shoulders","Arms","Core","Overall"],default=["Overall"])
        if st.form_submit_button("🚀 Create Profile & Program"):
            profile_data = {"age":age,"gender":gender,"height":height,"experience":experience,"training_days":training_days,"session_length":session_length,"resting_heart_rate":resting_hr,"primary_goal":primary_goal,"target_weight":target_weight if target_weight>0 else None,"strength_goals":strength_goals,"timeline":timeline,"diet_type":diet_type,"allergies":allergies,"meals_per_day":meals_per_day,"sleep_hours":sleep_hours,"job_activity":job_activity,"stress_level":stress,"equipment":equipment,"injuries":injuries,"focus_areas":focus_areas}
            gym_bro.setup_profile(profile_data)
            if weight>0: gym_bro.add_body_measurement(weight, body_fat if body_fat>0 else None, "Initial")
            gym_bro.generate_program()
            st.session_state.show_intro = False; st.rerun()
    st.stop()

# ---------- Sticky Top Navigation ----------
st.markdown("""
<style>
.sticky-nav {
    position: sticky;
    top: 0;
    z-index: 9999;
    background: #0f0c29;
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

if "current_page" not in st.session_state:
    st.session_state.current_page = "👤 Profile"

st.markdown('<div class="sticky-nav">', unsafe_allow_html=True)
cols = st.columns(5)
pages = ["👤 Profile", "💪 Log Workout", "📊 Progress", "🎯 My Program", "🤖 AI Chat"]
for idx, page_name in enumerate(pages):
    with cols[idx]:
        if st.button(page_name, key=f"nav_{page_name}", use_container_width=True,
                     type="primary" if st.session_state.current_page == page_name else "secondary"):
            st.session_state.current_page = page_name
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

page = st.session_state.current_page

# ---------- Sidebar ----------
with st.sidebar:
    st.title("Gym Bro X")
    st.markdown(f"Logged in as **{username}**")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.markdown("---")
    if gym_bro.profile:
        streak = gym_bro.get_streak_info()
        c1,c2,c3 = st.columns(3)
        c1.metric("🔥", streak["current"])
        c2.metric("👑", streak["longest"])
        c3.metric("📅", f"{streak['week']}/7")

    st.markdown("---")
    if "delete_mode" not in st.session_state:
        st.session_state.delete_mode = False
    if not st.session_state.delete_mode:
        if st.button("🗑️ Delete my account"):
            st.session_state.delete_mode = True
            st.rerun()
    else:
        st.warning(f"Permanently delete **{username}** and all data?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, delete", type="primary"):
                if delete_user_folder(username):
                    st.session_state.logged_in = False
                    st.session_state.delete_mode = False
                    st.rerun()
        with col2:
            if st.button("Cancel"):
                st.session_state.delete_mode = False
                st.rerun()

# ---------- Main Content ----------
if page == "👤 Profile":
    st.header("Your Profile")
    p = gym_bro.profile
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Age:** {p.get('age','?')}")
        st.markdown(f"**Height:** {p.get('height','?')} cm")
    with col2:
        st.markdown(f"**Gender:** {p.get('gender','?')}")
        w = gym_bro.body_measurements[-1]["weight"] if gym_bro.body_measurements else '?'
        st.markdown(f"**Weight:** {w} kg")
    with col3:
        st.markdown(f"**Goal:** {p.get('primary_goal','?')}")
        st.markdown(f"**Experience:** {p.get('experience','?')}")
    if st.button("✏️ Edit Full Profile"):
        st.session_state.edit_profile = True
    if st.session_state.get("edit_profile"):
        with st.form("edit_profile_form"):
            age = st.number_input("Age",10,100,p.get("age",25))
            gender = st.selectbox("Gender",["Male","Female","Other","Prefer not to say"],
                                  index=["Male","Female","Other","Prefer not to say"].index(p.get("gender","Male")))
            height = st.number_input("Height (cm)",100,250,p.get("height",175))
            w_last = gym_bro.body_measurements[-1]["weight"] if gym_bro.body_measurements else 75.0
            bf_last = gym_bro.body_measurements[-1].get("body_fat",0.0) if gym_bro.body_measurements else 0.0
            weight = st.number_input("Weight (kg)",30.0,300.0,w_last)
            body_fat = st.number_input("Body fat %",0.0,60.0,bf_last,step=0.1)
            experience = st.selectbox("Experience",["Beginner","Intermediate","Advanced"],
                                      index=["Beginner","Intermediate","Advanced"].index(p.get("experience","Beginner")))
            training_days = st.slider("Days/week",1,7,p.get("training_days",4))
            session_length = st.selectbox("Session length",["30 min","45 min","60 min","75 min","90 min"],
                                          index=["30 min","45 min","60 min","75 min","90 min"].index(p.get("session_length","60 min")))
            include_hr = st.checkbox("Resting HR",value=bool(p.get("resting_heart_rate")))
            resting_hr = None
            if include_hr: resting_hr = st.number_input("Resting HR",30,120,p.get("resting_heart_rate") or 60)
            primary_goal = st.selectbox("Primary goal",["Build muscle","Lose fat","Get stronger","Improve endurance","Tone up","General fitness","Sport-specific","Rehabilitation"],
                                        index=["Build muscle","Lose fat","Get stronger","Improve endurance","Tone up","General fitness","Sport-specific","Rehabilitation"].index(p.get("primary_goal","Build muscle")))
            target_weight = st.number_input("Target weight",0.0,300.0,p.get("target_weight") or 0.0)
            strength_goals = st.text_area("Strength goals",value=p.get("strength_goals",""))
            timeline = st.selectbox("Timeline",["No rush","3 months","6 months","1 year"],
                                    index=["No rush","3 months","6 months","1 year"].index(p.get("timeline","No rush")))
            diet_type = st.selectbox("Diet",["No special","Vegan","Vegetarian","Keto","Paleo","Mediterranean","High protein","IF"],
                                     index=["No special","Vegan","Vegetarian","Keto","Paleo","Mediterranean","High protein","IF"].index(p.get("diet_type","No special")))
            allergies = st.text_input("Allergies",value=p.get("allergies",""))
            meals_per_day = st.selectbox("Meals/day",[2,3,4,5,6],index=[2,3,4,5,6].index(p.get("meals_per_day",3)))
            sleep_hours = st.number_input("Sleep (hours)",3.0,12.0,p.get("sleep_hours",7.0),0.5)
            job_activity = st.selectbox("Activity level",["Sedentary","Lightly active","Moderately active","Very active"],
                                        index=["Sedentary","Lightly active","Moderately active","Very active"].index(p.get("job_activity","Sedentary")))
            stress = st.slider("Stress level",1,10,p.get("stress_level",5))
            equipment = st.multiselect("Equipment",["Full gym","Barbell","Dumbbells","Cables","Machines","Bodyweight","Bands","Kettlebells","Pull-up bar","Bench","Squat rack"],
                                       default=p.get("equipment",["Full gym"]))
            injuries = st.text_area("Injuries",value=p.get("injuries",""))
            focus_areas = st.multiselect("Focus areas",["Chest","Back","Legs","Shoulders","Arms","Core","Overall"],
                                         default=p.get("focus_areas",["Overall"]))
            if st.form_submit_button("💾 Save Full Profile"):
                new_profile = {"age":age,"gender":gender,"height":height,"experience":experience,"training_days":training_days,"session_length":session_length,"resting_heart_rate":resting_hr,"primary_goal":primary_goal,"target_weight":target_weight if target_weight>0 else None,"strength_goals":strength_goals,"timeline":timeline,"diet_type":diet_type,"allergies":allergies,"meals_per_day":meals_per_day,"sleep_hours":sleep_hours,"job_activity":job_activity,"stress_level":stress,"equipment":equipment,"injuries":injuries,"focus_areas":focus_areas}
                gym_bro.setup_profile(new_profile)
                gym_bro.add_body_measurement(weight, body_fat if body_fat>0 else None, "Profile update")
                gym_bro.generate_program()
                st.session_state.edit_profile = False; st.rerun()
    if len(gym_bro.body_measurements)>1:
        wd = gym_bro.get_weight_progress()
        if wd:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=wd["dates"],y=wd["weights"],mode='lines+markers',name='Weight'))
            if any(bf is not None for bf in wd["body_fats"]):
                fig.add_trace(go.Scatter(x=wd["dates"],y=wd["body_fats"],mode='lines+markers',name='Body Fat %',yaxis='y2'))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True, key="weight_chart")

elif page == "💪 Log Workout":
    st.header("Log Workout")
    col1,col2,col3 = st.columns(3)
    energy = col1.slider("⚡ Energy",1,10,7)
    sleep = col2.slider("😴 Sleep",1,10,7)
    duration = col3.number_input("⏱️ Minutes",15,180,45)
    common_ex = ["Barbell Squat","Deadlift","Bench Press","Overhead Press","Barbell Row","Pull-ups","Lat Pulldowns","Dumbbell Press","Lateral Raises","Bicep Curls","Tricep Pushdowns","Leg Press","Romanian Deadlift","Face Pulls","Planks","Lunges","Calf Raises","Dips","Push-ups"]
    all_ex = common_ex + gym_bro.custom_exercises
    mode = st.radio("Select or custom",["📋 List","✏️ Custom"],horizontal=True)
    if mode.startswith("📋"): ex_name = st.selectbox("Exercise",all_ex)
    else:
        ex_name = st.text_input("Exercise name")
        if ex_name and ex_name not in gym_bro.custom_exercises:
            if st.button("Save custom"): gym_bro.custom_exercises.append(ex_name); gym_bro._save_json("custom_exercises.json",gym_bro.custom_exercises); st.success(f"Saved {ex_name}!")
    num_sets = st.selectbox("Sets",[1,2,3,4,5],index=2)
    sets_data = []
    w0 = st.number_input("Set 1 Weight (kg)",0.0,500.0,st.session_state.w_0,key="w_0")
    r0 = st.number_input("Set 1 Reps",1,30,st.session_state.r_0,key="r_0")
    n0 = st.text_input("Set 1 Notes",st.session_state.n_0,key="n_0")
    sets_data.append({"weight":w0,"reps":r0,"notes":n0})
    if num_sets>1:
        if st.button("⬇️ Apply to all"):
            for i in range(1,num_sets): st.session_state[f"w_{i}"]=w0; st.session_state[f"r_{i}"]=r0; st.session_state[f"n_{i}"]=n0
            st.rerun()
    for i in range(1,num_sets):
        w = st.number_input(f"Set {i+1} Weight",0.0,500.0,st.session_state[f"w_{i}"],key=f"w_{i}")
        r = st.number_input(f"Set {i+1} Reps",1,30,st.session_state[f"r_{i}"],key=f"r_{i}")
        n = st.text_input(f"Set {i+1} Notes",st.session_state[f"n_{i}"],key=f"n_{i}")
        sets_data.append({"weight":w,"reps":r,"notes":n})
    if st.button("➕ Add to workout"):
        st.session_state.current_exercises.append({"name":ex_name,"sets":sets_data})
        for i in range(5): st.session_state[f"w_{i}"]=20.0; st.session_state[f"r_{i}"]=10; st.session_state[f"n_{i}"]=""
        st.rerun()
    if st.session_state.current_exercises:
        for i,ex in enumerate(st.session_state.current_exercises):
            st.markdown(f"**{ex['name']}**")
            for j,s in enumerate(ex["sets"]): st.caption(f"Set {j+1}: {s['weight']}kg × {s['reps']}")
            if st.button("🗑️",key=f"del_{i}"): st.session_state.current_exercises.pop(i); st.rerun()
        if st.button("✅ Complete Workout",type="primary"):
            result = gym_bro.log_workout(st.session_state.current_exercises,energy,sleep,duration)
            st.session_state.current_exercises = []
            st.balloons()
            st.success(result["feedback"])
            if result["new_prs"]:
                for pr in result["new_prs"]: st.markdown(f"🏆 {pr['exercise']}: +{pr['improvement']}%")

elif page == "📊 Progress":
    st.header("Progress")
    progress = gym_bro.get_progress()
    if not progress: st.info("Log workouts to see progress!")
    else:
        for ex,data in progress.items():
            with st.expander(f"{ex} ({data['sessions']} sessions)"):
                c1,c2,c3 = st.columns(3)
                c1.metric("Best",f"{data['current']}kg")
                c2.metric("First",f"{data['first']}kg")
                c3.metric("Change",f"{data['change']}%",data['trend'])
                if ex in gym_bro.exercise_progress:
                    hist = gym_bro.exercise_progress[ex]
                    fig = go.Figure(go.Scatter(x=[h["date"][:10] for h in hist],y=[h["estimated_1rm"] for h in hist],mode='lines+markers'))
                    fig.update_layout(height=250)
                    st.plotly_chart(fig, use_container_width=True, key=f"prog_{ex}")

elif page == "🎯 My Program":
    st.header("My Program")
    if not gym_bro.current_program:
        if st.button("Generate Program"): gym_bro.generate_program(); st.rerun()
    else:
        prog = gym_bro.current_program
        st.subheader(prog.get("program_name","Plan"))
        for d in prog["days"]:
            with st.expander(f"{d['day']} – {d['focus']}"):
                for ex in d["exercises"]: st.write(f"• {ex['name']} {ex['sets']}×{ex['reps']} {ex.get('notes','')}")
        if st.button("🔄 Regenerate"): gym_bro.generate_program(); st.rerun()

elif page == "🤖 AI Chat":
    st.header("💬 AI Coach")
    if "chat_messages" not in st.session_state: st.session_state.chat_messages = []
    if gym_bro.chat_history and len(st.session_state.chat_messages)==0:
        for msg in gym_bro.chat_history[-500:]:
            st.session_state.chat_messages.append({"role":msg["role"],"content":msg["content"]})
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    profile_txt = gym_bro.get_profile_context()
    recent_wos = gym_bro.get_recent_workouts_context(5)
    progress_summary = json.dumps(gym_bro.get_progress()) if gym_bro.get_progress() else "None"
    knowledge = get_knowledge_text()
    learned = gym_bro.get_learned_knowledge_text()

    system_prompt = f"""You are Gym Bro X, an expert AI coach with full memory.

USER PROFILE:
{profile_txt}

RECENT WORKOUTS:
{recent_wos}

STRENGTH PROGRESS:
{progress_summary}

KNOWLEDGE:
{knowledge}

{learned}

Tools:
- create_program(program_json)
- log_todays_workout(exercises)
- search_web(query)
- save_learned_knowledge(fact)

When the user asks for a program change, ALWAYS use create_program. Output ONLY the JSON inside the function call. Ensure all strings are properly escaped. Each day must have a 'focus' and an 'exercises' array. Each exercise must have 'name', 'sets' (number), 'reps' (string like "8-10"), and optional 'notes'."""

    functions = [
        {"name":"create_program","description":"Create/update workout program.","parameters":{"type":"object","properties":{"program_json":{"type":"string","description":"Full program JSON"}},"required":["program_json"]}},
        {"name":"log_todays_workout","description":"Log a completed workout.","parameters":{"type":"object","properties":{"exercises":{"type":"string","description":"JSON array of exercises"}},"required":["exercises"]}},
        {"name":"search_web","description":"Search the internet.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}},
        {"name":"save_learned_knowledge","description":"Save a fact.","parameters":{"type":"object","properties":{"fact":{"type":"string"}},"required":["fact"]}}
    ]

    if prompt := st.chat_input("Ask anything..."):
        st.session_state.chat_messages.append({"role":"user","content":prompt})
        gym_bro.save_chat_message("user",prompt)
        with st.spinner("Thinking..."):
            try:
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                messages = [{"role":"system","content":system_prompt}]
                messages.extend(st.session_state.chat_messages[-60:])
                response = client.chat.completions.create(
                    model="gpt-4-turbo", messages=messages, functions=functions,
                    function_call="auto", temperature=0.8, max_tokens=1000
                )
                msg = response.choices[0].message
                if msg.function_call:
                    fc = msg.function_call
                    raw_args = fc.arguments
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        repaired = raw_args
                        repaired = re.sub(r'(?<!\\)"', r'\\"', repaired)
                        repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
                        try:
                            args = json.loads(repaired)
                        except:
                            st.session_state.chat_messages.append({"role":"assistant","content":f"Sorry bro, couldn't process that. Raw: {raw_args[:200]}"})
                            st.rerun()

                    if fc.name == "create_program":
                        program_json_str = args.get("program_json", "")
                        if not program_json_str and "program_name" in args:
                            program_json_str = json.dumps(args)
                        prog, err = parse_program_payload(program_json_str)
                        if prog:
                            gym_bro.current_program = prog
                            gym_bro._save_json("current_program.json", prog)
                            reply = "✅ Program updated! Check your calendar."
                        else:
                            reply = f"Couldn't update program: {err}"
                    elif fc.name == "log_todays_workout":
                        try:
                            raw_exercises = args.get("exercises", "[]")
                            try: exercises = json.loads(raw_exercises)
                            except: exercises = json.loads(re.sub(r'(?<!\\)"',r'\\"',raw_exercises))
                            if not isinstance(exercises, list): raise ValueError("List required")
                            clean = []
                            for ex in exercises:
                                if not isinstance(ex, dict): continue
                                name = ex.get("name","Unknown")
                                sets = ex.get("sets",[])
                                if not isinstance(sets, list): sets=[]
                                valid = [s for s in sets if isinstance(s,dict) and s.get("weight",0)>0]
                                if valid: clean.append({"name":name,"sets":valid})
                            if not clean: raise ValueError("No valid exercises")
                            result = gym_bro.log_workout(clean, 7, 7, 60)
                            reply = f"Workout logged! {result['feedback']}"
                        except Exception as e:
                            reply = f"Couldn't log workout: {e}"
                    elif fc.name == "search_web":
                        query = args.get("query", "")
                        results = search_exercises(query)
                        reply = f"Search results:\n{results}"
                        if results and "Link:" in results:
                            gym_bro.add_learned_knowledge(f"From search '{query}': {results[:200]}")
                    elif fc.name == "save_learned_knowledge":
                        gym_bro.add_learned_knowledge(args.get("fact", ""))
                        reply = f"🧠 Learned: {args['fact']}"
                    else:
                        reply = "Unknown function."
                    st.session_state.chat_messages.append({"role":"assistant","content":reply})
                    gym_bro.save_chat_message("assistant", reply)
                else:
                    # Fallback: detect program JSON directly in text
                    prog, _ = parse_program_payload(msg.content)
                    if prog:
                        gym_bro.current_program = prog
                        gym_bro._save_json("current_program.json", prog)
                        reply = "✅ Program updated from your message! Check the Calendar."
                    else:
                        reply = msg.content
                    st.session_state.chat_messages.append({"role":"assistant","content":reply})
                    gym_bro.save_chat_message("assistant", reply)
            except Exception as e:
                st.session_state.chat_messages.append({"role":"assistant","content":f"Error: {e}"})
            st.rerun()

st.markdown("---")
st.caption(f"Gym Bro X | User: {username} | We go jim! 💎")