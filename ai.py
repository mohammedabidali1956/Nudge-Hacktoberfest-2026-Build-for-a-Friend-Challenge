"""ai.py - Local AI extraction engine for Nudge using Ollama & Gemma.

This module handles:
1. Ollama connection checking and model discovery.
2. Prompt engineering with dynamic calendar references.
3. Structured JSON extraction with defensive parsing.
4. Deterministic date normalization using Python's datetime.
5. Task validation and safe fallbacks.
"""

import datetime
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import ollama

# Preferred model name
DEFAULT_GEMMA_MODEL = "gemma3:1b"

# Allowed priorities and categories as specified in MVP scope
ALLOWED_PRIORITIES = {"high", "medium", "low"}
ALLOWED_CATEGORIES = {"college", "work", "personal", "finance", "health", "other"}


def check_ollama_status() -> Tuple[bool, str, List[str]]:
    """Check if the local Ollama daemon is reachable and list installed models.

    Returns:
        (is_connected, message, model_names)
    """
    try:
        response = ollama.list()
        models = []
        # Response might be a ListResponse object with .models attribute
        model_list = getattr(response, "models", None)
        if model_list is None and isinstance(response, dict):
            model_list = response.get("models", [])
        
        if model_list:
            for m in model_list:
                name = getattr(m, "model", None) or getattr(m, "name", None)
                if not name and isinstance(m, dict):
                    name = m.get("model") or m.get("name")
                if name:
                    models.append(name)

        return True, "Connected to Ollama", models
    except Exception as e:
        return False, f"Nudge can't connect to Ollama. Make sure Ollama is running locally.\n\nRun in terminal: `ollama serve`", []


def detect_gemma_model(available_models: List[str]) -> Optional[str]:
    """Find gemma3:1b or another installed Gemma variant."""
    # Exact check for default model or with :latest tag
    for m in available_models:
        if m == DEFAULT_GEMMA_MODEL or m.startswith(f"{DEFAULT_GEMMA_MODEL}:"):
            return DEFAULT_GEMMA_MODEL

    # Fallback to any gemma model
    for m in available_models:
        if "gemma" in m.lower():
            return m

    return None


def get_calendar_reference(base_date: Optional[datetime.date] = None) -> Tuple[str, Dict[str, str]]:
    """Build a precise calendar reference mapping relative phrases to YYYY-MM-DD.

    This ensures 1B/small open-weight models don't have to perform arbitrary date math.
    """
    if base_date is None:
        base_date = datetime.date.today()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_name = days[base_date.weekday()]
    tomorrow = base_date + datetime.timedelta(days=1)

    mapping = {
        "today": base_date.isoformat(),
        "tonight": base_date.isoformat(),
        "tomorrow": tomorrow.isoformat(),
    }

    # Upcoming 7 days mapping
    upcoming_dates = {}
    for i in range(1, 8):
        d = base_date + datetime.timedelta(days=i)
        d_name = days[d.weekday()]
        if d_name not in upcoming_dates:
            upcoming_dates[d_name] = d.isoformat()
            mapping[d_name.lower()] = d.isoformat()

    # End of current week (Sunday)
    days_to_sun = (6 - base_date.weekday()) % 7
    if days_to_sun == 0:
        days_to_sun = 7
    end_of_week = base_date + datetime.timedelta(days=days_to_sun)
    mapping["this week"] = end_of_week.isoformat()
    mapping["sometime this week"] = end_of_week.isoformat()

    ref_text = f"Today's date is {base_date.isoformat()} ({today_name}).\n"
    ref_text += "Calendar reference for relative dates:\n"
    ref_text += f"- \"today\" or \"tonight\" = {base_date.isoformat()}\n"
    ref_text += f"- \"tomorrow\" = {tomorrow.isoformat()}\n"
    for day_name in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if day_name in upcoming_dates:
            ref_text += f"- \"{day_name}\" = {upcoming_dates[day_name]}\n"
    ref_text += f"- \"this week\" or \"sometime this week\" = {end_of_week.isoformat()}\n"

    return ref_text, mapping


