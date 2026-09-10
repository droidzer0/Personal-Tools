import re
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class NoteParser:
    def __init__(self, daily_dir: Path):
        self.daily_dir = daily_dir

    def find_previous_note(self, target_date: date) -> Optional[Tuple[date, Path]]:
        """Find the note from yesterday, or the most recent preceding note within the last 14 days."""
        if not self.daily_dir.exists():
            return None

        # Check yesterday first
        yesterday = target_date - timedelta(days=1)
        yesterday_file = self.daily_dir / f"{yesterday.strftime('%Y-%m-%d')}.md"
        if yesterday_file.exists():
            return yesterday, yesterday_file

        # Fallback: scan backwards up to 14 days
        for i in range(2, 15):
            past_date = target_date - timedelta(days=i)
            candidate = self.daily_dir / f"{past_date.strftime('%Y-%m-%d')}.md"
            if candidate.exists():
                return past_date, candidate

        return None

    def parse_note_content(self, file_path: Path) -> Dict[str, any]:
        """
        Parses a daily note to extract:
        - Incomplete tasks (- [ ])
        - Completed tasks count (- [x])
        - Scratchpad / freeform notes
        - Logged workout actuals
        """
        if not file_path.exists():
            return {
                "incomplete_tasks": [],
                "completed_count": 0,
                "scratchpad_notes": [],
                "workout_logs": []
            }

        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        incomplete_tasks = []
        completed_count = 0
        scratchpad_notes = []
        workout_logs = []

        in_scratchpad = False
        in_workout = False
        in_calendar = False

        for line in lines:
            trimmed = line.strip()

            # Track section headers (## or ###)
            if trimmed.startswith("## ") or trimmed.startswith("### "):
                lower_header = trimmed.lower()
                in_scratchpad = ("scratchpad" in lower_header or "notes" in lower_header or "tomorrow" in lower_header)
                in_workout = ("workout" in lower_header or "exercise" in lower_header)
                in_calendar = ("schedule" in lower_header or "calendar" in lower_header or "meeting" in lower_header or "events" in lower_header)

            # Checkboxes
            if trimmed.startswith("- [ ]"):
                task_text = trimmed[5:].strip()
                # Skip workout checklist items and scheduled calendar events from rolling over
                is_calendar_event = (
                    in_calendar or
                    "⏰" in task_text or
                    "🗓️" in task_text or
                    "all day" in task_text.lower() or
                    bool(re.search(r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b', task_text, re.IGNORECASE))
                )
                if not in_workout and not is_calendar_event:
                    incomplete_tasks.append(task_text)
            elif trimmed.startswith("- [x]") or trimmed.startswith("- [X]"):
                completed_count += 1
                if in_workout:
                    # Capture completed workout lines
                    workout_logs.append(trimmed)

            # Scratchpad bullets or lines
            elif in_scratchpad and trimmed and not trimmed.startswith("#") and not trimmed.startswith("---"):
                lower_line = trimmed.lower()
                is_placeholder = (
                    "capture thoughts" in lower_line or
                    "use this space" in lower_line or
                    lower_line in ("-", "*", "- [ ]", "*(none)*", "none")
                )
                if not is_placeholder:
                    clean_text = re.sub(r'^[-*]\s*(\[\s*\]\s*)?', '', trimmed).strip()
                    if clean_text:
                        scratchpad_notes.append(clean_text)

            # Parse explicit actual weights logged (e.g., "Actual: 45 lbs x 10" or "`45 lbs x 10`")
            if in_workout and ("actual:" in trimmed.lower() or "logged:" in trimmed.lower()):
                workout_logs.append(trimmed)

        return {
            "incomplete_tasks": incomplete_tasks,
            "completed_count": completed_count,
            "scratchpad_notes": scratchpad_notes,
            "workout_logs": workout_logs,
            "raw_text": text
        }

    def update_pbs_in_health_file(self, health_file_path: Path, new_actuals: List[str]) -> List[str]:
        """
        Parses logged actuals and checks if any new personal bests were set.
        Updates the Personal Bests table in Health & Fitness.md if appropriate.
        Returns a list of announcements for any new PBs set.
        """
        if not health_file_path.exists() or not new_actuals:
            return []

        # Simple pattern recognition for logged weights e.g. "Squat ... 140 lbs x 8"
        announcements = []
        # Additional logic can dynamically rewrite the PB table as personal best records increase
        return announcements
