# gym_knowledge.py – Gym Bro X Final

EXERCISE_DB = {
    "barbell_back_squat": {
        "name": "Barbell Back Squat",
        "primary": ["quadriceps", "glutes"],
        "secondary": ["hamstrings", "erector spinae", "core", "adductors"],
        "form_cues": [
            "Bar on upper traps, not neck",
            "Chest up, shoulders back",
            "Feet shoulder-width, toes slightly out",
            "Knees track over toes",
            "Depth: hip crease below knee",
            "Drive through midfoot"
        ],
        "common_mistakes": [
            "Knees caving in – strengthen glute medius, use band around knees",
            "Heels lifting – improve ankle mobility, weightlifting shoes",
            "Butt wink – reduce depth, improve hip mobility, brace core"
        ],
        "progressions": ["goblet squat", "box squat", "front squat"],
        "regressions": ["leg press", "bulgarian split squat", "bodyweight squat"]
    },
    "deadlift_conventional": {
        "name": "Conventional Deadlift",
        "primary": ["erector spinae", "glutes", "hamstrings"],
        "secondary": ["traps", "lats", "forearms", "core", "quadriceps"],
        "form_cues": [
            "Bar over midfoot, touching shins",
            "Shoulders slightly in front of bar",
            "Hips not too low (not a squat)",
            "Arms straight, lats engaged",
            "Take slack out of bar before pulling",
            "Push floor away, don't pull bar up",
            "Lockout: squeeze glutes, don't hyperextend"
        ]
    },
    "bench_press": {
        "name": "Barbell Bench Press",
        "primary": ["pectoralis major", "anterior deltoid", "triceps brachii"],
        "secondary": ["serratus anterior", "biceps (short head)"],
        "form_cues": [
            "Retract shoulder blades",
            "Slight arch in lower back",
            "Feet planted firmly",
            "Lower bar to lower chest",
            "Drive bar up and slightly back"
        ],
        "common_mistakes": [
            "Flaring elbows – tuck elbows at 45°",
            "Bouncing off chest – controlled descent",
            "Uneven lockout – strengthen weaker side"
        ]
    },
    "overhead_press": {
        "name": "Overhead Press",
        "primary": ["anterior deltoid", "medial deltoid", "triceps brachii"],
        "secondary": ["upper chest", "traps", "core"],
        "form_cues": [
            "Bar at collarbone height",
            "Elbows slightly in front of bar",
            "Press bar straight up, move head back",
            "Lockout with head through"
        ]
    },
    "pull_up": {
        "name": "Pull-up",
        "primary": ["latissimus dorsi", "biceps brachii"],
        "secondary": ["traps", "rhomboids", "core"],
        "form_cues": [
            "Dead hang start",
            "Pull shoulder blades down and together",
            "Lead with chest, not chin",
            "Full range: chin over bar, arms straight at bottom"
        ]
    },
    "barbell_row": {
        "name": "Barbell Row",
        "primary": ["latissimus dorsi", "traps", "rhomboids"],
        "secondary": ["biceps", "rear delts", "erector spinae"],
        "form_cues": [
            "Hinge at hips, back flat",
            "Pull bar to lower chest",
            "Squeeze shoulder blades at top"
        ]
    }
}

TRAINING_PRINCIPLES = {
    "progressive_overload": "Gradually increase weight, reps, sets, or decrease rest. Apply 2.5-5kg/week for main lifts.",
    "periodization": "Cycle between hypertrophy (8-12 reps), strength (3-6 reps), power (1-3 reps) blocks every 4-6 weeks.",
    "recovery": "48-72h between heavy sessions for same muscle group. Sleep 7-9h, protein 1.6-2.2g/kg.",
    "hypertrophy": "3-4 sets of 8-12 reps at 65-80% 1RM, 60-90s rest. Train each muscle 2x/week for optimal growth.",
    "strength": "4-5 sets of 3-6 reps at 80-90% 1RM, 2-3 min rest. Focus on compound lifts.",
    "muscle_groups": {
        "chest": ["bench press", "incline press", "flyes", "dips", "push-ups"],
        "back": ["deadlifts", "pull-ups", "rows", "lat pulldowns", "face pulls"],
        "legs": ["squats", "leg press", "lunges", "romanian deadlift", "calf raises"],
        "shoulders": ["overhead press", "lateral raises", "front raises", "face pulls"],
        "arms": ["bicep curls", "tricep pushdowns", "hammer curls", "skull crushers"],
        "core": ["planks", "hanging leg raises", "cable crunches", "ab wheel"]
    }
}

def get_knowledge_text():
    text = "Exercise database:\n"
    for key, ex in EXERCISE_DB.items():
        text += f"- {ex['name']}: targets {', '.join(ex['primary'])}. Cues: {'; '.join(ex['form_cues'][:3])}.\n"
    text += "\nTraining principles:\n"
    for k, v in TRAINING_PRINCIPLES.items():
        if isinstance(v, str):
            text += f"- {k}: {v}\n"
        else:
            text += f"- {k}: {v}\n"
    return text