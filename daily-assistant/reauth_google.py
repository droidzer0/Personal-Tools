#!/usr/bin/env python3
"""
Zero-dependency Google OAuth2 Re-Authenticator for Gmail and Google Calendar.
Works on any Python 3 installation without requiring ANY external pip packages.
"""

import os
import sys
import json
import time
import ssl
import datetime
import urllib.parse
import urllib.request
import urllib.error
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
VAULT_DEST = REPO_ROOT / "obsidian-vault" / "Life Dashboard" / "Productivity"
PASTEUR_DEST = Path("/Users/user/Documents/antigravity/resilient-pasteur")

# Find credentials.json across known paths
POSSIBLE_CREDS = [
    VAULT_DEST / "credentials.json",
    PASTEUR_DEST / "credentials.json",
    SCRIPT_DIR / "credentials.json",
]
CREDS_PATH = next((p for p in POSSIBLE_CREDS if p.exists()), POSSIBLE_CREDS[0])

PORT = 8088
REDIRECT_URI = f"http://localhost:{PORT}/"
AUTH_CODE = None

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly"
]
SCOPES_STRING = " ".join(SCOPES)

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

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global AUTH_CODE
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            AUTH_CODE = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """
            <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #2e7d32;">✅ Authentication Successful!</h1>
            <p>Your Google account has been authorized with Gmail & Calendar permissions.</p>
            <p>You can close this browser tab and return to the terminal.</p>
            </body></html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Failed to capture authorization code.")

    def log_message(self, format, *args):
        return

def authenticate_account(token_filename: str, account_label: str):
    global AUTH_CODE
    AUTH_CODE = None

    if not CREDS_PATH.exists():
        print(f"❌ Error: {CREDS_PATH} not found!")
        print("Please place credentials.json in this directory or in Obsidian Vault Productivity folder.")
        sys.exit(1)

    creds_data = json.loads(CREDS_PATH.read_text(encoding="utf-8"))
    client_info = creds_data.get("installed") or creds_data.get("web")
    if not client_info:
        print("❌ Error: Invalid credentials.json format.")
        sys.exit(1)

    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES_STRING,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    print(f"\n=======================================================")
    print(f"🔐 Authenticating: {account_label} ({token_filename})")
    print(f"Permissions: Gmail (Read-Only) + Google Calendar (Read-Only)")
    print(f"=======================================================")
    print(f"Opening browser for Google authorization...\n")

    try:
        server = HTTPServer(("localhost", PORT), OAuthCallbackHandler)
    except OSError as e:
        print(f"❌ Error opening port {PORT}: {e}")
        return False

    server.timeout = 120

    webbrowser.open(auth_url)
    print(f"If the browser doesn't open automatically, visit this URL:")
    print(f"{auth_url}\n")
    print("Waiting for sign-in in browser (timeout in 120s)...")

    while AUTH_CODE is None:
        server.handle_request()

    server.server_close()

    if not AUTH_CODE:
        print("❌ Authorization failed or timed out.")
        return False

    print("🔑 Authorization code received! Exchanging for tokens...")

    token_url = "https://oauth2.googleapis.com/token"
    token_params = urllib.parse.urlencode({
        "code": AUTH_CODE,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    req = urllib.request.Request(
        token_url,
        data=token_params,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=get_ssl_context()) as resp:
            token_res = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"❌ Failed to exchange token: {e}")
        return False

    access_token = token_res.get("access_token")
    refresh_token = token_res.get("refresh_token")
    expires_in = token_res.get("expires_in", 3600)

    expiry_dt = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    expiry_iso = expiry_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    token_payload = {
        "token": access_token,
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": SCOPES,
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": expiry_iso
    }

    # Save to known destinations
    saved_paths = []
    for dest_dir in [SCRIPT_DIR, VAULT_DEST, PASTEUR_DEST]:
        if dest_dir.exists():
            target_path = dest_dir / token_filename
            target_path.write_text(json.dumps(token_payload, indent=2), encoding="utf-8")
            saved_paths.append(str(target_path))
            print(f"✅ Saved token to: {target_path}")

    return True

def main():
    print("🚀 Google OAuth Re-Authentication Tool (Gmail + Google Calendar)")
    print("This will refresh tokens for your 2 Google accounts with Calendar & Gmail scopes.\n")
    print("Prerequisites:")
    print("1. Ensure 'Google Calendar API' is enabled in your Google Cloud Console project.")
    print("2. Ensure test users include both of your Gmail addresses.\n")

    success_1 = authenticate_account("token_1.json", "Personal Account A")
    if not success_1:
        print("Stopping due to error on Account 1.")
        return

    print("\nAccount A complete!")
    try:
        ans = input("\nWould you like to authenticate Account B (token_2.json) now? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "y"

    if ans in ("", "y", "yes"):
        authenticate_account("token_2.json", "Personal Account B")

    print("\n🎉 All set! Your Google tokens now have Gmail and Calendar read access active.")

if __name__ == "__main__":
    main()
