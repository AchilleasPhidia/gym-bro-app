# program_parser.py – now repairs truncated JSON and missing commas
import json
import re

def _repair_truncated_json(json_str: str) -> str:
    """Attempt to close unclosed braces and brackets."""
    # Count open and close braces/brackets
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    # Add missing closing characters at the end
    missing_braces = open_braces - close_braces
    missing_brackets = open_brackets - close_brackets
    # We must close brackets before braces to respect nesting
    if missing_brackets > 0:
        json_str += ']' * missing_brackets
    if missing_braces > 0:
        json_str += '}' * missing_braces
    # Remove trailing comma if present before closing
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    return json_str

def _simple_json_repair(json_str: str) -> str:
    """Remove trailing commas and stray text after final brace."""
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    last_brace = json_str.rfind('}')
    if last_brace != -1:
        json_str = json_str[:last_brace+1]
    return json_str

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

    raw_json = match.group(1)

    # Try to parse, with progressive repairs
    prog = None
    try:
        prog = json.loads(raw_json)
    except json.JSONDecodeError:
        # First repair: remove trailing commas / extra text
        repaired = _simple_json_repair(raw_json)
        try:
            prog = json.loads(repaired)
        except json.JSONDecodeError:
            # Second repair: close truncated structures
            repaired = _repair_truncated_json(repaired)
            try:
                prog = json.loads(repaired)
            except json.JSONDecodeError as e:
                return None, f"JSON decode error after full repair: {e}"

    if prog is None:
        return None, "Failed to parse JSON."

    if not isinstance(prog, dict) or "program_name" not in prog or "days" not in prog:
        return None, "JSON is missing required keys 'program_name' or 'days'."

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