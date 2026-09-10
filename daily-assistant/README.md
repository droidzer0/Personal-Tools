# Daily Assistant & Life Dashboard Orchestrator

Stateless, autonomous batch engine that runs daily to:
1. **Rollover Tasks**: Parse previous day's Obsidian note (unfinished tasks, completed items, scratchpad notes) with calendar-rollover exclusion.
2. **Google Calendar Integration**: Fetch scheduled events and all-day items from connected Google accounts (Account A & Account B) and format them into interactive checkboxes (`- [ ]`) under `## 🎯 To-do -> ### 📅 Today's Schedule`.
3. **Workout Routine Engine**: Generate today's personalized workout routine (tracking biometrics, 191 lbs -> 165 lbs goal, PBs, lap swimming, desk-worker mobility).
4. **Systems Pulse**: Gather real-time system metrics (DroidZero website health, OCI instance metrics).
5. **Gmail Triage**: Triage Gmail inboxes (unread count, urgent senders).
6. **Financial Markets**: Fetch financial market indexes (VOO, QQQ, BTC, ETH) with daily delta indicators.
7. **Chicago Weather**: Real-time precipitation forecasting and conditions.
8. **Gemini AI Synthesis**: Use Google Gemini API (`gemini-3.5-flash`) to synthesize into a clean Markdown note.
9. **Vault Delivery**: Write today's note directly into the Obsidian Vault (`Daily/YYYY-MM-DD.md`) for instant sync to iPhone.

---

## 🔑 Google Calendar & Gmail Authentication

To connect your Google Calendars:
1. In [Google Cloud Console](https://console.cloud.google.com/) under `Personal Life Dashboard`:
   - Go to **APIs & Services** -> **Enabled APIs & Services**.
   - Click **+ Enable APIs and Services**, search for **Google Calendar API**, and click **Enable**.
2. Run the zero-dependency re-authenticator tool:
   ```bash
   python3 reauth_google.py
   ```
3. A browser window will open requesting read permissions for Gmail and Google Calendar.
   - Authorize Account A (`token_1.json`).
   - Authorize Account B (`token_2.json`).
4. Re-run `python3 daily_orchestrator.py --dry-run` to preview today's events!
