# tools.py – Ultra‑robust JSON parser, web search, form analysis

import json, re, io, base64
from duckduckgo_search import DDGS
from PIL import Image

# ---------- Web Search ----------
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

# ---------- Form Analysis ----------
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

# ---------- JSON Repair & Parsing ----------
def repair_json(j_str: str) -> str:
    """Aggressively fix common JSON errors, especially from AI."""
    # Remove trailing commas before closing brackets/braces
    j_str = re.sub(r',\s*([}\]])', r'\1', j_str)
    # Remove anything after the last closing brace
    last_brace = j_str.rfind('}')
    if last_brace != -1:
        j_str = j_str[:last_brace+1]
    # Balance braces and brackets
    open_braces   = j_str.count('{') - j_str.count('}')
    open_brackets = j_str.count('[') - j_str.count(']')
    j_str += ']' * max(0, open_brackets) + '}' * max(0, open_braces)
    # Fix unterminated strings – add a closing quote if we have an odd number
    cleaned = re.sub(r'\\"', '', j_str)          # remove escaped quotes for counting
    if cleaned.count('"') % 2 != 0:
        j_str += '"'
    # Escape unescaped newlines inside strings (common AI mistake)
    # We do a safe replacement: replace literal newline with \n only when inside quotes.
    # Simple approach: replace all newlines not preceded by backslash with \\n
    j_str = re.sub(r'(?<!\\)\n', r'\\n', j_str)
    # Remove stray backslashes before quotes (the AI sometimes puts \")
    j_str = j_str.replace('\\"', '"')            # then we fix again later? No, keep as is.
    # Fix missing commas between objects in arrays/objects
    # Insert comma before a new key (i.e., before a quote that follows a closing brace/bracket)
    j_str = re.sub(r'(["}\]\d])\s*\n?\s*"', r'\1, "', j_str)
    # Also, insert comma before a new element in an array (after a number/boolean)
    j_str = re.sub(r'(\d)\s+(\d)', r'\1, \2', j_str)   # two numbers separated by space -> comma
    # Remove comments (//)
    j_str = re.sub(r'//.*', '', j_str)
    return j_str

def parse_program_payload(text: str):
    """Extract a valid program JSON from any text. Returns (program_dict, error_msg)."""
    if not text:
        return None, "Empty response."

    # Try multiple strategies to find a JSON object containing "program_name"
    match = None
    # 1) Code block
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not match:
        # 2) Plain object with program_name
        match = re.search(r'(\{[^{}]*"program_name"[^{}]*\})', text, re.DOTALL)
        if not match:
            # 3) First { to last }
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last > first:
                candidate = text[first:last+1]
                if '"program_name"' in candidate and '"days"' in candidate:
                    match = re.search(r'(\{.*\})', candidate, re.DOTALL)

    if not match:
        return None, "No JSON object with 'program_name' and 'days' found."

    raw = match.group(1)

    # Attempt 1: parse as-is
    for attempt in range(3):
        try:
            prog = json.loads(raw)
            if "program_name" in prog and "days" in prog:
                return prog, None
        except json.JSONDecodeError:
            if attempt == 0:
                raw = repair_json(raw)
            elif attempt == 1:
                # Try to extract just the JSON part from inside a code block again (if any)
                inner_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
                if inner_match:
                    raw = inner_match.group(1)
                raw = repair_json(raw)

    return None, f"Could not parse program JSON. Raw snippet: {raw[:200]}..."

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