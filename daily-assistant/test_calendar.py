#!/usr/bin/env python3
"""
Test script to verify Google Calendar integration and task rollover protection in daily-assistant.
"""
import os
import sys
import io
import tempfile
import urllib.error
from datetime import date, datetime, timedelta
from email.message import Message
from pathlib import Path
from unittest.mock import patch

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

def test_mandatory_tasks_schedule():
    print("Testing mandatory daily and Wednesday-only medication schedule...")
    monday = date(2026, 11, 16)
    for offset in range(7):
        day = monday + timedelta(days=offset)
        tasks = config.get_mandatory_tasks_for_date(day)
        assert "Brush Teeth & Floss" in tasks, f"Missing hygiene task on {day}"
        assert "Wash Face" in tasks, f"Missing Wash Face on {day}"
        assert "Take Cholesterol Medication" in tasks, f"Missing Cholesterol Medication on {day}"
        if day.weekday() == 2:  # Wednesday (2026-11-18)
            assert "Take Vitamin D Medication" in tasks, f"Missing Vitamin D Medication on Wednesday {day}"
        else:
            assert "Take Vitamin D Medication" not in tasks, f"Unexpected Vitamin D Medication on non-Wednesday {day}"

    all_recurring = config.get_all_recurring_tasks()
    for expected in [
        "Brush Teeth & Floss",
        "Wash Face",
        "Take Cholesterol Medication",
        "Take Vitamin D Medication",
    ]:
        assert expected in all_recurring, f"Missing '{expected}' in get_all_recurring_tasks()"
    assert len(all_recurring) == len(set(all_recurring)), "get_all_recurring_tasks() must deduplicate tasks"
    print("✅ Mandatory tasks schedule test passed successfully!")


def test_medication_rollover_protection():
    print("Testing NoteParser medication rollover protection...")
    sample_content = """---
date: 2026-11-18
tags: [daily-note]
type: daily-note
---

# 📅 Daily Plan: Wednesday, 2026-11-18

## 🎯 To-do

### 📅 Today's Schedule
*No scheduled calendar events today.*

### 📋 Priorities & Tasks
- [ ] Pick up cholesterol prescription from pharmacy
- [ ] Refill Vitamin D prescription
- [ ] Brush Teeth & Floss
- [ ] Wash Face
- [ ] Take Cholesterol Medication
- [ ] Take Vitamin D Medication
- [ ] 💊 **Take Cholesterol Medication**
- [ ] Take weekly Vitamin D
"""
    test_file = SCRIPT_DIR / "sample_med_rollover_note.md"
    test_file.write_text(sample_content, encoding="utf-8")

    try:
        for parser in (
            NoteParser(SCRIPT_DIR),
            NoteParser(SCRIPT_DIR, recurring_tasks=config.get_all_recurring_tasks()),
        ):
            parsed = parser.parse_note_content(test_file)
            incomplete = parsed["incomplete_tasks"]
            assert "Pick up cholesterol prescription from pharmacy" in incomplete, "Should roll over cholesterol pharmacy errand"
            assert "Refill Vitamin D prescription" in incomplete, "Should roll over Vitamin D refill errand"
            assert "Brush Teeth & Floss" not in incomplete, "Should NOT roll over Brush Teeth & Floss"
            assert "Wash Face" not in incomplete, "Should NOT roll over Wash Face"
            assert "Take Cholesterol Medication" not in incomplete, "Should NOT roll over daily Cholesterol Medication"
            assert "Take Vitamin D Medication" not in incomplete, "Should NOT roll over Wednesday Vitamin D Medication"
            assert "💊 **Take Cholesterol Medication**" not in incomplete, "Should NOT roll over formatted Cholesterol Medication"
            assert "Take weekly Vitamin D" not in incomplete, "Should NOT roll over weekly Vitamin D variant"
    finally:
        if test_file.exists():
            test_file.unlink()

    print("✅ NoteParser medication rollover protection test passed successfully!")


