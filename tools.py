# tools.py – robust exercise parsing, web search, and form analysis
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
                        {"type": "text", "text": "Analyze this gym exercise form. Point out any mistakes, risk of injury, and how to correct them. Be encouraging but direct."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Form analysis failed: {e}"

def parse_program_payload(text: str):
    if not text:
        return None, "Empty response."
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if not match:
        match = re.search(r'(\{[^{}]*"program_name"[^{}]*\})', text, re.DOTALL)
        if not match:
            first = text.find('{')
            last = text.rfind('}')
            if first != -1 and last > first:
                candidate = text[first:last+1]
                if '"program_name"' in candidate and '"days"' in candidate:
                    match = re.search(r'(\{.*\})', candidate, re.DOTALL)
    if not match:
        return None, "No JSON object with 'program_name' and 'days' found."
    raw_json = match.group(1)
    raw_json = re.sub(r',\s*([}\]])', r'\1', raw_json)
    last_brace = raw_json.rfind('}')
    if last_brace != -1:
        raw_json = raw_json[:last_brace+1]
    try:
        prog = json.loads(raw_json)
    except json.JSONDecodeError:
        open_b = raw_json.count('{') - raw_json.count('}')
        open_s = raw_json.count('[') - raw_json.count(']')
        raw_json += ']' * open_s + '}' * open_b
        try:
            prog = json.loads(raw_json)
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e}"
    if not isinstance(prog, dict) or "program_name" not in prog or "days" not in prog:
        return None, "Missing required keys."
    return prog, None

def normalize_exercises(program: dict):
    exercises = []
    for day in program.get("days", []):
        for ex in day.get("exercises", []):
            name = ex.get("name", "Unnamed Exercise")
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
                except (ValueError, TypeError):
                    num_sets = 3
                reps_field = ex.get("reps", "10")
                if isinstance(reps_field, str) and "-" in reps_field:
                    reps = int(reps_field.split("-")[0])
                else:
                    try:
                        reps = int(reps_field)
                    except (ValueError, TypeError):
                        reps = 10
                notes = ex.get("notes", "")
                for _ in range(num_sets):
                    sets_data.append({"weight": 0, "reps": reps, "notes": notes})
            if sets_data:
                exercises.append({"name": name, "sets": sets_data})
    return exercises