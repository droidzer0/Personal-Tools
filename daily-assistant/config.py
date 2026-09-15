import os
from datetime import date
from pathlib import Path
# Try loading dotenv if available; otherwise parse .env manually
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Base paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# Default Vault location: on macOS local vs OCI VM
DEFAULT_VAULT_LOCAL = REPO_ROOT / "obsidian-vault"
DEFAULT_VAULT_OCI = Path("/opt/obsidian-vault")

VAULT_PATH = Path(
    os.getenv(
        "OBSIDIAN_VAULT_PATH",
        str(DEFAULT_VAULT_LOCAL if DEFAULT_VAULT_LOCAL.exists() else DEFAULT_VAULT_OCI)
    )
)

DAILY_DIR = VAULT_PATH / "Daily"
HEALTH_FILE = VAULT_PATH / "Life Dashboard" / "Health" / "Health & Fitness.md"
FINANCE_FILE = VAULT_PATH / "Life Dashboard" / "Finance" / "Finance Dashboard.md"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# DroidZero & Server Monitoring
DROIDZERO_URL = os.getenv("DROIDZERO_URL", "https://droidzero.duckdns.org")
UPTIME_KUMA_URL = os.getenv("UPTIME_KUMA_URL", "http://127.0.0.1:3001")

# Google OAuth credentials paths (falls back across known locations)
POSSIBLE_CREDS = [
    SCRIPT_DIR / "credentials.json",
    VAULT_PATH / "Life Dashboard" / "Productivity" / "credentials.json",
    Path("/Users/user/Documents/antigravity/resilient-pasteur/credentials.json"),
]
GOOGLE_CREDENTIALS_PATH = next((p for p in POSSIBLE_CREDS if p.exists()), POSSIBLE_CREDS[0])
GMAIL_CREDENTIALS_PATH = GOOGLE_CREDENTIALS_PATH

POSSIBLE_TOKEN_DIRS = [
    SCRIPT_DIR,
    VAULT_PATH / "Life Dashboard" / "Productivity",
    Path("/Users/user/Documents/antigravity/resilient-pasteur"),
]
GOOGLE_TOKENS_DIR = next((d for d in POSSIBLE_TOKEN_DIRS if (d / "token_1.json").exists()), POSSIBLE_TOKEN_DIRS[0])
GMAIL_TOKENS_DIR = GOOGLE_TOKENS_DIR

# Google Calendar & Timezone Configuration
GOOGLE_CALENDAR_ENABLED = os.getenv("GOOGLE_CALENDAR_ENABLED", "true").lower() in ("true", "1", "yes")
CALENDAR_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "America/Chicago")

def _normalize_ics_url(url: str) -> str:
    url = url.strip()
    if url.startswith("webcal://"):
        return "https://" + url[9:]
    return url

CALENDAR_ICS_URLS = [_normalize_ics_url(u) for u in os.getenv("CALENDAR_ICS_URLS", "").split(",") if u.strip()]

# Financial Market Trackers
DEFAULT_TICKERS = ["VOO", "VTI", "VT", "QQQ", "IGV", "NOW", "BTC-USD", "ETH-USD"]
TRACKED_TICKERS = os.getenv("TRACKED_TICKERS", ",".join(DEFAULT_TICKERS)).split(",")

# Push Notifications (ntfy.sh)
NTFY_ENABLED = os.getenv("NTFY_ENABLED", "true").lower() in ("true", "1", "yes")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "")
NTFY_SERVER_URL = os.getenv("NTFY_SERVER_URL", "https://ntfy.sh").rstrip("/")
OBSIDIAN_VAULT_NAME = os.getenv("OBSIDIAN_VAULT_NAME", VAULT_PATH.name or "obsidian-vault")

# User Biometric Profile (27yo male, 5'10", starting from square 1, Chicago desk worker)
USER_PROFILE = {
    "age": 27,
    "gender": "male",
    "height_in": 70,  # 5'10"
    "current_weight_lbs": 191.0,
    "target_weight_lbs": 167.5,  # 165 - 170 lbs
    "location": "Chicago, IL",
    "occupation": "Tech Worker (Desk)",
    "cardio_preference": "Lap swimming",
    "status": "Square 1 On-Ramp (Post-illness rebuilding)"
}

# Fitness Program Progression & Tracking
PROGRAM_START_DATE = date.fromisoformat(os.getenv("PROGRAM_START_DATE", "2026-09-07"))

# Mandatory Daily Recurring Tasks (appended to every daily note's priorities)
MANDATORY_DAILY_TASKS = [
    "Brush Teeth & Floss",
    "Wash Face"
]