def test_wednesday_vs_non_wednesday_generation():
    print("Testing Wednesday vs non-Wednesday note generation & prompt building...")
    client = GeminiClient(api_key="", model_name="gemini-2.5-flash")
    prev_data = {"incomplete_tasks": ["Ship feature"], "scratchpad_notes": []}
    workout_data = {
        "title": "Full Body Strength A",
        "category": "Strength",
        "goal": "Build foundation",
        "exercises": [],
        "desk_mobility": "Cat-cow stretch",
    }
    api_data = {
        "website": {"message": "🟢 Online (HTTP 200)"},
        "instance": {"load_avg": "0.10, 0.10, 0.10", "disk_free_gb": "80.0 GB"},
        "weather": {"summary": "45°F • Clear"},
        "markets": [{"display": "**VOO**: $680.00 (🟢 +0.50%)"}],
        "gmail": {"status": "🟢 0 unread"},
        "calendar": {"calendar_lines": [], "status": "🟢 0 events"},
    }

    wednesday = date(2026, 11, 18)
    thursday = date(2026, 11, 19)

    for explicit_tasks in (True, False):
        wed_tasks = config.get_mandatory_tasks_for_date(wednesday) if explicit_tasks else None
        thu_tasks = config.get_mandatory_tasks_for_date(thursday) if explicit_tasks else None

        wed_prompt = client._build_prompt(
            today_str=wednesday.strftime("%Y-%m-%d"),
            weekday_name=wednesday.strftime("%A"),
            prev=prev_data,
            workout=workout_data,
            apis=api_data,
            mandatory_tasks=wed_tasks,
        )
        thu_prompt = client._build_prompt(
            today_str=thursday.strftime("%Y-%m-%d"),
            weekday_name=thursday.strftime("%A"),
            prev=prev_data,
            workout=workout_data,
            apis=api_data,
            mandatory_tasks=thu_tasks,
        )

        assert "- [ ] Take Cholesterol Medication" in wed_prompt
        assert "- [ ] Take Vitamin D Medication" in wed_prompt
        assert "- [ ] Take Cholesterol Medication" in thu_prompt
        assert "Take Vitamin D Medication" not in thu_prompt

        wed_note = client.generate_daily_note(
            today=wednesday,
            previous_note_data=prev_data,
            workout_data=workout_data,
            api_data=api_data,
            mandatory_tasks=wed_tasks,
        )
        thu_note = client.generate_daily_note(
            today=thursday,
            previous_note_data=prev_data,
            workout_data=workout_data,
            api_data=api_data,
            mandatory_tasks=thu_tasks,
        )

        assert "- [ ] Take Cholesterol Medication" in wed_note
        assert "- [ ] Take Vitamin D Medication" in wed_note
        assert "- [ ] Take Cholesterol Medication" in thu_note
        assert "Take Vitamin D Medication" not in thu_note

    print("✅ Wednesday vs non-Wednesday generation test passed successfully!")


def test_github_token_expiration_parsing():
    print("Testing _parse_github_token_expiration across GitHub header formats...")
    from modules.api_hub import _parse_github_token_expiration

    assert _parse_github_token_expiration("2027-02-22 15:19:44 UTC") == datetime(2027, 2, 22, 15, 19, 44)
    assert _parse_github_token_expiration("2027-02-22 15:19:44 -0800") == datetime(2027, 2, 22, 23, 19, 44)
    assert _parse_github_token_expiration("2027-02-22 15:19:44 +0530") == datetime(2027, 2, 22, 9, 49, 44)
    assert _parse_github_token_expiration("2027-02-22T23:19:44Z") == datetime(2027, 2, 22, 23, 19, 44)
    assert _parse_github_token_expiration("2027-02-22T15:19:44-08:00") == datetime(2027, 2, 22, 23, 19, 44)
    assert _parse_github_token_expiration("") is None
    assert _parse_github_token_expiration("not-a-date") is None
    assert _parse_github_token_expiration(None) is None
    print("✅ _parse_github_token_expiration test passed successfully!")


class _MockHTTPResponse:
    def __init__(self, headers: dict, body: bytes = b"{}"):
        self.headers = headers
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _assert_token_not_leaked(dummy_token: str, info: dict, incidents: list):
    for k, v in info.items():
        assert dummy_token not in str(v), f"Raw token leaked in info[{k}]"
    for inc in incidents:
        assert dummy_token not in inc, "Raw token leaked in incident message"


