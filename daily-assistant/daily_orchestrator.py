#!/usr/bin/env python3
"""
Daily Assistant & Life Dashboard Orchestrator
Stateless, autonomous batch script that prepares your daily Obsidian note.
"""

import sys
import argparse
from datetime import date, datetime
from pathlib import Path

# Add script directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import config
from modules.note_parser import NoteParser
from modules.workout_engine import WorkoutEngine
from modules.api_hub import ApiHub
from modules.gemini_client import GeminiClient
from modules.notifier import Notifier

def run_orchestration(target_date: date, dry_run: bool = False, force: bool = False):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Starting Daily Assistant Orchestrator for {target_date}...")
    
    # 0. Sync and pull latest previous note from CouchDB if on OCI VM with livesync-cli
    import shutil
    import subprocess
    from datetime import timedelta
    if shutil.which("livesync-cli") and not dry_run:
        try:
            subprocess.run(["livesync-cli", "sync"], timeout=30, check=False)
            yesterday_str = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
            rel_path = f"Daily/{yesterday_str}.md"
            subprocess.run(["livesync-cli", "pull", rel_path, f"/data/{rel_path}"], timeout=15, check=False)
        except Exception as e:
            print(f"    Notice: Pre-orchestration LiveSync pull encountered: {e}")

    # 1. Initialize modules
    parser = NoteParser(config.DAILY_DIR)
    workout_engine = WorkoutEngine(config.USER_PROFILE)
    api_hub = ApiHub(
        config.DROIDZERO_URL,
        config.GMAIL_CREDENTIALS_PATH,
        config.GMAIL_TOKENS_DIR
    )
    gemini_client = GeminiClient(
        config.GEMINI_API_KEY,
        config.GEMINI_MODEL
    )

    # 2. Parse previous note
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📖 Reading previous daily note context...")
    prev_result = parser.find_previous_note(target_date)
    prev_data = {}
    if prev_result:
        prev_date, prev_path = prev_result
        print(f"    Found previous note: {prev_path.name}")
        prev_data = parser.parse_note_content(prev_path)
        print(f"    Carrying forward {len(prev_data['incomplete_tasks'])} incomplete tasks.")
        print(f"    Converting {len(prev_data['scratchpad_notes'])} scratchpad items from yesterday into to-dos.")
    else:
        print("    No previous note found in rolling 14-day window. Initializing fresh start.")
        prev_data = {
            "incomplete_tasks": [],
            "completed_count": 0,
            "scratchpad_notes": [],
            "workout_logs": []
        }

    # 3. Get workout routine
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏋️ Determining today's workout & recovery plan...")
    workout_data = workout_engine.get_today_routine(target_date)
    print(f"    Selected routine: {workout_data['title']} ({workout_data['category']})")

    # 4. Gather Live API metrics
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 Gathering Life Dashboard & external API metrics...")
    website_status = api_hub.check_website_status()
    print(f"    DroidZero: {website_status['message']}")

    instance_health = api_hub.get_instance_health()
    print(f"    Instance Load: {instance_health['load_avg']} | Free Disk: {instance_health['disk_free_gb']}")

    weather = api_hub.get_chicago_weather()
    print(f"    Chicago Weather: {weather['summary']}")

    markets = api_hub.get_market_watchlist(config.TRACKED_TICKERS, target_date)
    if target_date.weekday() >= 5:
        print("    Markets: Weekend detected (markets closed).")
    else:
        print(f"    Markets: {len(markets)} assets polled with trend indicators.")

    gmail_triage = api_hub.get_gmail_triage()
    print(f"    Gmail Triage: {gmail_triage['status']}")

    calendar_data = {"events": [], "calendar_lines": [], "count": 0, "status": "Disabled"}
    if config.GOOGLE_CALENDAR_ENABLED:
        calendar_data = api_hub.get_calendar_events(
            target_date=target_date,
            timezone_name=config.CALENDAR_TIMEZONE,
            ics_urls=config.CALENDAR_ICS_URLS
        )
        print(f"    Google Calendar: {calendar_data['status']}")

    api_data = {
        "website": website_status,
        "instance": instance_health,
        "weather": weather,
        "markets": markets,
        "gmail": gmail_triage,
        "calendar": calendar_data
    }

    # 5. Synthesize note via Gemini (or fallback template)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✨ Formatting note via Gemini ({config.GEMINI_MODEL})...")
    note_content = gemini_client.generate_daily_note(
        today=target_date,
        previous_note_data=prev_data,
        workout_data=workout_data,
        api_data=api_data
    )

    # 6. Target file path
    target_file = config.DAILY_DIR / f"{target_date.strftime('%Y-%m-%d')}.md"

    if dry_run:
        print(f"\n--- [DRY RUN PREVIEW: {target_file}] ---\n")
        print(note_content)
        print("\n--- [END DRY RUN] ---\n")
        return

    # Check if target already exists
    if target_file.exists() and not force:
        print(f"⚠️ Note {target_file.name} already exists. Use --force to overwrite. Exiting without changes.")
        return

    # Ensure Daily/ directory exists
    config.DAILY_DIR.mkdir(parents=True, exist_ok=True)

    # Write note
    target_file.write_text(note_content, encoding="utf-8")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Successfully wrote today's note: {target_file}")

    # Optional: Update Finance Dashboard with current market prices (weekdays only)
    if target_date.weekday() < 5:
        try:
            update_finance_watchlist(config.FINANCE_FILE, markets)
        except Exception as e:
            print(f"    Notice: Could not auto-update Finance Dashboard table ({e})")

    # 7. Push and Sync to CouchDB (if on OCI VM with livesync-cli) before notifying
    import shutil
    import subprocess
    if shutil.which("livesync-cli"):
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Pushing newly created note to CouchDB via livesync-cli...")
            rel_path = f"Daily/{target_date.strftime('%Y-%m-%d')}.md"
            subprocess.run(["livesync-cli", "push", f"/data/{rel_path}", rel_path], timeout=30, check=False)
            subprocess.run(["livesync-cli", "sync"], timeout=30, check=False)
        except Exception as e:
            print(f"    Notice: livesync-cli push/sync prior to notification encountered: {e}")

    # 8. Dispatch push notification via ntfy (if enabled)
    if config.NTFY_ENABLED and config.NTFY_TOPIC:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📲 Sending mobile push notification via ntfy...")
            notifier = Notifier(
                topic=config.NTFY_TOPIC,
                server_url=config.NTFY_SERVER_URL,
                vault_name=config.OBSIDIAN_VAULT_NAME
            )
            sent = notifier.send_daily_note_notification(
                target_date=target_date,
                workout_data=workout_data,
                api_data=api_data,
                prev_data=prev_data
            )
            if sent:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📲 Push notification sent successfully to topic '{config.NTFY_TOPIC}'.")
        except Exception as e:
            print(f"    Notice: Could not send mobile notification ({e})")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Complete! Note is ready for Obsidian LiveSync.\n")

