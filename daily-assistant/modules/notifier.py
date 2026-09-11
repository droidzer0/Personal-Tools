"""
Push Notification Module for Daily Assistant
Sends notifications via ntfy.sh with deep links to open daily notes in Obsidian on iOS.
Zero external dependencies (uses standard urllib.request).
"""

import json
import ssl
import urllib.request
import urllib.error
import urllib.parse
from datetime import date
from typing import Dict, Any, Optional

def _get_ssl_context():
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

class Notifier:
    def __init__(
        self,
        topic: str,
        server_url: str = "https://ntfy.sh",
        vault_name: str = "obsidian-vault",
        timeout: int = 10
    ):
        self.topic = topic.strip()
        self.server_url = server_url.rstrip("/")
        self.vault_name = vault_name.strip()
        self.timeout = timeout
        self.ssl_ctx = _get_ssl_context()

    @property
    def endpoint(self) -> str:
        return f"{self.server_url}/{self.topic}"

    def build_obsidian_uri(self, target_date: date) -> str:
        """
        Builds a native Obsidian deep link for the specified daily note.
        Format: obsidian://open?vault=<VAULT>&file=Daily%2F<YYYY-MM-DD>
        """
        vault_encoded = urllib.parse.quote(self.vault_name)
        file_encoded = urllib.parse.quote(f"Daily/{target_date.strftime('%Y-%m-%d')}")
        return f"obsidian://open?vault={vault_encoded}&file={file_encoded}"

    def send_daily_note_notification(
        self,
        target_date: date,
        workout_data: Optional[Dict[str, Any]] = None,
        api_data: Optional[Dict[str, Any]] = None,
        prev_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Sends a rich completion notification to the phone with today's briefing preview
        and a 1-tap deep link that opens today's note in Obsidian.
        """
        if not self.topic:
            print("[Notifier] No ntfy topic configured. Skipping notification.")
            return False

        today_str = target_date.strftime("%Y-%m-%d")
        obsidian_uri = self.build_obsidian_uri(target_date)

        # Build concise preview snippets
        preview_parts = []

        # 1. Weather snippet
        if api_data and "weather" in api_data:
            w = api_data["weather"]
            high_low = w.get("temp_high_low", "")
            cond = w.get("condition", "")
            if high_low:
                preview_parts.append(f"⛅ {high_low}")
            elif cond:
                preview_parts.append(f"⛅ {cond}")

        # 2. Workout snippet
        if workout_data:
            if workout_data.get("skipped", False):
                preview_parts.append("🛋️ Rest Day")
            else:
                w_title = workout_data.get("title", "")
                if w_title:
                    preview_parts.append(f"🏋️ {w_title}")

        # 3. Rollover tasks count
        if prev_data and "incomplete_tasks" in prev_data:
            task_count = len(prev_data["incomplete_tasks"])
            if task_count > 0:
                preview_parts.append(f"🎯 {task_count} to-do{'s' if task_count > 1 else ''}")

        # 4. Priority email snippet
        if api_data and "gmail" in api_data:
            top_email = api_data["gmail"].get("top_email")
            if top_email:
                subj = top_email.get("subject", "")
                if len(subj) > 28:
                    subj = subj[:25] + "..."
                preview_parts.append(f"📬 {subj}")

        if preview_parts:
            message = " | ".join(preview_parts) + "\nTap to open your daily note."
        else:
            message = "Your daily briefing, workout, and schedule are ready. Tap to open in Obsidian."

        payload = {
            "topic": self.topic,
            "title": f"Daily Note Ready ☀️ ({today_str})",
            "message": message,
            "tags": ["spiral_calendar_pad", "sparkles"],
            "priority": 3,
            "click": obsidian_uri,
            "actions": [
                {
                    "action": "view",
                    "label": "Open in Obsidian",
                    "url": obsidian_uri,
                    "clear": True
                }
            ]
        }

        return self._post_ntfy_json(payload)

    def send_failure_alert(self, error_message: str, target_date: Optional[date] = None) -> bool:
        """
        Sends an alert notification if the generator encounters an unexpected error.
        """
        if not self.topic:
            return False

        date_str = target_date.strftime("%Y-%m-%d") if target_date else "Today"
        payload = {
            "topic": self.topic,
            "title": f"⚠️ Daily Note Failed ({date_str})",
            "message": f"The daily assistant encountered an error:\n{error_message[:250]}",
            "tags": ["warning", "rotating_light"],
            "priority": 4
        }

        return self._post_ntfy_json(payload)

    def send_test_notification(self) -> bool:
        """
        Sends a verification notification to confirm phone delivery and deep link handling.
        """
        if not self.topic:
            print("[Notifier] Error: NTFY_TOPIC is not set.")
            return False

        today = date.today()
        obsidian_uri = self.build_obsidian_uri(today)
        title = "Daily Assistant Test 🔔"
        message = f"Success! Tapping this notification opens today's note ({today.strftime('%Y-%m-%d')}) directly in Obsidian."

        payload = {
            "topic": self.topic,
            "title": title,
            "message": message,
            "tags": ["white_check_mark", "iphone"],
            "priority": 3,
            "click": obsidian_uri,
            "actions": [
                {
                    "action": "view",
                    "label": "Open in Obsidian",
                    "url": obsidian_uri,
                    "clear": True
                }
            ]
        }

        print(f"[Notifier] Sending test notification to {self.endpoint}...")
        print(f"[Notifier] Deep Link: {obsidian_uri}")
        return self._post_ntfy_json(payload)

    def _post_ntfy_json(self, payload: Dict[str, Any]) -> bool:
        """Internal helper to dispatch JSON HTTP request to ntfy server."""
        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.server_url,
                data=data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=self.timeout) as response:
                if 200 <= response.status < 300:
                    return True
                else:
                    print(f"[Notifier] Unexpected status from ntfy: {response.status}")
                    return False
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            print(f"[Notifier] HTTPError {e.code} ({e.reason}): {err_body}")
            return False
        except Exception as e:
            print(f"[Notifier] Network error sending notification: {e}")
            return False