def test_backup_token_tracker_and_incidents():
    print("Testing ApiHub._read_env_var, _check_github_backup_token, and extract_system_incidents...")
    from modules.api_hub import ApiHub

    dummy_token = "github_pat_TEST_SECRET_DO_NOT_LEAK_12345"
    old_token = "github_pat_OLD_STALE_TOKEN_00000"
    now_utc = datetime(2026, 11, 24, 15, 0, 0)

    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir) / ".env"
        env_path.write_text(
            "# DroidZero env\n"
            f'BACKUP_GITHUB_TOKEN="{old_token}"\n'
            "GITHUB_TOKEN='ghp_unrelated_site_token'\n"
            f"export BACKUP_GITHUB_TOKEN='{dummy_token}'\n",
            encoding="utf-8",
        )
        assert ApiHub._read_env_var(env_path, "BACKUP_GITHUB_TOKEN") == dummy_token
        assert ApiHub._read_env_var(env_path, "MISSING_KEY") is None
        assert ApiHub._read_env_var(Path(tmpdir) / "nonexistent.env", "BACKUP_GITHUB_TOKEN") is None

        clean_env = {k: v for k, v in os.environ.items() if k != "BACKUP_GITHUB_TOKEN"}
        with patch.dict(os.environ, clean_env, clear=True):
            hub = ApiHub(
                droidzero_url="https://droidzero.duckdns.org",
                gmail_creds_path=Path("."),
                gmail_tokens_dir=Path("."),
                droidzero_env_path=env_path,
                backup_github_repo="droidzer0/droidzero-backups",
            )

            # 1. Live 200: 60 days out -> green, 0 incidents
            with patch.object(ApiHub, "_check_systemd_timer", return_value="active"), patch(
                "urllib.request.urlopen",
                return_value=_MockHTTPResponse({"github-authentication-token-expiration": "2027-01-23 07:00:00 -0800"}),
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_days_remaining"] == 60
            assert info["backup_token_expires_on"] == "2027-01-23"
            assert info["backup_token_expired"] is False
            assert info["backup_token_status"].startswith("🟢 60 days until expiration (expires 2027-01-23)")
            assert "backup timer active" in info["backup_token_status"]
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert incidents == []
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 2. Live 200: 14 days out -> yellow, 1 incident
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                return_value=_MockHTTPResponse({"github-authentication-token-expiration": "2026-12-08 07:00:00 -0800"}),
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_days_remaining"] == 14
            assert info["backup_token_status"] == "🟡 14 days until expiration (expires 2026-12-08)"
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert len(incidents) == 1
            assert "14 days until expiration" in incidents[0]
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 3. Live 200: 5 days out -> red, 1 incident
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                return_value=_MockHTTPResponse({"github-authentication-token-expiration": "2026-11-29 15:00:00 UTC"}),
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_days_remaining"] == 5
            assert info["backup_token_status"] == "🔴 5 days until expiration (expires 2026-11-29)"
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert len(incidents) == 1
            assert "5 days until expiration" in incidents[0]
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 4. Live 200: < 24h remaining -> Expires today / < 1 day left, expired == False, 1 incident
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                return_value=_MockHTTPResponse({"github-authentication-token-expiration": "2026-11-24 23:00:00 UTC"}),
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_days_remaining"] == 0
            assert info["backup_token_expired"] is False
            assert info["backup_token_status"] == "🔴 Expires today / < 1 day left (expires 2026-11-24)"
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert len(incidents) == 1
            assert "0 days until expiration" in incidents[0]
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 5. Live 200: no expiration header -> Valid (no expiration set), 0 incidents
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                return_value=_MockHTTPResponse({}),
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_no_expiry"] is True
            assert info["backup_token_status"] == "🟢 Valid (no expiration set)"
            assert ApiHub.extract_system_incidents({"website": info}) == []

            # 6. Live HTTP 401 -> expired, immediate rotation incident
            err_401 = urllib.error.HTTPError(
                url="https://api.github.com/repos/droidzer0/droidzero-backups",
                code=401,
                msg="Unauthorized",
                hdrs=Message(),
                fp=io.BytesIO(b""),
            )
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                side_effect=err_401,
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_expired"] is True
            assert info["backup_token_status"].startswith("🔴 Expired / Unauthorized")
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert len(incidents) == 1
            assert "immediately" in incidents[0]
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 7. Live HTTP 403 with expiration header -> expiration + permission warning incident
            hdrs_403 = Message()
            hdrs_403["github-authentication-token-expiration"] = "2027-01-23 15:00:00 UTC"
            err_403 = urllib.error.HTTPError(
                url="https://api.github.com/repos/droidzer0/droidzero-backups",
                code=403,
                msg="Forbidden",
                hdrs=hdrs_403,
                fp=io.BytesIO(b""),
            )
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                side_effect=err_403,
            ):
                info = hub._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_days_remaining"] == 60
            assert "HTTP 403" in info["backup_token_status"]
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert len(incidents) == 1
            assert "Check DroidZero backup GitHub token permissions" in incidents[0]
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 8. Unreachable GitHub API + BACKUP_TOKEN_EXPIRES_ON fallback
            hub_fallback = ApiHub(
                droidzero_url="https://droidzero.duckdns.org",
                gmail_creds_path=Path("."),
                gmail_tokens_dir=Path("."),
                droidzero_env_path=env_path,
                backup_github_repo="droidzer0/droidzero-backups",
                backup_token_expires_on="2027-02-22",
            )
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None), patch(
                "urllib.request.urlopen",
                side_effect=OSError(f"Network down while sending {dummy_token}"),
            ):
                info = hub_fallback._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_source"] == "config_fallback"
            assert info["backup_token_days_remaining"] == 90
            assert info["backup_token_error"] is None
            assert info["backup_token_status"] == "🟢 90 days until expiration (expires 2027-02-22)"
            incidents = ApiHub.extract_system_incidents({"website": info})
            assert incidents == []
            _assert_token_not_leaked(dummy_token, info, incidents)

            # 9. No token and no fallback -> white unavailable status, 0 false incidents
            hub_none = ApiHub(
                droidzero_url="https://droidzero.duckdns.org",
                gmail_creds_path=Path("."),
                gmail_tokens_dir=Path("."),
                droidzero_env_path=Path(tmpdir) / "missing.env",
            )
            with patch.object(ApiHub, "_check_systemd_timer", return_value=None):
                info = hub_none._check_github_backup_token(now_utc=now_utc)
            assert info["backup_token_status"].startswith("⚪ Backup token expiry unavailable")
            assert ApiHub.extract_system_incidents({"website": info}) == []

    print("✅ Backup token tracker and incident tests passed successfully!")


