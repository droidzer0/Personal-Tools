import os
import json
import ssl
import time
import urllib.request
import urllib.error
from datetime import date
from typing import Dict, List, Optional

def get_ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        pass
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    except Exception:
        return ssl._create_unverified_context()

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.ssl_ctx = get_ssl_context()

    def generate_daily_note(
        self,
        today: date,
        previous_note_data: Dict[str, any],
        workout_data: Dict[str, any],
        api_data: Dict[str, any],
        system_incidents: Optional[List[str]] = None
    ) -> str:
        """
        Calls Gemini to format and synthesize the daily note.
        Falls back smoothly to high-fidelity deterministic generation if API is unreachable.
        """
        today_str = today.strftime("%Y-%m-%d")
        weekday_name = today.strftime("%A")

        if self.api_key:
            # 1. Try direct REST API first (zero external pip packages required)
            try:
                text = self._call_gemini_rest_api(today_str, weekday_name, previous_note_data, workout_data, api_data, system_incidents)
                if text:
                    return text
            except Exception as e:
                print(f"[GeminiClient] Direct REST API error ({e}); trying SDK or fallback.")

            # 2. Try SDK if installed
            try:
                text = self._call_gemini_sdk(today_str, weekday_name, previous_note_data, workout_data, api_data, system_incidents)
                if text:
                    return text
            except Exception as e:
                print(f"[GeminiClient] SDK invocation error ({e}); using deterministic generation.")

        return self._deterministic_generation(today_str, weekday_name, previous_note_data, workout_data, api_data, system_incidents)

    def _build_prompt(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None
    ) -> str:
        workout_lines = []
        for ex in workout.get('exercises', []):
            url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
            workout_lines.append(f"- [ ] **{url_part}** — {ex['target']} (Cue: {ex['cue']})")

        cal_data = apis.get('calendar', {})
        cal_lines = cal_data.get('calendar_lines', [])
        cal_summary_str = '\n'.join(cal_lines) if cal_lines else "No scheduled calendar events today."
        markets_str = ', '.join(q.get('display', '') for q in apis.get('markets', []))

        return f"""
You are an executive assistant and athletic performance coach formatting a daily Obsidian note for {today_str} ({weekday_name}).
User context: 27-year-old male tech worker living in Chicago, working at a desk, restarting fitness from square 1 (Current: 191 lbs, Goal: 165-170 lbs).

Input Data:
---
1. Unfinished Tasks from Previous Note:
{chr(10).join(f"- [ ] {t}" for t in prev.get('incomplete_tasks', [])) if prev.get('incomplete_tasks') else "- [ ] Review project priorities and define top daily goals"}

2. Yesterday's Scratchpad & Tomorrow's Ideas (Convert each of these notes/thoughts into actionable tasks):
{chr(10).join(f"- {s}" for s in prev.get('scratchpad_notes', [])) if prev.get('scratchpad_notes') else "No scratchpad notes."}

3. Today's Google Calendar Events & Schedule:
{cal_summary_str}

4. Today's Scheduled Workout ({workout.get('title')}):
Goal: {workout.get('goal')}
Exercises:
{chr(10).join(workout_lines)}
Desk Posture Cue: {workout.get('desk_mobility')}

5. Life Dashboard & System Status:
- Website (DroidZero): {apis.get('website', {}).get('message', 'Online')}
- Server Instance Load: {apis.get('instance', {}).get('load_avg', 'Normal')} | Disk Free: {apis.get('instance', {}).get('disk_free_gb', 'N/A')}
- Chicago Weather: {apis.get('weather', {}).get('summary', 'Seasonal')}
- Gmail Triage: {apis.get('gmail', {}).get('status', 'Ready')}
- Google Calendar: {cal_data.get('status', 'Ready')}
- Market Overview: {markets_str}

6. System Health Alerts / Incidents Requiring Action:
{chr(10).join(f"- 🚨 {inc}" for inc in (system_incidents or [])) if system_incidents else "All systems fully operational."}
---

Formatting Guidelines:
1. Output valid Markdown only. Start with Obsidian YAML frontmatter (date, tags: [daily-note], type: daily-note).
2. Create clear, motivating sections:
   - Header with Chicago weather and quick system pulse.
   - ## 🎯 To-do
     Must contain two clearly organized subsections:
     ### 📅 Today's Schedule
     - List each Google Calendar event for today with interactive checkboxes: `- [ ] ⏰ 09:00 AM – 10:00 AM: Meeting Title ([Join Meet](url)) *(Account A)*` or `- [ ] 🗓️ All Day: Event Name`.
     - If there are no scheduled events, output: `*No scheduled calendar events today.*`
     ### 📋 Priorities & Tasks
     - CRITICAL - SYSTEM OUTAGES & WARNINGS: If any system is down, degraded, or requires reauthorization (listed in "System Health Alerts / Incidents"), you MUST create an urgent checklist task `- [ ] ⚠️` at the TOP of Priorities & Tasks to investigate and fix it (e.g. `- [ ] ⚠️ Reauthorize Google Calendar API: Run python3 reauth_google.py in terminal`; `- [ ] 🚨 Investigate DroidZero downtime`).
     - Convert EVERY thought, errand, reminder, or idea from "Yesterday's Scratchpad & Tomorrow's Ideas" into an actionable checklist task `- [ ]` (e.g., "Put on the agenda tomorrow to schedule my swim session" -> `- [ ] Schedule morning swim session`; "I also need to order groceries" -> `- [ ] Order groceries`).
     - Also carry over any unfinished `- [ ]` tasks from the previous note.
     - Ensure no task, idea, or system alert is lost or omitted. List all converted tasks as clear `- [ ]` items.
   - ## 🏋️ Workout: {workout.get('title')} (include the exact workout checklist, clickable diagram links, biometrics context, and desk worker posture cues).
   - ## 📊 Life Dashboard Pulse (compact table or bullets covering DroidZero, VM health, Gmail triage, Calendar sync status, and Market Watchlist).
   - ## 📝 Scratchpad & Tomorrow's Ideas (empty space for the user to jot notes during the day).
3. Ensure all workout items have interactive checkboxes: `- [ ] [**Exercise Name**](URL) ↗ — target` and an indented line `  - Actual: `___ lbs x ___ reps`` for mobile logging.
4. Keep the output clean, sharp, and directly usable in Obsidian. Do not wrap in ```markdown code fences.
"""

    def _call_gemini_rest_api(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None
    ) -> Optional[str]:
        """Calls Google Gemini REST API directly without requiring any pip dependencies."""
        prompt = self._build_prompt(today_str, weekday_name, prev, workout, apis, system_incidents)

        # Normalize model name for v1beta endpoint
        model = self.model_name.replace("models/", "")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 8192
            }
        }

        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )

                with urllib.request.urlopen(req, timeout=45, context=self.ssl_ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if not p.get("thought", False) and "text" in p]
                        full_text = "".join(text_parts).strip()
                        if full_text:
                            if full_text.startswith("```markdown"):
                                full_text = full_text[11:].strip()
                            elif full_text.startswith("```"):
                                full_text = full_text[3:].strip()
                            if full_text.endswith("```"):
                                full_text = full_text[:-3].strip()
                            return full_text
                return None
            except urllib.error.HTTPError as he:
                if he.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
            except Exception:
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise

        return None

    def _call_gemini_sdk(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None
    ) -> Optional[str]:
        """Calls Gemini using google-genai or google-generativeai SDK if available."""
        prompt = self._build_prompt(today_str, weekday_name, prev, workout, apis, system_incidents)

        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip()
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text.strip()

    def _deterministic_generation(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None
    ) -> str:
        """Deterministic high-quality fallback generator."""
        incomplete = prev.get("incomplete_tasks", [])
        scratch = prev.get("scratchpad_notes", [])

        tasks_md = []
        if system_incidents:
            for inc in system_incidents:
                tasks_md.append(f"- [ ] ⚠️ {inc}")

        if incomplete:
            for task in incomplete:
                tasks_md.append(f"- [ ] {task}")
        else:
            tasks_md.append("- [ ] Review project priorities for today")
            tasks_md.append("- [ ] 30-minute deep focus coding session")

        if scratch:
            for note in scratch:
                clean_note = note.lstrip("-* \t").strip()
                if clean_note:
                    tasks_md.append(f"- [ ] {clean_note}")

        cal_data = apis.get("calendar", {})
        cal_lines = cal_data.get("calendar_lines", [])

        todo_blocks = ["### 📅 Today's Schedule"]
        if cal_lines:
            todo_blocks.extend(cal_lines)
        else:
            todo_blocks.append("*No scheduled calendar events today.*")

        todo_blocks.append("\n### 📋 Priorities & Tasks")
        todo_blocks.extend(tasks_md)

        workout_exercises = []
        for ex in workout.get("exercises", []):
            url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
            workout_exercises.append(f"- [ ] **{url_part}** — {ex['target']}")
            workout_exercises.append(f"  - Form Cue: *{ex['cue']}*")
            workout_exercises.append(f"  - Actual: `___ lbs x ___ reps`")

        market_lines = " • ".join(q.get("display", "") for q in apis.get("markets", []))

        return f"""---
date: {today_str}
day: {weekday_name}
tags:
  - daily-note
type: daily-note
---

# 📅 Daily Plan: {weekday_name}, {today_str}

> 🌤️ **Chicago Weather:** {apis.get('weather', {}).get('summary', 'Chicago, IL')}
> 🌐 **DroidZero:** {apis.get('website', {}).get('message', 'Online')} • **VM Load:** `{apis.get('instance', {}).get('load_avg', 'N/A')}`

---

## 🎯 To-do

{chr(10).join(todo_blocks)}

---

## 🏋️ Workout: {workout.get('title')}
> **Category:** {workout.get('category')} • **Target Goal:** {workout.get('goal')}
> **Biometrics:** Current BMI: `{workout.get('current_bmi', 27.4)}` • Goal: `165–170 lbs` (`-{workout.get('weight_to_lose', 23.5)} lbs` to target)

{chr(10).join(workout_exercises)}

> [!TIP]
> **Desk Worker Posture Cue:** {workout.get('desk_mobility')}

---

## 📊 Life Dashboard Pulse

| Service | Status & Metrics | Quick Action |
| :--- | :--- | :--- |
| **🌐 DroidZero Site** | {apis.get('website', {}).get('message', 'Online')} | [[00-DroidZero-Master-Hub|Master Hub]] |
| **🖥️ OCI Instance** | Load: `{apis.get('instance', {}).get('load_avg', 'N/A')}` • Disk Free: `{apis.get('instance', {}).get('disk_free_gb', 'N/A')}` | [[03-Infrastructure-and-Backend-API|API Blueprint]] |
| **📧 Gmail Inboxes** | {apis.get('gmail', {}).get('status', 'Ready')} | [[Subscriptions Report|Subscriptions]] |
| **📅 Google Calendar** | {cal_data.get('status', 'Ready')} | [[Dashboard|Command Center]] |
| **💪 Health Ledger** | Weight: `191 lbs` • Weekly weigh-in on Sunday | [[Health & Fitness|Health Dashboard]] |

**📈 Markets & Tickers:**
{market_lines if market_lines else "VOO • VTI • VT • QQQ • IGV • NOW • BTC • ETH"}

---

## 📝 Scratchpad & Tomorrow's Ideas
- 

---
[[Dashboard|⬅️ Back to Life Dashboard]]
"""