def update_finance_watchlist(finance_file: Path, markets: list):
    """Updates the Finance Dashboard table with freshly polled prices."""
    if not finance_file.exists() or not markets:
        return

    content = finance_file.read_text(encoding="utf-8")
    today_str = date.today().strftime("%Y-%m-%d")

    for item in markets:
        symbol = item.get("symbol")
        price = item.get("price")
        change = item.get("change_pct")
        if not symbol or price == "N/A":
            continue

        # Look for row e.g. | **VOO** (S&P 500 ETF) | Equity Index | $0.00 | - | - | 2026-09-09 |
        # Replace the price and change if line contains symbol
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if f"**{symbol}**" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7:
                    # parts[0] is empty, parts[1]=Asset, parts[2]=Type, parts[3]=Price, parts[4]=Change, parts[5]=Holdings, parts[6]=Date
                    parts[3] = price
                    parts[4] = change
                    parts[6] = today_str
                    line = "| " + " | ".join(parts[1:-1]) + " |"
            new_lines.append(line)
        content = "\n".join(new_lines)

    finance_file.write_text(content, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Daily Assistant & Life Dashboard Orchestrator")
    parser.add_argument("--date", type=str, help="Target date in YYYY-MM-DD format (defaults to today)")
    parser.add_argument("--dry-run", action="store_true", help="Print generated note to stdout without writing to vault")
    parser.add_argument("--force", action="store_true", help="Overwrite existing note for the target date")
    parser.add_argument("--test-notify", action="store_true", help="Send a test notification to verify phone delivery and deep link")

    args = parser.parse_args()

    if args.test_notify:
        if not config.NTFY_TOPIC:
            print("❌ Error: NTFY_TOPIC is not configured in config.py or .env")
            sys.exit(1)
        notifier = Notifier(
            topic=config.NTFY_TOPIC,
            server_url=config.NTFY_SERVER_URL,
            vault_name=config.OBSIDIAN_VAULT_NAME
        )
        print(f"Testing push notification to topic '{config.NTFY_TOPIC}'...")
        success = notifier.send_test_notification()
        if success:
            print("✅ Test notification sent! Check your iPhone.")
            sys.exit(0)
        else:
            print("❌ Failed to send test notification. Check logs above.")
            sys.exit(1)

    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Expected YYYY-MM-DD.")
            sys.exit(1)
    else:
        target_date = date.today()

    try:
        run_orchestration(target_date, dry_run=args.dry_run, force=args.force)
    except Exception as err:
        if config.NTFY_ENABLED and config.NTFY_TOPIC and not args.dry_run:
            try:
                notifier = Notifier(
                    topic=config.NTFY_TOPIC,
                    server_url=config.NTFY_SERVER_URL,
                    vault_name=config.OBSIDIAN_VAULT_NAME
                )
                notifier.send_failure_alert(str(err), target_date)
            except Exception:
                pass
        raise

if __name__ == "__main__":
    main()
