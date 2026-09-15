import os
import json
import ssl
import time
import urllib.request
import urllib.error
from datetime import date
from typing import Dict, List, Optional, Any

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
        system_incidents: Optional[List[str]] = None,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        mandatory_tasks: Optional[List[str]] = None
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
                text = self._call_gemini_rest_api(
                    today_str, weekday_name, previous_note_data, workout_data, api_data,
                    system_incidents, timeline, working_weights, mandatory_tasks
                )
                if text:
                    return text
            except Exception as e:
                print(f"[GeminiClient] Direct REST API error ({e}); trying SDK or fallback.")

            # 2. Try SDK if installed
            try:
                text = self._call_gemini_sdk(
                    today_str, weekday_name, previous_note_data, workout_data, api_data,
                    system_incidents, timeline, working_weights, mandatory_tasks
                )
                if text:
                    return text
            except Exception as e:
                print(f"[GeminiClient] SDK invocation error ({e}); using deterministic generation.")

        return self._deterministic_generation(
            today_str, weekday_name, previous_note_data, workout_data, api_data,
            system_incidents, timeline, working_weights, mandatory_tasks
        )

    def _build_prompt(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        mandatory_tasks: Optional[List[str]] = None
    ) -> str:
        cal_data = apis.get('calendar', {})
        cal_lines = cal_data.get('calendar_lines', [])
        cal_summary_str = '\n'.join(cal_lines) if cal_lines else "No scheduled calendar events today."
        markets_str = ', '.join(q.get('display', '') for q in apis.get('markets', []))

        # Program timeline
        week = timeline.get("week", 1) if timeline else 1
        day = timeline.get("day", 1) if timeline else 1
        cycle_str = f"Week {week}, Day {day}"

        # Quote of the day
        quote_data = apis.get('quote', {})
        quote_text = quote_data.get('quote', 'We are what we repeatedly do. Excellence, then, is not an act, but a habit.')
        quote_author = quote_data.get('author', 'Will Durant')
        quote_theme = quote_data.get('theme', 'Habit & Consistency')

        # Real news headlines
        news = apis.get('news', {})
        chicago_n = news.get('chicago', {})
        us_n = news.get('us', {})
        world_n = news.get('world', {})
        news_lines = [
            f"- 🏙️ **Chicago**: [{chicago_n.get('title', 'Local news')}]({chicago_n.get('link', '#')}) *({chicago_n.get('source', 'WGN-TV')})*",
            f"- 🇺🇸 **US**: [{us_n.get('title', 'National news')}]({us_n.get('link', '#')}) *({us_n.get('source', 'NPR')})*",
            f"- 🌍 **World**: [{world_n.get('title', 'World news')}]({world_n.get('link', '#')}) *({world_n.get('source', 'BBC News')})*"
        ]
        news_summary_str = "\n".join(news_lines)

        # Gmail unread candidates and triage
        gmail_data = apis.get('gmail', {})
        candidates = gmail_data.get('candidates', [])
        email_candidates_lines = []
        for idx, cand in enumerate(candidates[:5], 1):
            email_candidates_lines.append(
                f"- Candidate {idx} [{cand.get('account', 'Gmail')}]: From: {cand.get('sender')} | Subject: \"{cand.get('subject')}\" | Snippet: \"{cand.get('snippet')}\" | Important: {cand.get('is_important')}"
            )
        email_candidates_str = "\n".join(email_candidates_lines) if email_candidates_lines else "No unread emails in inboxes."

        # Working weights benchmarks
        ww_lines = []
        if working_weights:
            for ex_name, ex_data in working_weights.items():
                ww_lines.append(f"- {ex_name}: Working: {ex_data.get('working', '--')} | PB: {ex_data.get('pb', '--')}")
        ww_summary_str = "\n".join(ww_lines) if ww_lines else "No recorded lifts yet."

        is_workout_skipped = workout.get("skipped", False)
        if is_workout_skipped:
            workout_section_input = "4. Workout Status: USER IS SKIPPING WORKOUT TODAY (explicitly requested in yesterday's scratchpad). DO NOT GENERATE ANY WORKOUT SECTION."
            workout_format_instruction = "- WORKOUT SECTION: Do NOT output any '## 🏋️ Workout' section today. The user explicitly chose to skip the workout. Completely omit the workout section."
        else:
            workout_lines = []
            for ex in workout.get('exercises', []):
                url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
                workout_lines.append(f"- [ ] **{url_part}** — {ex['target']} (Cue: {ex['cue']})")
            workout_section_input = f"""4. Today's Scheduled Workout ({cycle_str}: {workout.get('title')}):
Program Timeline: {cycle_str} (CRITICAL: Do NOT say 'Week 1, Day 1' unless week is 1 and day is 1. You MUST use {cycle_str} in any Coach's Note or headers).
Goal: {workout.get('goal')}
Exercises:
{chr(10).join(workout_lines)}
Desk Posture Cue: {workout.get('desk_mobility')}
Recent Health Ledger Working Weights / PBs:
{ww_summary_str}"""
            workout_format_instruction = f"- ## 🏋️ Workout ({cycle_str}): {workout.get('title')} (include the exact workout checklist, clickable diagram links, biometrics context, desk worker posture cues, and Coach's Note referencing {cycle_str})."

        mandatory_checklist = mandatory_tasks or ["Brush Teeth & Floss", "Wash Face"]
        mandatory_tasks_str = "\n".join(f"- [ ] {t}" for t in mandatory_checklist)

        return f"""
You are an executive assistant and athletic performance coach formatting a daily Obsidian note for {today_str} ({weekday_name}).
User context: 27-year-old male tech worker living in Chicago, working at a desk, training on Square 1 On-Ramp protocol (Current: 191 lbs, Goal: 165-170 lbs). Today is {cycle_str} of the fitness program.

Input Data:
---
1. Unfinished Tasks from Previous Note:
{chr(10).join(f"- [ ] {t}" for t in prev.get('incomplete_tasks', [])) if prev.get('incomplete_tasks') else "- [ ] Review project priorities and define top daily goals"}

2. Yesterday's Scratchpad & Tomorrow's Ideas (Convert each of these notes/thoughts into actionable tasks):
{chr(10).join(f"- {s}" for s in prev.get('scratchpad_notes', [])) if prev.get('scratchpad_notes') else "No scratchpad notes."}

3. Today's Google Calendar Events & Schedule:
{cal_summary_str}

{workout_section_input}

5. Life Dashboard & System Status:
- Website (DroidZero): {apis.get('website', {}).get('message', 'Online')}
- Server Instance Load: {apis.get('instance', {}).get('load_avg', 'Normal')} | Disk Free: {apis.get('instance', {}).get('disk_free_gb', 'N/A')}
- Chicago Weather: {apis.get('weather', {}).get('summary', 'Seasonal')}
- Gmail Triage: {apis.get('gmail', {}).get('status', 'Ready')}
- Google Calendar: {cal_data.get('status', 'Ready')}
- Market Overview: {markets_str}

6. System Health Alerts / Incidents Requiring Action:
{chr(10).join(f"- 🚨 {inc}" for inc in (system_incidents or [])) if system_incidents else "All systems fully operational."}

7. Today's Reflection Quote:
"{quote_text}" — {quote_author} (Theme: {quote_theme})

8. Today's Real News Headlines:
{news_summary_str}

9. Unread Inbound Email Candidates & Triage:
{email_candidates_str}
---

Formatting Guidelines:
1. Output valid Markdown only. Start with Obsidian YAML frontmatter formatted with Dataview metadata:
---
date: {today_str}
tags:
  - daily-note
type: daily-note
program_week: {week}
program_day: {day}
workout: "{workout.get('title', 'Rest / Recovery')}"
body_weight: 191
workout_completed: false
---
2. Create clear, motivating sections:
   - Header with Date: '# 📅 {weekday_name}, {today_str}'.
   - Daily Reflection Quote: Directly under the header, place the daily reflection quote in a blockquote:
     > 💭 *"{quote_text}"*
     > — **{quote_author}**
   - Weather and system pulse summary line directly below the quote.
   - ## 🎯 To-do
     Must contain two clearly organized subsections:
     ### 📅 Today's Schedule
     - List each Google Calendar event for today with interactive checkboxes: `- [ ] ⏰ 09:00 AM – 10:00 AM: Meeting Title ([Join Meet](url)) *(Account A)*` or `- [ ] 🗓️ All Day: Event Name`.
     - If there are no scheduled events, output: `*No scheduled calendar events today.*`
     ### 📋 Priorities & Tasks
     - CRITICAL - SYSTEM OUTAGES & WARNINGS: If any system is down, degraded, or requires reauthorization (listed in "System Health Alerts / Incidents"), you MUST create an urgent checklist task `- [ ] ⚠️` at the TOP of Priorities & Tasks to investigate and fix it (e.g. `- [ ] ⚠️ Reauthorize Google Calendar API: Run python3 reauth_google.py in terminal`; `- [ ] 🚨 Investigate DroidZero downtime`).
     - Convert EVERY thought, errand, reminder, or idea from "Yesterday's Scratchpad & Tomorrow's Ideas" into an actionable checklist task `- [ ]`.
     - ACTION FROM PRIORITY EMAIL: If the priority email requires an action (e.g. paying a bill, retrieving a package with access code, confirming travel, or replying to an urgent request), ALSO create an actionable checklist item `- [ ]` here.
     - Also carry over any unfinished `- [ ]` tasks from the previous note.
     - MANDATORY DAILY HYGIENE HABITS: Always include these daily personal hygiene items at the end of Priorities & Tasks:
{mandatory_tasks_str}
     - Ensure no task, idea, or system alert is lost or omitted.
   - ## 📬 Priority Email Spotlight
     Review the unread email candidates. Identify the single most important or urgent email (favoring actionable human correspondence, bills, deliveries, travel, or account security alerts over automated marketing/newsletters).
     Format as:
     > **Account**: [Account A or B] • **From**: [Sender Name / Email]
     > **Subject**: [Subject Line]
     > **Summary**: [2-3 concise sentences detailing what the email is, key dates/numbers/codes, and why it matters].
     If all inboxes are caught up (zero unread), output:
     > *All inboxes clear. Zero unread priority emails requiring attention.*
   {workout_format_instruction}
   - ## 📰 Daily News Briefing
     Present today's authentic news headlines with clickable links:
{news_summary_str}
   - ## 📊 Life Dashboard Pulse (compact table or bullets covering DroidZero, VM health, Gmail triage, Calendar sync status, and Market Watchlist).
   - ## 📝 Scratchpad & Tomorrow's Ideas (empty space for the user to jot notes during the day).
3. Ensure all workout items (if workout is active today) have interactive checkboxes: `- [ ] [**Exercise Name**](URL) ↗ — target` and an indented line `  - Actual: `___ lbs x ___ reps`` for mobile logging.
4. Keep the output clean, sharp, and directly usable in Obsidian. Do not wrap in ```markdown code fences.
"""

    def _call_gemini_rest_api(
        self,
        today_str: str,
        weekday_name: str,
        prev: Dict[str, any],
        workout: Dict[str, any],
        apis: Dict[str, any],
        system_incidents: Optional[List[str]] = None,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        mandatory_tasks: Optional[List[str]] = None
    ) -> Optional[str]:
        """Calls Google Gemini REST API directly without requiring any pip dependencies."""
        prompt = self._build_prompt(
            today_str, weekday_name, prev, workout, apis, system_incidents,
            timeline, working_weights, mandatory_tasks
        )

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
        system_incidents: Optional[List[str]] = None,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        mandatory_tasks: Optional[List[str]] = None
    ) -> Optional[str]:
        """Calls Gemini using google-genai or google-generativeai SDK if available."""
        prompt = self._build_prompt(
            today_str, weekday_name, prev, workout, apis, system_incidents,
            timeline, working_weights, mandatory_tasks
        )

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
        system_incidents: Optional[List[str]] = None,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        mandatory_tasks: Optional[List[str]] = None
    ) -> str:
        """Deterministic high-quality fallback generator."""
        incomplete = prev.get("incomplete_tasks", [])
        scratch = prev.get("scratchpad_notes", [])

        week = timeline.get("week", 1) if timeline else 1
        day = timeline.get("day", 1) if timeline else 1
        cycle_str = f"Week {week}, Day {day}"

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

        # Check for actionable priority email
        gmail_data = apis.get("gmail", {})
        top_email = gmail_data.get("top_email")
        if top_email:
            subj = top_email.get("subject", "").lower()
            snd = top_email.get("sender", "").lower()
            if "luxer" in snd or "package" in subj:
                tasks_md.append(f"- [ ] 📦 Retrieve package: {top_email.get('subject')}")
            elif "payment" in subj or "due" in subj or "bill" in subj:
                tasks_md.append(f"- [ ] 💳 Action needed: {top_email.get('subject')}")

        # Mandatory daily hygiene habits
        mandatory_checklist = mandatory_tasks or ["Brush Teeth & Floss", "Wash Face"]
        for m_task in mandatory_checklist:
            tasks_md.append(f"- [ ] {m_task}")

        cal_data = apis.get("calendar", {})
        cal_lines = cal_data.get("calendar_lines", [])

        todo_blocks = ["### 📅 Today's Schedule"]
        if cal_lines:
            todo_blocks.extend(cal_lines)
        else:
            todo_blocks.append("*No scheduled calendar events today.*")

        todo_blocks.append("\n### 📋 Priorities & Tasks")
        todo_blocks.extend(tasks_md)

        # Quote of the day
        quote_data = apis.get("quote", {})
        if quote_data and "quote" in quote_data:
            quote_md = f'> 💭 *"{quote_data["quote"]}"*\n> — **{quote_data.get("author", "Unknown")}**'
        else:
            quote_md = '> 💭 *"We are what we repeatedly do. Excellence, then, is not an act, but a habit."*\n> — **Will Durant**'

        # Priority Email Spotlight
        if top_email:
            priority_email_md = f"""---

## 📬 Priority Email Spotlight
> **Account**: {top_email.get('account', 'Gmail')} • **From**: {top_email.get('sender', 'Unknown')}
> **Subject**: {top_email.get('subject', 'No Subject')}
> **Summary**: {top_email.get('summary', '')}"""
        else:
            priority_email_md = """---

## 📬 Priority Email Spotlight
> *All inboxes clear. Zero unread priority emails requiring attention.*"""

        is_workout_skipped = workout.get("skipped", False)
        if is_workout_skipped:
            workout_section_md = ""
        else:
            workout_exercises = []
            for ex in workout.get("exercises", []):
                url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
                workout_exercises.append(f"- [ ] **{url_part}** — {ex['target']}")
                workout_exercises.append(f"  - Form Cue: *{ex['cue']}*")
                workout_exercises.append(f"  - Actual: `___ lbs x ___ reps`")

            workout_section_md = f"""---

## 🏋️ Workout ({cycle_str}): {workout.get('title')}
> **Category:** {workout.get('category')} • **Target Goal:** {workout.get('goal')}
> **Biometrics:** Current BMI: `{workout.get('current_bmi', 27.4)}` • Goal: `165–170 lbs` (`-{workout.get('weight_to_lose', 23.5)} lbs` to target)

{chr(10).join(workout_exercises)}

> [!TIP]
> **Desk Worker Posture Cue:** {workout.get('desk_mobility')}
"""

        # News Briefing
        news = apis.get("news", {})
        chicago_n = news.get("chicago", {})
        us_n = news.get("us", {})
        world_n = news.get("world", {})
        news_lines = []
        if chicago_n.get("link"):
            news_lines.append(f"- 🏙️ **Chicago**: [{chicago_n.get('title', 'Local news')}]({chicago_n.get('link')}) *({chicago_n.get('source', 'WGN-TV')})*")
        else:
            news_lines.append(f"- 🏙️ **Chicago**: {chicago_n.get('title', 'Local news unavailable')}")

        if us_n.get("link"):
            news_lines.append(f"- 🇺🇸 **US**: [{us_n.get('title', 'National news')}]({us_n.get('link')}) *({us_n.get('source', 'NPR')})*")
        else:
            news_lines.append(f"- 🇺🇸 **US**: {us_n.get('title', 'National news unavailable')}")

        if world_n.get("link"):
            news_lines.append(f"- 🌍 **World**: [{world_n.get('title', 'World news')}]({world_n.get('link')}) *({world_n.get('source', 'BBC News')})*")
        else:
            news_lines.append(f"- 🌍 **World**: {world_n.get('title', 'World news unavailable')}")

        news_section_md = f"""---

## 📰 Daily News Briefing
{chr(10).join(news_lines)}"""

        market_lines = " • ".join(q.get("display", "") for q in apis.get("markets", []))

        return f"""---
date: {today_str}
day: {weekday_name}
tags:
  - daily-note
type: daily-note
program_week: {week}
program_day: {day}
workout: "{workout.get('title', 'Rest / Recovery')}"
body_weight: 191
workout_completed: false
---

# 📅 Daily Plan: {weekday_name}, {today_str}

{quote_md}

> 🌤️ **Chicago Weather:** {apis.get('weather', {}).get('summary', 'Chicago, IL')}
> 🌐 **DroidZero:** {apis.get('website', {}).get('message', 'Online')} • **VM Load:** `{apis.get('instance', {}).get('load_avg', 'N/A')}`

---

## 🎯 To-do

{chr(10).join(todo_blocks)}
{priority_email_md}
{workout_section_md}
{news_section_md}

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
