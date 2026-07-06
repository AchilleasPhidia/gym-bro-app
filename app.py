# app.py - Gym Bro v4.1 (AI chat programs now update calendar)

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
                system_prompt = f"""You are Gym Bro, a supportive and knowledgeable gym coach. 
You give advice on exercises, form, nutrition, motivation, and programming.
Speak like a friendly bro: use 'bro', emojis, and hype.
Be encouraging but honest. Keep responses under 150 words unless you are providing a program.
{last_workout_context}

IMPORTANT: If the user asks you to create or update their workout program, you MUST respond with a valid JSON object wrapped in a code block like:
```json
{{
  "program_name": "...",
  "days": [
    {{"day": "Monday", "focus": "...", "exercises": [{{"name": "...", "sets": 3, "reps": "8-10", "notes": "..."}}]}}
  ]
}}