def test_backup_token_rendered_and_rollover_dedup():
    print("Testing GeminiClient rendering and NoteParser expiry alert rollover dedup...")
    client = GeminiClient(api_key="", model_name="gemini-2.5-flash")
    prev_data = {"incomplete_tasks": ["Rotate personal SSH keys"], "scratchpad_notes": []}
    workout_data = {
        "title": "Full Body Strength A",
        "category": "Strength",
        "goal": "Build foundation",
        "exercises": [],
        "desk_mobility": "Cat-cow stretch",
    }
    status_str = "🟢 89 days until expiration (expires 2027-02-22) • backup timer active"
    api_data = {
        "website": {
            "message": "🟢 Online (HTTP 200)",
            "duckdns_status": "🟢 Active (droidzero.duckdns.org → 147.224.207.15)",
            "cert_status": "🟢 56 days until expiration (expires 2027-01-19)",
            "backup_token_status": status_str,
        },
        "instance": {"load_avg": "0.10, 0.10, 0.10", "disk_free_gb": "80.0 GB"},
        "weather": {"summary": "45°F • Clear"},
        "markets": [{"display": "**VOO**: $680.00 (🟢 +0.50%)"}],
        "gmail": {"status": "🟢 0 unread"},
        "calendar": {"calendar_lines": [], "status": "🟢 0 events"},
    }

    target = date(2026, 11, 24)
    prompt = client._build_prompt(
        today_str=target.strftime("%Y-%m-%d"),
        weekday_name=target.strftime("%A"),
        prev=prev_data,
        workout=workout_data,
        apis=api_data,
    )
    assert f"- GitHub Backup Token (`backup-token`): {status_str}" in prompt
    assert "**🔑 GitHub Backup Token**" in prompt

    note = client.generate_daily_note(
        today=target,
        previous_note_data=prev_data,
        workout_data=workout_data,
        api_data=api_data,
    )
    assert f"| **🔑 GitHub Backup Token** | {status_str} |" in note

    # Rollover dedup: auto-generated expiry alerts must not stack across consecutive days
    sample_note = """---
date: 2026-11-24
tags: [daily-note]
type: daily-note
---

## 🎯 To-do

### 📋 Priorities & Tasks
- [ ] ⚠️ Rotate DroidZero backup GitHub token: 14 days until expiration (2026-12-08) — update BACKUP_GITHUB_TOKEN in /opt/droidzero-api/.env
- [ ] ⚠️ Renew DroidZero SSL certificate: 12 days until expiration (2026-12-06)
- [ ] ⚠️ Renew or disable Tailscale node key expiry: 10 days until expiration (2026-12-04)
- [ ] Rotate personal SSH keys
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        note_file = Path(tmpdir) / "2026-11-24.md"
        note_file.write_text(sample_note, encoding="utf-8")
        parser = NoteParser(Path(tmpdir), recurring_tasks=config.get_all_recurring_tasks())
        parsed = parser.parse_note_content(note_file)
        assert parsed["incomplete_tasks"] == ["Rotate personal SSH keys"], (
            f"Expected only regular user task to roll over, got: {parsed['incomplete_tasks']}"
        )

    print("✅ Backup token rendering and rollover dedup tests passed successfully!")


if __name__ == "__main__":
    test_note_parser_rollover()
    test_deterministic_generation_with_calendar()
    test_parse_ics_feed()
    test_mandatory_tasks_schedule()
    test_medication_rollover_protection()
    test_wednesday_vs_non_wednesday_generation()
    test_github_token_expiration_parsing()
    test_backup_token_tracker_and_incidents()
    test_backup_token_rendered_and_rollover_dedup()
    print("\n🎉 All tests passed!")

