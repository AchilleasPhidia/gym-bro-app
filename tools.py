# tools.py – Gym Bro X Final (Bulletproof JSON parser)

import json, re, io, base64
from duckduckgo_search import DDGS
from PIL import Image

def search_exercises(query: str, max_results: int = 3) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        summary = "Here's what I found:\n"
        for i, r in enumerate(results, 1):
            summary += f"{i}. {r['title']}\n   {r['body'][:200]}...\n   Link: {r['href']}\n"
        return summary
    except Exception as e:
        return f"Search failed: {e}"

def analyze_form(image_file, client) -> str:
    try:
        image = Image.open(image_file)
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this gym exercise form."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Form analysis failed: {e}"

def repair_json(j_str: str) -> str:
    """Aggressively fix common JSON errors from AI."""
    # Remove anything after the last closing brace
    last_brace = j_str.rfind('}')
    if last_brace != -1:
        j_str = j_str[:last_brace+1]
    # Remove trailing commas before closing brackets/braces
    j_str = re.sub(r',\s*([}\]])', r'\1', j_str)
    # Insert missing commas between consecutive strings or values
    j_str = re.sub(r'"\s*\n?\s*"', '", "', j_str)
    j_str = re.sub(r'([}\]\d])\s*\n?\s*"', r'\1, "', j_str)
    j_str = re.sub(r'(\d)\s+(\d)', r'\1, \2', j_str)
    # Fix unterminated strings – if odd number of unescaped quotes, append one
    cleaned = re.sub(r'\\"', '', j_str)
    if cleaned.count('"') % 2 != 0:
        j_str += '"'
    # Escape unescaped newlines inside strings
    j_str = re.sub(r'(?<!\\)\n', r'\\n', j_str)
    # Balance braces and brackets
    open_braces = j_str.count('{') - j_str.count('}')
    open_brackets = j_str.count('[') - j_str.count(']')
    j_str += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
    return j_str

def parse_program_payload(text: str):
    """
    Extract a valid program JSON from any text.
    Returns (program_dict, error_msg). One will be None.
    """
    if not text:
        return None, "Empty response."

    # Attempt 1: Standard JSON code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not match:
        # Attempt 2: Look for a JSON object containing "program_name"
        match = re.search(r'(\{[^{}]*"program_name"[^{}]*\})', text, re.DOTALL)
        if not match:
            # Attempt 3: Find first { and last } and hope it's complete
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last > first:
                candidate = text[first:last+1]
                if '"program_name"' in candidate and '"days"' in candidate:
                    match = re.search(r'(\{.*\})', candidate, re.DOTALL)
    if not match:
        # Attempt 4: Sometimes the AI puts the JSON directly as the function argument without quotes
        # Look for something that looks like a JSON object with program_name anywhere
        match = re.search(r'(\{[^{}]*"program_name".*?"days".*?\})', text, re.DOTALL)

    if not match:
        return None, "No JSON object with 'program_name' and 'days' found."

    raw_json = match.group(1)

    # Try as-is
    try:
        prog = json.loads(raw_json)
        if "program_name" in prog and "days" in prog:
            return prog, None
    except json.JSONDecodeError:
        pass

    # Try repaired
    repaired = repair_json(raw_json)
    try:
        prog = json.loads(repaired)
        if "program_name" in prog and "days" in prog:
            return prog, None
    except json.JSONDecodeError:
        pass

    # Last resort: maybe it's double‑encoded (a string containing JSON)
    try:
        inner = json.loads(raw_json)
        if isinstance(inner, str):
            return parse_program_payload(inner)
    except:
        pass

    return None, f"Could not parse program JSON. Raw snippet: {raw_json[:200]}..."

def normalize_exercises(program: dict):
    exercises = []
    for day in program.get("days", []):
        for ex in day.get("exercises", []):
            name = ex.get("name", "exercise")
            sets_data = []
            sets_field = ex.get("sets", 3)
            if isinstance(sets_field, list):
                for s in sets_field:
                    if isinstance(s, dict):
                        sets_data.append({
                            "weight": s.get("weight", 0),
                            "reps": s.get("reps", 10),
                            "notes": s.get("notes", "")
                        })
            elif isinstance(sets_field, dict):
                sets_data.append({
                    "weight": sets_field.get("weight", 0),
                    "reps": sets_field.get("reps", 10),
                    "notes": sets_field.get("notes", "")
                })
            else:
                try:
                    num_sets = int(sets_field)
                except:
                    num_sets = 3
                reps_field = ex.get("reps", "10")
                if isinstance(reps_field, str) and "-" in reps_field:
                    reps = int(reps_field.split("-")[0])
                else:
                    try:
                        reps = int(reps_field)
                    except:
                        reps = 10
                notes = ex.get("notes", "")
                for _ in range(num_sets):
                    sets_data.append({"weight": 0, "reps": reps, "notes": notes})
            if sets_data:
                exercises.append({"name": name, "sets": sets_data})
    return exercises