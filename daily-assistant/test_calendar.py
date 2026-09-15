#!/usr/bin/env python3
"""
Test script to verify Google Calendar integration and task rollover protection in daily-assistant.
"""
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config
from modules.note_parser import NoteParser
from modules.gemini_client import GeminiClient

def test_note_parser_rollover():
    print("Testing NoteParser rollover protection...")
    parser = NoteParser(SCRIPT_DIR)

    # Mock note content with calendar events and regular tasks
    sample_content = """---
date: 2026-09-09
tags: [daily-note]
type: daily-note
---

# Wednesday, September 9, 2026

## 🎯 To-do

### 📅 Today's Schedule
- [ ] ⏰ 09:00 AM – 10:00 AM: Team Sync Meeting (Account A)
- [ ] ⏰ 02:00 PM – 02:30 PM: 1-on-1 with Bob
- [ ] 🗓️ All Day: Hackathon Day 1

### 📋 Priorities & Tasks
- [ ] Implement Google Calendar sync
- [x] Complete daily assistant refactor
- [ ] Buy groceries for dinner

## 🏋️ Workout: Full Body Strength
- [ ] [Bench Press](https://musclewiki.com) ↗ — 3x10
  - Actual: 135 lbs x 10

## 📝 Scratchpad & Tomorrow's Ideas
- Look into calendar widgets
"""
    test_file = SCRIPT_DIR / "sample_test_note.md"
    test_file.write_text(sample_content, encoding="utf-8")

    try:
        parsed = parser.parse_note_content(test_file)
    finally:
        if test_file.exists():
            test_file.unlink()

    print(f"Parsed incomplete tasks: {parsed['incomplete_tasks']}")

    # Assertions
    assert "Implement Google Calendar sync" in parsed['incomplete_tasks'], "Should keep regular task 1"
    assert "Buy groceries for dinner" in parsed['incomplete_tasks'], "Should keep regular task 2"
    assert not any("Team Sync" in t for t in parsed['incomplete_tasks']), "Should NOT rollover Team Sync meeting!"
    assert not any("1-on-1" in t for t in parsed['incomplete_tasks']), "Should NOT rollover 1-on-1 meeting!"
    assert not any("Hackathon" in t for t in parsed['incomplete_tasks']), "Should NOT rollover All Day event!"
    assert not any("Bench Press" in t for t in parsed['incomplete_tasks']), "Should NOT rollover workout items!"
    print("✅ NoteParser rollover protection test passed successfully!")

def test_deterministic_generation_with_calendar():
    print("Testing deterministic generation with calendar events...")
    client = GeminiClient(api_key="", model_name="gemini-2.5-flash")

    prev_data = {
        "incomplete_tasks": ["Ship calendar feature"],
        "scratchpad_notes": []
    }
    workout_data = {
        "title": "Full Body Strength A",
        "category": "Strength",
        "goal": "Build foundation",
        "exercises": [],
        "desk_mobility": "Cat-cow stretch"
    }
    api_data = {
        "website": {"message": "🟢 Online (HTTP 200)"},
        "instance": {"load_avg": "1.20, 1.10, 1.05", "disk_free_gb": "90.0 GB"},
        "weather": {"summary": "72°F • Clear"},
        "markets": [{"display": "**VOO**: $700.00 (🟢 +0.50%)"}],
        "gmail": {"status": "🟢 0 unread"},
        "calendar": {
            "calendar_lines": [
                "- [ ] ⏰ 09:30 AM – 10:30 AM: Architecture Review ([Join Meet](https://meet.google.com/abc)) *(Account A)*",
                "- [ ] 🗓️ All Day: Team Planning Offsite *(Account B)*"
            ],
            "status": "🟢 2 events scheduled today"
        }
    }

    result = client.generate_daily_note(
        today=date(2026, 9, 10),
        previous_note_data=prev_data,
        workout_data=workout_data,
        api_data=api_data
    )

    print("\nGenerated Note Preview:")
    print("-" * 50)
    print(result[:1000])
    print("-" * 50)

    assert "### 📅 Today's Schedule" in result, "Must contain Today's Schedule header"
    assert "09:30 AM – 10:30 AM: Architecture Review" in result, "Must contain timed event"
    assert "All Day: Team Planning Offsite" in result, "Must contain all-day event"
    assert "### 📋 Priorities & Tasks" in result, "Must contain Priorities & Tasks header"
    assert "Ship calendar feature" in result, "Must contain rolled over task"
    assert "📅 Google Calendar" in result, "Must show Google Calendar in Life Dashboard pulse"
    print("✅ Deterministic note generation test passed successfully!")

def test_parse_ics_feed():
    print("Testing ApiHub._parse_ics_feed iCloud integration...")
    from modules.api_hub import ApiHub
    from zoneinfo import ZoneInfo
    hub = ApiHub(droidzero_url="", gmail_creds_path=Path("."), gmail_tokens_dir=Path("."))

    sample_ics = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Apple Inc.//Mac OS X 10.15.7//EN
X-WR-CALNAME:Home
BEGIN:VEVENT
UID:event-1
SUMMARY:Lap Swim
DTSTART;TZID=America/Chicago:20260915T070000
DTEND;TZID=America/Chicago:20260915T073000
LOCATION:FFC - West Loop
END:VEVENT
BEGIN:VEVENT
UID:event-2
SUMMARY:Happy Hour with
  Team
DTSTART;TZID=America/Chicago:20260915T170000
DTEND;TZID=America/Chicago:20260915T180000
LOCATION:Bar Siena
END:VEVENT
BEGIN:VEVENT
UID:event-3
SUMMARY:Old Cancelled Meeting
STATUS:CANCELLED
DTSTART;TZID=America/Chicago:20260915T120000
DTEND;TZID=America/Chicago:20260915T130000
END:VEVENT
BEGIN:VEVENT
UID:event-4
SUMMARY:Annual Review
RRULE:FREQ=YEARLY
DTSTART;VALUE=DATE:20200915
DTEND;VALUE=DATE:20200916
END:VEVENT
BEGIN:VEVENT
UID:event-5
SUMMARY:Tomorrow Meeting
DTSTART;TZID=America/Chicago:20260916T090000
DTEND;TZID=America/Chicago:20260916T100000
END:VEVENT
END:VCALENDAR"""

    target = date(2026, 9, 15)
    tz = ZoneInfo("America/Chicago")
    events, cal_name = hub._parse_ics_feed(sample_ics, target, tz)

    assert cal_name == "Home", f"Expected 'Home', got '{cal_name}'"
    assert len(events) == 3, f"Expected 3 events (2 timed + 1 yearly recurrence), got {len(events)}"

    summaries = [e["summary"] for e in events]
    assert "Lap Swim" in summaries, "Missing Lap Swim"
    assert "Happy Hour with Team" in summaries, "Failed line unfolding on Happy Hour"
    assert "Annual Review" in summaries, "Missing annual recurrence event"
    assert "Old Cancelled Meeting" not in summaries, "Cancelled event was not filtered"
    assert "Tomorrow Meeting" not in summaries, "Tomorrow's event incorrectly matched"

    lap_swim = next(e for e in events if e["summary"] == "Lap Swim")
    assert lap_swim["time_display"] == "7:00 AM – 7:30 AM"
    assert lap_swim["account"] == "iCloud"
    assert lap_swim["calendar"] == "Home"
    print("✅ ApiHub._parse_ics_feed tests passed successfully!")

if __name__ == "__main__":
    test_note_parser_rollover()
    test_deterministic_generation_with_calendar()
    test_parse_ics_feed()
    print("\n🎉 All tests passed!")

