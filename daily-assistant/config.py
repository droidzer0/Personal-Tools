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

from typing import Dict, List, Optional

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

def get_daily_note_dir(target_date: date, vault_path: Optional[Path] = None) -> Path:
    """Returns the month directory for a given target date: Daily/YYYY/MonthName"""
    base = (vault_path or VAULT_PATH) / "Daily"
    return base / str(target_date.year) / target_date.strftime("%B")

def get_daily_note_path(target_date: date, vault_path: Optional[Path] = None) -> Path:
    """Returns the full Path to the daily note: Daily/YYYY/MonthName/YYYY-MM-DD.md"""
    return get_daily_note_dir(target_date, vault_path) / f"{target_date.strftime('%Y-%m-%d')}.md"

def get_daily_note_rel_path(target_date: date) -> str:
    """Returns the vault-relative path: Daily/YYYY/MonthName/YYYY-MM-DD.md"""
    return f"Daily/{target_date.year}/{target_date.strftime('%B')}/{target_date.strftime('%Y-%m-%d')}.md"

HEALTH_FILE = VAULT_PATH / "Life Dashboard" / "Health" / "Health & Fitness.md"
FINANCE_FILE = VAULT_PATH / "Life Dashboard" / "Finance" / "Finance Dashboard.md"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# DroidZero & Server Monitoring
DROIDZERO_URL = os.getenv("DROIDZERO_URL", "https://droidzero.duckdns.org")
UPTIME_KUMA_URL = os.getenv("UPTIME_KUMA_URL", "http://127.0.0.1:3001")
DROIDZERO_ENV_PATH = Path(os.getenv("DROIDZERO_ENV_PATH", "/opt/droidzero-api/.env"))
BACKUP_GITHUB_REPO = os.getenv("BACKUP_GITHUB_REPO", "droidzer0/droidzero-backups").strip()
BACKUP_TOKEN_EXPIRES_ON = os.getenv("BACKUP_TOKEN_EXPIRES_ON", "").strip()

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
    "Wash Face",
    "Take Cholesterol Medication",
]

# Weekday-Specific Recurring Tasks (Python date.weekday(): 0=Monday .. 6=Sunday)
WEEKLY_MANDATORY_TASKS: Dict[int, List[str]] = {
    2: [  # Wednesday
        "Take Vitamin D Medication",
    ],
}

def get_mandatory_tasks_for_date(target_date: date) -> List[str]:
    """Returns all mandatory daily and weekday-specific tasks for target_date."""
    tasks = list(MANDATORY_DAILY_TASKS)
    tasks.extend(WEEKLY_MANDATORY_TASKS.get(target_date.weekday(), []))
    return tasks

def get_all_recurring_tasks() -> List[str]:
    """Returns all configured daily and weekday-specific recurring tasks."""
    tasks = list(MANDATORY_DAILY_TASKS)
    for day_tasks in WEEKLY_MANDATORY_TASKS.values():
        for task in day_tasks:
            if task not in tasks:
                tasks.append(task)
    return tasks
