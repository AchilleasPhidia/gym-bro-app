# program_parser.py
import json
import re

def parse_program_payload(text: str):
    """Try to extract a valid program JSON from a string.
    Returns (program_dict, error_msg).  One will be None.
    """
    if not text:
        return None, "Empty response."

    # 1. Look for JSON code block (with or without language)
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not match:
        # 2. Look for a plain JSON object that contains "program_name"
        match = re.search(r'(\{[^{}]*"program_name"[^{}]*\})', text, re.DOTALL)
        if not match:
            # 3. Grab the first { to last } and check for required keys
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last > first:
                candidate = text[first:last+1]
                if '"program_name"' in candidate and '"days"' in candidate:
                    match = re.search(r'(\{.*\})', candidate, re.DOTALL)

    if not match:
        return None, "No JSON object with 'program_name' and 'days' found."

    try:
        prog = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        return None, f"JSON decode error: {e}"

    if not isinstance(prog, dict) or "program_name" not in prog or "days" not in prog:
        return None, "JSON is missing required keys 'program_name' or 'days'."

    # Validate that days is a list of objects with at least day and exercises
    days = prog.get("days")
    if not isinstance(days, list) or len(days) == 0:
        return None, "'days' must be a non-empty list."
    for d in days:
        if not isinstance(d, dict):
            return None, "Each day must be an object."
        if "day" not in d or "exercises" not in d:
            return None, "Each day must have 'day' and 'exercises'."
        if not isinstance(d["exercises"], list):
            return None, "'exercises' must be a list."

    return prog, None


def normalize_exercises(program: dict):
    """Convert a program dict into the flat exercise list used by the workout tab."""
    exercises = []
    for day in program.get("days", []):
        day_name = day.get("day", "Unknown")
        for ex in day.get("exercises", []):
            name = ex.get("name", "exercise")
            sets_data = []
            # If sets is a list of objects (detailed sets)
            if isinstance(ex.get("sets"), list):
                for s in ex["sets"]:
                    sets_data.append({
                        "weight": s.get("weight", 0),
                        "reps": s.get("reps", 10),
                        "notes": s.get("notes", "")
                    })
            else:
                # Simple sets/reps numbers
                num_sets = ex.get("sets", 3)
                reps = ex.get("reps", "10")
                if isinstance(reps, str) and "-" in reps:
                    reps = int(reps.split("-")[0])
                else:
                    reps = int(reps) if isinstance(reps, (int, str)) and str(reps).isdigit() else 10
                for _ in range(int(num_sets)):
                    sets_data.append({"weight": 0, "reps": reps, "notes": ex.get("notes", "")})
            exercises.append({"name": name, "sets": sets_data})
    return exercises