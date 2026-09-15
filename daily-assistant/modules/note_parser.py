import re
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class NoteParser:
    def __init__(self, daily_dir: Path):
        self.daily_dir = daily_dir

    def find_previous_note(self, target_date: date) -> Optional[Tuple[date, Path]]:
        """Find the note from yesterday, or the most recent preceding note within the last 14 days."""
        if not self.daily_dir.exists():
            return None

        # Check yesterday first
        yesterday = target_date - timedelta(days=1)
        yesterday_file = self.daily_dir / f"{yesterday.strftime('%Y-%m-%d')}.md"
        if yesterday_file.exists():
            return yesterday, yesterday_file

        # Fallback: scan backwards up to 14 days
        for i in range(2, 15):
            past_date = target_date - timedelta(days=i)
            candidate = self.daily_dir / f"{past_date.strftime('%Y-%m-%d')}.md"
            if candidate.exists():
                return past_date, candidate

        return None

    @staticmethod
    def detect_workout_skip(scratchpad_notes: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Scans scratchpad notes to detect if the user wrote they intend to skip a workout day or rest.
        Guards against negations (e.g. "don't skip workout").
        Returns (should_skip, matching_note).
        """
        skip_patterns = [
            r"\b(?:skip|skipping|pass\s+on|opt\s+out\s+of)\s+(?:(?:a|the|my|tomorrow(?:'s)?)\s+)*(?:workout(?:\s+day)?|gym|lifting|exercise|training|swim(?:ming)?)\b",
            r"\b(?:going\s+to|gonna|plan\s+to|planning\s+to|want\s+to)\s+skip\s+(?:(?:a|the|my|tomorrow(?:'s)?)\s+)*(?:workout(?:\s+day)?|gym|lifting|exercise|training)\b",
            r"\b(?:take|taking|have|need)\s+(?:a\s+)?(?:rest|recovery)\s+day\s+(?:tomorrow|next\s+day)\b",
            r"\b(?:rest|recovery)\s+day\s+tomorrow\b",
            r"\bno\s+workout\s+(?:tomorrow|next\s+day)\b",
            r"\bday\s+off\s+from\s+(?:the\s+)?(?:workout|gym|lifting|exercise)\b",
            r"\bskip\s+tomorrow'?s?\s+(?:session|routine|lifting|swim|run|workout)\b",
            r"\bskip\s+a\s+workout\s+day\b",
        ]

        negation_pattern = r"\b(?:don't|do\s+not|never|won't|cannot|can't|shouldn't|not)\s+(?:skip|skipping)\b"

        for note in scratchpad_notes:
            lower = note.lower().strip()
            # Check for negation first
            if re.search(negation_pattern, lower):
                continue

            for pat in skip_patterns:
                if re.search(pat, lower):
                    return True, note

        return False, None

    def parse_note_content(self, file_path: Path) -> Dict[str, Any]:
        """
        Parses a daily note to extract:
        - Incomplete tasks (- [ ])
        - Completed tasks count (- [x])
        - Scratchpad / freeform notes
        - Logged workout logs and structured actuals
        - Workout skip intent
        """
        if not file_path.exists():
            return {
                "incomplete_tasks": [],
                "completed_count": 0,
                "scratchpad_notes": [],
                "workout_logs": [],
                "workout_actuals": [],
                "skip_workout": False,
                "skip_workout_reason": None,
                "raw_text": ""
            }

        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()

        incomplete_tasks = []
        completed_count = 0
        scratchpad_notes = []
        workout_logs = []
        workout_actuals = []

        in_scratchpad = False
        in_workout = False
        in_calendar = False

        current_exercise: Optional[str] = None
        current_exercise_completed = False

        for line in lines:
            trimmed = line.strip()

            # Track section headers (## or ###)
            if trimmed.startswith("## ") or trimmed.startswith("### "):
                lower_header = trimmed.lower()
                in_scratchpad = ("scratchpad" in lower_header or "notes" in lower_header or "tomorrow" in lower_header)
                in_workout = ("workout" in lower_header or "exercise" in lower_header)
                in_calendar = ("schedule" in lower_header or "calendar" in lower_header or "meeting" in lower_header or "events" in lower_header)
                current_exercise = None
                current_exercise_completed = False

            # Checkboxes
            if trimmed.startswith("- [ ]"):
                task_text = trimmed[5:].strip()
                # Skip workout checklist items and scheduled calendar events from rolling over
                is_calendar_event = (
                    in_calendar or
                    "⏰" in task_text or
                    "🗓️" in task_text or
                    "all day" in task_text.lower() or
                    bool(re.search(r'\b\d{1,2}:\d{2}\s*(?:am|pm)\b', task_text, re.IGNORECASE))
                )
                recurring_hygiene = any(h in task_text.lower() for h in ["brush teeth", "wash face", "floss"])
                if not in_workout and not is_calendar_event and not recurring_hygiene:
                    incomplete_tasks.append(task_text)
                elif in_workout:
                    current_exercise = self._extract_exercise_name(task_text)
                    current_exercise_completed = False

            elif trimmed.startswith("- [x]") or trimmed.startswith("- [X]"):
                completed_count += 1
                if in_workout:
                    workout_logs.append(trimmed)
                    task_text = trimmed[5:].strip()
                    current_exercise = self._extract_exercise_name(task_text)
                    current_exercise_completed = True

            # Scratchpad bullets or lines
            elif in_scratchpad and trimmed and not trimmed.startswith("#") and not trimmed.startswith("---"):
                lower_line = trimmed.lower()
                is_placeholder = (
                    "capture thoughts" in lower_line or
                    "use this space" in lower_line or
                    lower_line in ("-", "*", "- [ ]", "*(none)*", "none")
                )
                if not is_placeholder:
                    clean_text = re.sub(r'^[-*]\s*(\[\s*\]\s*)?', '', trimmed).strip()
                    if clean_text:
                        scratchpad_notes.append(clean_text)

            # Parse explicit actual weights logged
            if in_workout:
                actual_match = re.search(r'(?:actual|logged):\s*(.+)', trimmed, re.IGNORECASE)
                if actual_match:
                    workout_logs.append(trimmed)
                    raw_val = actual_match.group(1).strip().strip("`").strip()
                    # Only accept if not an unfilled template placeholder
                    if raw_val and "___" not in raw_val and raw_val not in ("--", "—"):
                        ex_name = current_exercise or "General Exercise"
                        workout_actuals.append({
                            "exercise": ex_name,
                            "actual": raw_val,
                            "completed": current_exercise_completed,
                            "raw_line": trimmed
                        })

        # Detect workout skip intent from scratchpad
        skip_workout, skip_reason = self.detect_workout_skip(scratchpad_notes)
        if skip_workout:
            # Filter out the skip note from scratchpad_notes so it doesn't rollover into an actionable to-do
            scratchpad_notes = [n for n in scratchpad_notes if n != skip_reason]

        return {
            "incomplete_tasks": incomplete_tasks,
            "completed_count": completed_count,
            "scratchpad_notes": scratchpad_notes,
            "workout_logs": workout_logs,
            "workout_actuals": workout_actuals,
            "skip_workout": skip_workout,
            "skip_workout_reason": skip_reason,
            "raw_text": text
        }

    @staticmethod
    def _extract_exercise_name(text: str) -> str:
        """Extracts clean exercise name from markdown checkbox text."""
        # Check for [**Name**](url) or **[Name](url)** or [Name](url)
        match_link = re.search(r'\[(?:\*\*)?([^\]]+?)(?:\*\*)?\]\(.*?\)', text)
        if match_link:
            name = match_link.group(1).strip()
            return re.sub(r'\s*↗$', '', name).strip()

        # Check for **Name**
        match_bold = re.search(r'\*\*([^*]+?)\*\*', text)
        if match_bold:
            return match_bold.group(1).strip()

        # Split on dash or colon if present
        parts = re.split(r'[-—:]', text, maxsplit=1)
        return parts[0].strip()

    # --- Health & Fitness Dashboard Updates ---

    CANONICAL_EXERCISES = {
        "Barbell Squat": {
            "aliases": ["barbell squat", "back squat", "squat", "goblet squat (or barbell squat)", "goblet squat", "barbell back squat", "barbell front squat"],
            "exclusions": ["split squat", "leg press"]
        },
        "Bench Press": {
            "aliases": ["bench press", "dumbbell bench press", "barbell bench press", "incline dumbbell press", "incline bench press", "flat bench press", "dumbbell press"],
            "exclusions": []
        },
        "Barbell Deadlift": {
            "aliases": ["barbell deadlift", "deadlift", "conventional deadlift", "sumo deadlift", "romanian deadlift", "dumbbell romanian deadlift (rdl)", "rdl"],
            "exclusions": []
        },
        "Cable / Dumbbell Row": {
            "aliases": ["cable / dumbbell row", "cable row", "dumbbell row", "chest-supported dumbbell / cable row", "seated cable row", "chest supported row", "seated row", "row"],
            "exclusions": []
        },
        "Dumbbell Overhead Press": {
            "aliases": ["dumbbell overhead press", "standing or seated dumbbell overhead press", "overhead press", "seated dumbbell overhead press", "standing dumbbell overhead press", "shoulder press", "dumbbell shoulder press", "ohp"],
            "exclusions": []
        },
        "Neutral Grip Pull-Up": {
            "aliases": ["neutral grip pull-up", "neutral grip pull up", "pull-up", "pull up", "pull-ups", "pullups", "neutral grip lat pulldown or assisted pull-ups", "assisted pull-up", "assisted pull-ups", "lat pulldown"],
            "exclusions": []
        },
        "Lap Swim (Continuous)": {
            "aliases": ["lap swim", "lap swim (continuous)", "continuous swim", "lap swimming", "freestyle laps", "freestyle intervals", "warmup freestyle laps", "main set: freestyle intervals", "swimming"],
            "exclusions": []
        }
    }

    @classmethod
    def match_canonical_exercise(cls, logged_name: str, table_exercises: List[str]) -> Optional[str]:
        """Matches a logged exercise name to one of the exercises in the Health & Fitness table."""
        clean_logged = logged_name.lower().strip()

        # 1. Check direct match against table exercises (cleaned)
        for tbl_ex in table_exercises:
            clean_tbl = tbl_ex.strip().strip("*").strip().lower()
            if clean_tbl == clean_logged:
                return tbl_ex

        # 2. Check canonical definitions
        for canon_name, data in cls.CANONICAL_EXERCISES.items():
            # Check exclusions
            if any(exc in clean_logged for exc in data["exclusions"]):
                continue

            for alias in data["aliases"]:
                if alias == clean_logged or alias in clean_logged:
                    # Find which table exercise corresponds to canon_name
                    for tbl_ex in table_exercises:
                        clean_tbl = tbl_ex.strip().strip("*").strip()
                        if canon_name.lower() in clean_tbl.lower() or clean_tbl.lower() in canon_name.lower():
                            return tbl_ex

        # 3. Fallback: fuzzy substring match
        for tbl_ex in table_exercises:
            clean_tbl = tbl_ex.strip().strip("*").strip().lower()
            if clean_tbl and (clean_tbl in clean_logged or clean_logged in clean_tbl):
                return tbl_ex

        return None

    @staticmethod
    def parse_performance(raw: str) -> Dict[str, Any]:
        """
        Parses a logged performance string into a structured dict with score for PB comparison.
        Supported formats:
        - '135 lbs x 10' / '25 lbs x 10 reps' / '140 lbs x 8'
        - 'Assisted (-50 lbs)'
        - '8 bodyweight' / '10 bodyweight reps'
        - '200m freestyle' / '500m freestyle'
        """
        clean = raw.strip().strip("`").strip()

        # Check assisted pull-ups e.g. Assisted (-50 lbs)
        m_assisted = re.search(r'assisted\s*\(\s*-?(\d+(?:\.\d+)?)\s*(?:lbs|kg)?\s*\)', clean, re.IGNORECASE)
        if m_assisted:
            asst_weight = float(m_assisted.group(1))
            return {
                "type": "assisted",
                "assistance_lbs": asst_weight,
                "score": -asst_weight,
                "display": f"Assisted (-{int(asst_weight) if asst_weight.is_integer() else asst_weight} lbs)"
            }

        # Check bodyweight reps e.g. 8 bodyweight, 10 bodyweight reps
        m_bw = re.search(r'(\d+)\s*(?:reps?\s+)?bodyweight|bodyweight\s*(?:x\s*)?(\d+)', clean, re.IGNORECASE)
        if m_bw:
            reps = int(m_bw.group(1) or m_bw.group(2))
            return {
                "type": "bodyweight",
                "reps": reps,
                "score": 1000 + reps,
                "display": f"{reps} bodyweight"
            }

        # Check swimming distance e.g. 200m freestyle, 500m
        m_swim = re.search(r'(\d+)\s*m(?:eters?)?\s*([a-zA-Z\s]+)?', clean, re.IGNORECASE)
        if m_swim:
            dist = int(m_swim.group(1))
            stroke = (m_swim.group(2) or "freestyle").strip()
            return {
                "type": "distance",
                "distance": dist,
                "stroke": stroke,
                "score": dist,
                "display": f"{dist}m {stroke}" if stroke else f"{dist}m"
            }

        # Check weight x reps e.g. 135 lbs x 10, 25 lbs x 10 reps, 35 x 10
        sets_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:lbs|kg)?\s*(?:each)?\s*x\s*(\d+)', clean, re.IGNORECASE)
        if sets_matches:
            best_e1rm = 0.0
            best_weight = 0.0
            best_reps = 0
            for w_str, r_str in sets_matches:
                w = float(w_str)
                r = int(r_str)
                e1rm = w * (1.0 + r / 30.0)
                if e1rm > best_e1rm:
                    best_e1rm = e1rm
                    best_weight = w
                    best_reps = r

            w_display = int(best_weight) if best_weight.is_integer() else best_weight
            return {
                "type": "weight_reps",
                "weight": best_weight,
                "reps": best_reps,
                "e1rm": round(best_e1rm, 1),
                "score": round(best_e1rm, 1),
                "display": f"{w_display} lbs x {best_reps}"
            }

        # Fallback raw
        return {
            "type": "raw",
            "score": 0.0,
            "display": clean
        }

    @classmethod
    def evaluate_new_pb(cls, new_perf: Dict[str, Any], old_pb_str: str) -> Tuple[bool, str]:
        """
        Compares new performance against current PB string.
        Returns (is_new_pb, updated_pb_display).
        """
        old_clean = old_pb_str.strip().strip("*").strip()
        # If no previous PB recorded
        if not old_clean or old_clean in ("--", "—", "-"):
            return True, new_perf["display"]

        old_perf = cls.parse_performance(old_clean)

        # Same type comparison
        if new_perf["type"] == "weight_reps" and old_perf["type"] == "weight_reps":
            if new_perf["weight"] > old_perf["weight"] and new_perf["reps"] >= old_perf["reps"]:
                return True, new_perf["display"]
            elif new_perf["weight"] == old_perf["weight"] and new_perf["reps"] > old_perf["reps"]:
                return True, new_perf["display"]
            elif new_perf["e1rm"] > old_perf["e1rm"] + 1.0:
                return True, new_perf["display"]
            return False, old_clean

        elif new_perf["type"] == "distance" and old_perf["type"] == "distance":
            if new_perf["distance"] > old_perf["distance"]:
                return True, new_perf["display"]
            return False, old_clean

        elif new_perf["type"] in ("bodyweight", "assisted") and old_perf["type"] in ("bodyweight", "assisted"):
            if new_perf["score"] > old_perf["score"]:
                return True, new_perf["display"]
            return False, old_clean

        return False, old_clean

    def update_pbs_in_health_file(
        self,
        health_file_path: Path,
        note_date: date,
        workout_actuals: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> List[str]:
        """
        Parses logged actuals and updates the Personal Bests & Working Lifts table
        in Health & Fitness.md.
        Updates Current Working Weight to the latest logged value, and updates Personal Best (PB)
        and Date Achieved if a milestone is beaten.
        Returns a list of announcements/logs.
        """
        if not health_file_path.exists() or not workout_actuals:
            return []

        content = health_file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Find the Personal Bests & Working Lifts table
        table_start_idx = -1
        table_header_idx = -1
        for i, line in enumerate(lines):
            if "## 🏋️ Personal Bests & Working Lifts" in line:
                table_start_idx = i
                break

        if table_start_idx == -1:
            return []

        # Find header line starting with '|'
        for i in range(table_start_idx, len(lines)):
            if lines[i].strip().startswith("|") and "Exercise" in lines[i]:
                table_header_idx = i
                break

        if table_header_idx == -1:
            return []

        announcements = []
        date_str = note_date.strftime("%Y-%m-%d")

        row_indices = []
        table_exercises = []
        for i in range(table_header_idx + 2, len(lines)):
            line = lines[i].strip()
            if not line.startswith("|"):
                break
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                row_indices.append(i)
                table_exercises.append(parts[1])

        modified = False
        new_lines = list(lines)

        for act in workout_actuals:
            logged_name = act["exercise"]
            raw_actual = act["actual"]
            perf = self.parse_performance(raw_actual)

            matched_tbl_ex = self.match_canonical_exercise(logged_name, table_exercises)
            if not matched_tbl_ex:
                continue

            for row_idx in row_indices:
                parts = [p.strip() for p in new_lines[row_idx].split("|")]
                if len(parts) < 6:
                    continue

                if parts[1] == matched_tbl_ex:
                    clean_name = parts[1].strip().strip("*").strip()
                    old_working = parts[2]
                    old_pb = parts[3]
                    target_goal = parts[4]
                    old_date = parts[5]

                    # If this is a pull-up exercise and current baseline is Assisted (-X lbs):
                    if ("pull-up" in clean_name.lower() or "pull up" in clean_name.lower()) and "assisted" in old_working.lower() and perf["type"] == "weight_reps":
                        perf["type"] = "assisted"
                        perf["assistance_lbs"] = perf["weight"]
                        perf["score"] = -perf["weight"]
                        perf["display"] = f"Assisted (-{int(perf['weight'])} lbs)"

                    new_working_display = perf["display"]
                    is_pb, pb_display = self.evaluate_new_pb(perf, old_pb)

                    new_date = date_str if is_pb else old_date
                    new_pb_display = pb_display

                    if new_working_display != old_working or is_pb:
                        modified = True
                        parts[2] = new_working_display
                        parts[3] = new_pb_display
                        parts[5] = new_date

                        ex_col = parts[1]
                        inner = ex_col.replace("**", "").strip()
                        ex_col = f"**{inner}**"

                        new_lines[row_idx] = f"| {ex_col:<27} | {parts[2]:<21} | {parts[3]:<18} | {target_goal:<18} | {parts[5]:<13} |"

                        if is_pb:
                            announcements.append(f"🏆 NEW PERSONAL BEST: {clean_name} -> {new_pb_display} (Previous: {old_pb or 'None'})")
                        else:
                            announcements.append(f"Updated {clean_name} working weight -> {new_working_display}")

                    break

        if modified and not dry_run:
            health_file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        return announcements

    def load_working_weights(self, health_file_path: Path) -> Dict[str, Dict[str, str]]:
        """
        Parses the Personal Bests & Working Lifts table from Health & Fitness.md.
        Returns a dict mapping exercise name to its current working weight, PB, and target goal.
        """
        if not health_file_path.exists():
            return {}

        content = health_file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        table_start_idx = -1
        table_header_idx = -1
        for i, line in enumerate(lines):
            if "Personal Bests & Working Lifts" in line:
                table_start_idx = i
                break

        if table_start_idx == -1:
            return {}

        for i in range(table_start_idx, len(lines)):
            if lines[i].strip().startswith("|") and "Exercise" in lines[i]:
                table_header_idx = i
                break

        if table_header_idx == -1:
            return {}

        weights = {}
        for i in range(table_header_idx + 2, len(lines)):
            line = lines[i].strip()
            if not line.startswith("|"):
                break
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 6:
                clean_name = parts[1].strip().strip("*").strip()
                working = parts[2].strip()
                pb = parts[3].strip()
                target_goal = parts[4].strip()
                date_achieved = parts[5].strip()
                weights[clean_name] = {
                    "working": working,
                    "pb": pb,
                    "goal": target_goal,
                    "date": date_achieved
                }

        return weights
