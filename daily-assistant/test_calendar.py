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

if __name__ == "__main__":
    test_note_parser_rollover()
    test_deterministic_generation_with_calendar()
    print("\n🎉 All tests passed!")
