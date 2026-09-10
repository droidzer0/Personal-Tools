# 🚀 OCI 24/7 Setup Guide: Running Daily Assistant Without Your Laptop

This guide explains how to set up the Daily Assistant on your Oracle Cloud Infrastructure VM (`instance-20260619-1207`) so that every morning at 5:00 AM Central, today's note is generated and pushed to CouchDB—ready on your iPhone before you wake up.

---

## Architecture Recap
1. Your CouchDB container runs on `127.0.0.1:5984` on the OCI VM.
2. `livesync-cli` mirrors the CouchDB database to a local directory `/opt/obsidian-vault`.
3. `daily_orchestrator.py` runs via cron at 5:00 AM Central (`10:00 UTC`):
   - Pulls edits made on phone/laptop yesterday.
   - Gathers live stats (DroidZero, OCI load, Gmail triage, Markets, Weather).
   - Calls Gemini with the customized 27yo tech worker workout plan.
   - Writes `Daily/YYYY-MM-DD.md`.
   - Pushes directly back to CouchDB.
4. You open Obsidian on your phone, and it syncs in 1–2 seconds.

---

## Step 1: Copy `daily-assistant` to the OCI Server

From your local Mac terminal:
```bash
# Using your Tailscale IP or SSH host
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  /Users/user/Desktop/Coding/Personal-Tools/daily-assistant/ \
  ubuntu@<TSIP>:/opt/droidzero-stack/daily-assistant/
```

---

## Step 2: Install Python Virtual Environment on OCI

SSH into your server:
```bash
ssh ubuntu@<TSIP>
cd /opt/droidzero-stack/daily-assistant
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Create your `.env` file:
```bash
cp deploy/sample.env .env
nano .env
```
Paste your **`GEMINI_API_KEY`** and set `OBSIDIAN_VAULT_PATH="/opt/obsidian-vault"`.

---

## Step 3: Setup `livesync-cli` on OCI

The author of Obsidian LiveSync (`vrtmrz`) provides `livesync-cli`:
```bash
# Install nodejs & npm if needed
sudo apt-get install -y nodejs npm

# Install or clone livesync-cli
git clone https://github.com/vrtmrz/obsidian-livesync.git /tmp/obsidian-livesync
cd /tmp/obsidian-livesync/src/apps/cli
npm install
npm run build
sudo npm link
```

### Initial Connection Setup
1. In your desktop Obsidian: **Settings** → **Self-hosted LiveSync** → **Copy Setup URI**.
2. Run on OCI:
```bash
mkdir -p /opt/obsidian-vault
livesync-cli setup --vault /opt/obsidian-vault "<YOUR_SETUP_URI>"
```
3. Test bidirectional sync:
```bash
livesync-cli sync
```
Your vault notes will now be mirrored in `/opt/obsidian-vault`.

---

## Step 4: Configure Crontab

On your OCI server, open crontab:
```bash
crontab -e
```

Add the following line to run every morning at 5:00 AM Chicago time (10:00 UTC):
```bash
# Run Daily Assistant every morning at 5:00 AM Central (10:00 UTC)
0 10 * * * /bin/bash /opt/droidzero-stack/daily-assistant/deploy/run_daily.sh
```

---

## Step 5: Test Execution
To test immediately:
```bash
/bin/bash /opt/droidzero-stack/daily-assistant/deploy/run_daily.sh
```
Check the output log:
```bash
cat /opt/droidzero-stack/daily-assistant/logs/daily_*.log
```
Then open your iPhone Obsidian app to confirm the note appears!