def build_system_prompt(user_text: str, base_date: Optional[datetime.date] = None) -> str:
    """Build the strict extraction prompt with dynamic calendar context."""
    if base_date is None:
        base_date = datetime.date.today()

    calendar_text, _ = get_calendar_reference(base_date)

    prompt = f"""You are Nudge's task extraction engine.

Your job is to convert messy natural-language notes into actionable tasks.

{calendar_text}

Rules:
1. Extract every genuine action or commitment.
2. Split multiple actions into separate tasks.
3. Resolve relative dates to YYYY-MM-DD using the calendar reference above. If no deadline exists, return null.
4. Infer priority: "high", "medium", or "low" based on urgency and wording.
5. Do not invent tasks that are not present. If the note has no tasks or commitments (e.g. "I have nothing urgent today"), return {{"tasks": []}}.
6. Keep task titles short, clean, and actionable (e.g. "Finish DBMS assignment", "Call Rahul about project", "Pay Ahmed ₹500", "Clean laptop"). Do not duplicate the date in the title.
7. Assign exactly one category:
   - "college": homework, assignments, DBMS, university, exams, courses
   - "work": office, clients, workplace tasks, jobs
   - "personal": friends, family, calling mom/Rahul, cleaning, errands
   - "finance": payments, money, ₹, $, bills, rent
   - "health": gym, doctor, medication, workout
   - "other": miscellaneous
8. For each task, provide "evidence":
   - "action_phrase": concise words from note indicating the action (e.g. "need to finish", "call", "pay")
   - "date_phrase": concise words indicating the deadline (e.g. "tomorrow", "tonight", "Friday"), or null
   - "category_reason": brief reason for the chosen category
9. Return ONLY valid JSON matching the schema below.

Output schema:
{{
  "tasks": [
    {{
      "title": "Finish DBMS assignment",
      "due_date": "YYYY-MM-DD",
      "priority": "high",
      "category": "college",
      "evidence": {{
        "action_phrase": "need to finish",
        "date_phrase": "tomorrow",
        "category_reason": "Academic coursework assignment"
      }}
    }}
  ]
}}

User note:
{user_text}
"""
    return prompt


def safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """Defensively extract and parse JSON from model output.

    Handles:
    - Code fences (```json ... ```)
    - Surrounding conversational text or preamble
    - Trailing commas or formatting quirks
    """
    text = text.strip()
    if not text:
        return None

    # Step 1: Strip markdown code blocks
    if "```" in text:
        # Match ```json ... ``` or just ``` ... ```
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()

    # Step 2: Try direct json.loads
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        if isinstance(data, list):
            return {"tasks": data}
    except Exception:
        pass

    # Step 3: Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None


def format_human_date(due_date_str: Optional[str], base_date: Optional[datetime.date] = None, date_phrase: Optional[str] = None) -> str:
    """Format an ISO date string (YYYY-MM-DD) into a human-friendly string.

    Examples:
    - Today
    - Tonight (if date_phrase indicated tonight)
    - Tomorrow
    - Friday, Oct 9
    - Nov 12, 2026
    """
    if not due_date_str:
        return "No deadline"

    if base_date is None:
        base_date = datetime.date.today()

    try:
        task_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except Exception:
        return due_date_str

    diff = (task_date - base_date).days

    if diff == 0:
        if date_phrase and "tonight" in date_phrase.lower():
            return "Tonight"
        return "Today"
    elif diff == 1:
        return "Tomorrow"
    elif 1 < diff <= 6:
        # e.g., "Friday, Oct 9"
        return task_date.strftime("%A, %b %d").replace(" 0", " ")
    elif diff == 7:
        return f"Next {task_date.strftime('%A')}"
    else:
        # e.g., "Oct 25, 2026"
        return task_date.strftime("%b %d, %Y").replace(" 0", " ")


def normalize_and_validate_tasks(
    raw_tasks: List[Dict[str, Any]],
    user_text: str,
    base_date: Optional[datetime.date] = None,
) -> List[Dict[str, Any]]:
    """Clean, validate, and enrich extracted tasks with Python datetime logic.

    Ensures every task has valid title, priority, category, validated due_date,
    human_date, and clear extraction evidence for the "Why Nudge?" section.
    """
    if base_date is None:
        base_date = datetime.date.today()

    _, date_map = get_calendar_reference(base_date)
    cleaned_tasks = []

    for item in raw_tasks:
        if not isinstance(item, dict):
            continue

        raw_title = item.get("title")
        if not raw_title or not str(raw_title).strip():
            continue

        title = str(raw_title).strip()

        # Clean priority
        raw_priority = str(item.get("priority", "")).lower().strip()
        if "high" in raw_priority:
            priority = "high"
        elif "low" in raw_priority:
            priority = "low"
        else:
            priority = "medium"

        # Clean category
        raw_cat = str(item.get("category", "")).lower().strip()
        matched_cat = None
        for cat in ALLOWED_CATEGORIES:
            if cat in raw_cat:
                matched_cat = cat
                break
        category = matched_cat or "other"

        # Evidence extraction
        evidence = item.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}

        action_phrase = evidence.get("action_phrase") or ""
        date_phrase = evidence.get("date_phrase") or ""
        category_reason = evidence.get("category_reason") or ""

        # Validate & resolve due date
        raw_due = item.get("due_date")
        resolved_date: Optional[str] = None

        # Check if model provided a valid YYYY-MM-DD
        if raw_due and isinstance(raw_due, str):
            clean_due = raw_due.strip()
            # If it's a literal placeholder like "YYYY-MM-DD", ignore it
            if "YYYY" not in clean_due and "null" not in clean_due.lower():
                try:
                    parsed_d = datetime.datetime.strptime(clean_due, "%Y-%m-%d").date()
                    resolved_date = parsed_d.isoformat()
                except Exception:
                    pass

        # Python deterministic date fallback using date_phrase or user_text
        detected_phrase = str(date_phrase or "").lower()
        if not resolved_date:
            for phrase, iso_val in date_map.items():
                if phrase in detected_phrase or phrase in title.lower() or phrase in user_text.lower():
                    resolved_date = iso_val
                    if not date_phrase:
                        date_phrase = phrase
                    break

        # If date_phrase explicitly mentions "tonight" or "today", ensure today's date
        if "tonight" in detected_phrase or "today" in detected_phrase:
            resolved_date = base_date.isoformat()
        elif "tomorrow" in detected_phrase:
            resolved_date = (base_date + datetime.timedelta(days=1)).isoformat()

        # Human-friendly readable date
        human_date = format_human_date(resolved_date, base_date, date_phrase)

        # Build clean evidence points for the "Why Nudge?" section
        reasons = []
        if date_phrase:
            reasons.append(f'"{date_phrase}" → detected as deadline ({human_date})')
        elif resolved_date:
            reasons.append(f'Deadline resolved as {human_date}')

        if action_phrase:
            reasons.append(f'"{action_phrase}" → interpreted as the action')
        else:
            # Fallback action hint from title
            first_word = title.split()[0] if title.split() else ""
            if first_word:
                reasons.append(f'"{first_word}" → identified as action verb')

        if category_reason:
            reasons.append(f'"{category.capitalize()}" → {category_reason}')
        else:
            reasons.append(f'Categorized as {category}')

        cleaned_tasks.append({
            "title": title,
            "due_date": resolved_date,
            "human_date": human_date,
            "priority": priority,
            "category": category,
            "evidence": {
                "action_phrase": action_phrase,
                "date_phrase": date_phrase,
                "category_reason": category_reason,
                "explanation_bullets": reasons,
            },
        })

    return cleaned_tasks


def extract_tasks(
    user_text: str,
    model_name: Optional[str] = None,
    base_date: Optional[datetime.date] = None,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Execute local task extraction via Ollama + Gemma.

    Returns:
        (success: bool, status_message: str, tasks: list)
    """
    clean_text = user_text.strip()
    if not clean_text:
        return False, "Write something first.", []

    # Verify Ollama connection
    connected, conn_msg, installed_models = check_ollama_status()
    if not connected:
        return False, conn_msg, []

    # Choose model
    if not model_name:
        model_name = detect_gemma_model(installed_models)

    if not model_name:
        return (
            False,
            f"The configured Gemma model ('{DEFAULT_GEMMA_MODEL}') isn't available locally.\n\n"
            f"Run in terminal to install:\n`ollama pull {DEFAULT_GEMMA_MODEL}`",
            [],
        )

    # Build prompt
    prompt = build_system_prompt(clean_text, base_date=base_date)

    try:
        response = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
            format="json",
        )

        content = ""
        if hasattr(response, "message") and hasattr(response.message, "content"):
            content = response.message.content
        elif isinstance(response, dict):
            content = response.get("message", {}).get("content", "")

        parsed_json = safe_json_extract(content)
        if not parsed_json:
            return (
                False,
                "Nudge received an unparseable response from the local model. Please try rewording your note.",
                [],
            )

        raw_tasks = parsed_json.get("tasks", [])
        if not isinstance(raw_tasks, list):
            return (
                False,
                "Nudge could not identify a valid task list in the model's output.",
                [],
            )

        validated_tasks = normalize_and_validate_tasks(raw_tasks, clean_text, base_date=base_date)

        if not validated_tasks:
            return True, "I couldn't find a clear action in that note.", []

        return True, "Success", validated_tasks

    except Exception as e:
        # Defensive catch: Never crash the application, return a clean user-facing error
        err_str = str(e)
        if "connect" in err_str.lower() or "connection" in err_str.lower():
            return (
                False,
                "Nudge can't connect to Ollama. Make sure Ollama is running locally.\n\nRun in terminal: `ollama serve`",
                [],
            )
        return (
            False,
            f"An unexpected error occurred during local extraction: {err_str}",
            [],
        )
