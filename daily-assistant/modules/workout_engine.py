from datetime import date
import re
from typing import Dict, List, Optional, Any

class WorkoutEngine:
    def __init__(self, profile: Dict[str, Any]):
        self.profile = profile

    def calculate_bmi(self, weight_lbs: float, height_in: float) -> float:
        """Calculates Body Mass Index (BMI)."""
        if height_in <= 0:
            return 0.0
        return round((weight_lbs * 703) / (height_in ** 2), 1)

    def _calibrate_target(
        self,
        exercise_name: str,
        default_target: str,
        latest_actuals: Optional[Dict[str, Any]] = None,
        working_weights: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Calibrates an exercise target using concrete numbers or ranges informed by
        previous session actuals or working weights from the Health Ledger.
        Guarantees that subjective terms ('moderate', 'light') are never present.
        """
        latest_actuals = latest_actuals or {}
        working_weights = working_weights or {}

        # 1. Match logged performance from recent daily notes
        clean_name = exercise_name.lower().strip()
        matched_act = None

        # Direct key match or substring match
        for key, act_data in latest_actuals.items():
            k_clean = key.lower().strip()
            if k_clean == clean_name or k_clean in clean_name or clean_name in k_clean:
                matched_act = act_data
                break

        # Check if matched exercise was a light dumbbell/goblet variation mapped to a heavy barbell compound
        is_barbell_compound = ("barbell" in clean_name or "squat rack" in clean_name)
        if is_barbell_compound and matched_act:
            matched_name_lower = matched_act.get("exercise", "").lower()
            if any(db in matched_name_lower for db in ["dumbbell", "goblet", "db", "rdl"]) and matched_act.get("weight", 0) < 65:
                matched_act = None

        # 2. Check if we have a concrete weight from recent actuals
        if matched_act and matched_act.get("weight") and matched_act["weight"] > 0:
            w = matched_act["weight"]
            is_each = "each" in default_target.lower()
            is_per_side = "per side" in default_target.lower()

            # Progressive overload range: baseline up to +5 lbs (or +10 lbs for heavy compound)
            if w >= 100:
                high_w = w + 10.0
            else:
                high_w = w + 5.0

            w_low = int(w) if w.is_integer() else w
            w_high = int(high_w) if high_w.is_integer() else high_w

            # Extract sets and reps from default_target (e.g. "3 sets x 10 reps", "4 sets x 15 reps")
            sr_match = re.search(r'(\d+\s*sets?\s*x\s*[\d–-]+\s*reps?(?:\s*per\s*side)?)', default_target, re.IGNORECASE)
            if sr_match:
                prefix = sr_match.group(1)
                suffix = " each" if is_each else ""
                return f"{prefix} @ {w_low}–{w_high} lbs{suffix}"
            elif "each" in default_target.lower():
                return f"3 sets x 10 reps @ {w_low}–{w_high} lbs each"
            else:
                return f"3 sets x 10 reps @ {w_low}–{w_high} lbs"

        # 3. Check working weights from Health Ledger
        for ex_key, ww_data in working_weights.items():
            if ex_key.lower() in clean_name or clean_name in ex_key.lower():
                w_str = ww_data.get("working", "")
                m = re.search(r'(\d+(?:\.\d+)?)\s*lbs', w_str, re.IGNORECASE)
                if m:
                    w = float(m.group(1))
                    if is_barbell_compound and w < 45:
                        pb_str = ww_data.get("pb", "")
                        pb_m = re.search(r'(\d+(?:\.\d+)?)\s*lbs', pb_str, re.IGNORECASE)
                        if pb_m and float(pb_m.group(1)) >= 100:
                            w = 95.0
                        else:
                            w = 65.0
                    high_w = w + 10.0 if w >= 100 else w + 5.0
                    w_low = int(w) if w.is_integer() else w
                    w_high = int(high_w) if high_w.is_integer() else high_w
                    is_each = "each" in default_target.lower()
                    suffix = " each" if is_each else ""
                    sr_match = re.search(r'(\d+\s*sets?\s*x\s*[\d–-]+\s*reps?)', default_target, re.IGNORECASE)
                    prefix = sr_match.group(1) if sr_match else "3 sets x 10 reps"
                    return f"{prefix} @ {w_low}–{w_high} lbs{suffix}"

        # 4. Fallback: sanitize default_target to ensure NO 'moderate' or 'light'
        clean_target = default_target
        clean_target = re.sub(r'@\s*moderate\s*(?:load|weight)?', '@ 75–85 lbs', clean_target, flags=re.IGNORECASE)
        clean_target = re.sub(r'@\s*light\s*(?:load|weight)?', '@ 30–35 lbs', clean_target, flags=re.IGNORECASE)
        clean_target = re.sub(r'\bmoderate\s+pace\b', 'steady 50–60s pace', clean_target, flags=re.IGNORECASE)
        return clean_target

    def get_today_routine(
        self,
        target_date: date,
        timeline: Optional[Dict[str, int]] = None,
        working_weights: Optional[Dict[str, Any]] = None,
        workout_history: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Determines the optimal routine based on day of week, Square 1 On-Ramp protocol,
        week rotation track (Track A vs Track B), and previous completed workout history.
        Weekday indices: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        """
        weekday = target_date.weekday()
        current_bmi = self.calculate_bmi(
            self.profile["current_weight_lbs"],
            self.profile["height_in"]
        )

        # Multi-track routines for weekly variety and anti-duplication
        # Track A is active on odd weeks; Track B on even weeks (with auto-rotation if last week ran the same track)
        routines_catalog = {
            0: {
                "track_a": {
                    "title": "Full Body Strength A1 (Squat Rack & Horizontal Focus)",
                    "category": "Strength",
                    "goal": "Neuromuscular activation, controlled 2-second eccentrics, 90s rest.",
                    "exercises": [
                        {
                            "name": "Squat Rack Barbell Squat",
                            "target": "3 sets x 8-10 reps @ 95–135 lbs",
                            "cue": "Set pins at mid-chest, brace core 360°, drive knees out, hit parallel depth.",
                            "url": "https://musclewiki.com/exercise/barbell-squat"
                        },
                        {
                            "name": "Dumbbell Bench Press",
                            "target": "3 sets x 10 reps @ 35–40 lbs each",
                            "cue": "Retract scapula into bench, protect shoulders, control descent.",
                            "url": "https://musclewiki.com/exercise/dumbbell-bench-press"
                        },
                        {
                            "name": "Chest-Supported Dumbbell / Cable Row",
                            "target": "3 sets x 12 reps @ 70–80 lbs",
                            "cue": "Drive elbows back, squeeze upper back to reverse desk slouch.",
                            "url": "https://musclewiki.com/exercise/cable-seated-row"
                        },
                        {
                            "name": "Dumbbell Romanian Deadlift (RDL)",
                            "target": "3 sets x 10 reps @ 35–40 lbs each",
                            "cue": "Hinge at the hips, feel hamstring stretch, protect lower back.",
                            "url": "https://musclewiki.com/exercise/dumbbell-romanian-deadlift"
                        },
                        {
                            "name": "Deadbug (Core & Pelvic Stabilization)",
                            "target": "3 sets x 8 reps per side",
                            "cue": "Lower back stays glued to the floor throughout movement.",
                            "url": "https://musclewiki.com/exercise/dead-bug"
                        }
                    ],
                    "desk_mobility": "2 min standing hip flexor stretch + doorway pec stretch."
                },
                "track_b": {
                    "title": "Full Body Strength A2 (Goblet Squat & Deadlift Focus)",
                    "category": "Strength",
                    "goal": "Posterior chain hypertrophy, explosive hip drive, posture reinforcement.",
                    "exercises": [
                        {
                            "name": "Goblet Squat (or Front Squat)",
                            "target": "3 sets x 10 reps @ 35–45 lbs",
                            "cue": "Knees track over toes, pause at depth to open tight hips.",
                            "url": "https://musclewiki.com/exercise/dumbbell-goblet-squat"
                        },
                        {
                            "name": "Incline Dumbbell Bench Press",
                            "target": "3 sets x 10 reps @ 35–40 lbs each",
                            "cue": "Focus on clavicular upper-chest contraction, controlled negative.",
                            "url": "https://musclewiki.com/exercise/incline-dumbbell-bench-press"
                        },
                        {
                            "name": "Seated Cable Row",
                            "target": "3 sets x 12 reps @ 70–80 lbs",
                            "cue": "Drive elbows straight back into back pockets, engage lats.",
                            "url": "https://musclewiki.com/exercise/cable-seated-row"
                        },
                        {
                            "name": "Barbell Deadlift",
                            "target": "3 sets x 6-8 reps @ 135–185 lbs",
                            "cue": "Bar stays against shins, wedge hips into bar, push floor away through heels.",
                            "url": "https://musclewiki.com/exercise/barbell-deadlift"
                        },
                        {
                            "name": "Forearm Plank",
                            "target": "3 sets x 30–45 seconds",
                            "cue": "Full body tension, glutes locked, maintain neutral cervical spine.",
                            "url": "https://musclewiki.com/exercise/plank"
                        }
                    ],
                    "desk_mobility": "Hamstring dynamic couch stretch (2 min per side)."
                }
            },
            1: {
                "track_a": {
                    "title": "Cardio & Spine Decompression (Lap Swim Intervals)",
                    "category": "Cardio & Recovery",
                    "goal": "Low-impact high-calorie burn, decompress spine and shoulders after desk work.",
                    "exercises": [
                        {
                            "name": "Warmup Freestyle Laps",
                            "target": "100m relaxed pace",
                            "cue": "Focus on smooth bilateral breathing and long body rotation.",
                            "url": "https://www.youtube.com/results?search_query=freestyle+swimming+technique+drills"
                        },
                        {
                            "name": "Main Set: Freestyle Intervals",
                            "target": "6 x 50m intervals @ 50–60s pace (30s rest between laps)",
                            "cue": "Steady stroke rate, engage core, maintain high elbows.",
                            "url": "https://www.youtube.com/results?search_query=freestyle+swimming+pacing"
                        },
                        {
                            "name": "Kickboard or Breaststroke Finisher",
                            "target": "100m steady pace",
                            "cue": "Active groin and hip stretch, strong flutter kick.",
                            "url": "https://musclewiki.com/exercise/flutter-kicks"
                        },
                        {
                            "name": "Cooldown Easy Float / Swim",
                            "target": "100m relaxed",
                            "cue": "Decompress spine, deep diaphragmatic breathing.",
                            "url": "https://www.youtube.com/results?search_query=swimming+cooldown+stretches"
                        }
                    ],
                    "desk_mobility": "Child's pose and thoracic rotation stretches post-swim."
                },
                "track_b": {
                    "title": "Cardio & Spine Decompression (Lap Swim Aerobic Endurance)",
                    "category": "Cardio & Recovery",
                    "goal": "Aerobic conditioning, steady cardiac output, thoracic decompression.",
                    "exercises": [
                        {
                            "name": "Warmup Mixed Stroke Laps",
                            "target": "150m easy freestyle & backstroke",
                            "cue": "Smooth relaxed pacing, loosen tight shoulder capsules.",
                            "url": "https://www.youtube.com/results?search_query=freestyle+swimming+technique+drills"
                        },
                        {
                            "name": "Main Set: 100m Continuous Laps",
                            "target": "4 x 100m continuous pace @ ~2:00/100m pace (45s rest)",
                            "cue": "Maintain steady stroke rhythm, strong core engagement.",
                            "url": "https://www.youtube.com/results?search_query=freestyle+swimming+pacing"
                        },
                        {
                            "name": "Freestyle Pulls with Buoy",
                            "target": "150m continuous upper body pulls",
                            "cue": "Isolate upper back and lats, counter desk hunch.",
                            "url": "https://musclewiki.com/exercise/cable-lat-pulldown"
                        },
                        {
                            "name": "Cooldown Float & Backstroke",
                            "target": "100m relaxed recovery",
                            "cue": "Deep diaphragmatic breathing, lengthen spine in water.",
                            "url": "https://www.youtube.com/results?search_query=swimming+cooldown+stretches"
                        }
                    ],
                    "desk_mobility": "Doorway lat stretch + kneeling hip flexor stretch."
                }
            },
            2: {
                "track_a": {
                    "title": "Full Body Strength B1 (Deadlift, Vertical Press & Kettlebells)",
                    "category": "Strength",
                    "goal": "Heavy hip hinge power, overhead pressing strength, and explosive hip snap.",
                    "exercises": [
                        {
                            "name": "Barbell Deadlift",
                            "target": "3 sets x 6-8 reps @ 135–185 lbs",
                            "cue": "Bar against shins, wedge hips into position, pull slack out of the bar, push floor away.",
                            "url": "https://musclewiki.com/exercise/barbell-deadlift"
                        },
                        {
                            "name": "Standing Dumbbell Overhead Press",
                            "target": "3 sets x 10 reps @ 25–30 lbs each",
                            "cue": "Squeeze glutes and abs, do not hyperextend lower back, press overhead.",
                            "url": "https://musclewiki.com/exercise/dumbbell-overhead-press"
                        },
                        {
                            "name": "Neutral Grip Lat Pulldown or Assisted Pull-ups",
                            "target": "3 sets x 10-12 reps @ 75–85 lbs",
                            "cue": "Pull elbows straight down into back pockets, pause at clavicle.",
                            "url": "https://musclewiki.com/exercise/cable-lat-pulldown"
                        },
                        {
                            "name": "Kettlebell Swings",
                            "target": "4 sets x 15 reps @ 35–45 lbs",
                            "cue": "Powerful hip hinge and snap, fire glutes at top, keep spine neutral.",
                            "url": "https://musclewiki.com/exercise/kettlebell-swing"
                        },
                        {
                            "name": "Cable Face Pulls (Desk Posture Cure)",
                            "target": "3 sets x 15 reps @ 30–40 lbs",
                            "cue": "Pull rope to forehead, rotate hands outwards to hit rear delts and external rotators.",
                            "url": "https://musclewiki.com/exercise/cable-face-pull"
                        }
                    ],
                    "desk_mobility": "Cat-cow stretch (10 reps) + neck chin tucks (15 reps)."
                },
                "track_b": {
                    "title": "Full Body Strength B2 (Squat Rack, Leg Press & Posterior Focus)",
                    "category": "Strength",
                    "goal": "Squat rack leg strength, overhead vertical pressing, and posture reversal.",
                    "exercises": [
                        {
                            "name": "Squat Rack Barbell Squat",
                            "target": "3 sets x 8-10 reps @ 95–135 lbs",
                            "cue": "Set pins at mid-chest, brace core 360°, drive knees out, hit parallel depth.",
                            "url": "https://musclewiki.com/exercise/barbell-squat"
                        },
                        {
                            "name": "Seated Dumbbell Overhead Press",
                            "target": "3 sets x 10 reps @ 25–30 lbs each",
                            "cue": "Back pressed into bench, press elbows vertically, control eccentric lowering.",
                            "url": "https://musclewiki.com/exercise/dumbbell-overhead-press"
                        },
                        {
                            "name": "Neutral Grip Lat Pulldown",
                            "target": "3 sets x 10-12 reps @ 80–90 lbs",
                            "cue": "Drive elbows straight down, squeeze scapulae together at the bottom.",
                            "url": "https://musclewiki.com/exercise/cable-lat-pulldown"
                        },
                        {
                            "name": "Leg Press (or Dumbbell Split Squats)",
                            "target": "3 sets x 10 reps @ 140–160 lbs",
                            "cue": "Feet shoulder-width on platform, control 2-second eccentric, press through mid-foot.",
                            "url": "https://musclewiki.com/exercise/machine-leg-press"
                        },
                        {
                            "name": "Cable Face Pulls (Desk Posture Cure)",
                            "target": "3 sets x 15 reps @ 35–42.5 lbs",
                            "cue": "Pull rope to forehead, externally rotate wrists, reverse desk slouch.",
                            "url": "https://musclewiki.com/exercise/cable-face-pull"
                        }
                    ],
                    "desk_mobility": "Cat-cow stretch and neck chin tucks between meetings."
                }
            },
            3: {
                "track_a": {
                    "title": "Active Recovery & Desk Worker Step Goal (Lakefront Walk)",
                    "category": "Recovery",
                    "goal": "Active circulation, lymphatic drainage, and posture reset.",
                    "exercises": [
                        {
                            "name": "Outdoor Walk / Treadmill Step Target",
                            "target": "8,000 – 10,000 steps total today (~4.0 – 5.0 miles)",
                            "cue": "Head outside along Lakefront/Chicago trail or indoor treadmill incline.",
                            "url": "https://musclewiki.com/exercise/standing-calf-raises"
                        },
                        {
                            "name": "Standing Desk Intervals",
                            "target": "3 x 30-minute standing sessions during workday",
                            "cue": "Shift weight between feet, engage calves, avoid locking knees.",
                            "url": "https://musclewiki.com/exercise/glute-bridge"
                        }
                    ],
                    "desk_mobility": "Deep couch stretch / hip flexor kneeling stretch (2 min per side)."
                },
                "track_b": {
                    "title": "Active Recovery & Posture Reset (Incline Walk & Thoracic Mobility)",
                    "category": "Recovery",
                    "goal": "Posterior chain blood flow, thoracic mobilization, and hip decompression.",
                    "exercises": [
                        {
                            "name": "Incline Treadmill Walk / Outdoor Trail",
                            "target": "30–40 min brisk incline walk (8–12% incline) or 8,000 steps",
                            "cue": "Maintain tall upright posture, push through glutes and calves.",
                            "url": "https://musclewiki.com/exercise/standing-calf-raises"
                        },
                        {
                            "name": "Standing Desk Intervals",
                            "target": "3 x 30-minute standing sessions during workday",
                            "cue": "Shift weight, engage core, keep screen at eye level.",
                            "url": "https://musclewiki.com/exercise/glute-bridge"
                        }
                    ],
                    "desk_mobility": "Thoracic spine foam rolling + 2 min pigeon stretch per side."
                }
            },
            4: {
                "track_a": {
                    "title": "Full Body Strength C1 (Kettlebell Swings & Squat Rack Power)",
                    "category": "Strength",
                    "goal": "Explosive hip hinge power, full-body hypertrophy, and grip strength.",
                    "exercises": [
                        {
                            "name": "Kettlebell Swings",
                            "target": "4 sets x 15-20 reps @ 35–45 lbs",
                            "cue": "Powerful hip hinge and snap, fire glutes, keep spine neutral throughout.",
                            "url": "https://musclewiki.com/exercise/kettlebell-swing"
                        },
                        {
                            "name": "Squat Rack Barbell Squat",
                            "target": "3 sets x 8-10 reps @ 95–135 lbs",
                            "cue": "Set pins at mid-chest, brace core 360°, drive knees out, hit parallel depth.",
                            "url": "https://musclewiki.com/exercise/barbell-squat"
                        },
                        {
                            "name": "Incline Dumbbell Press",
                            "target": "3 sets x 10 reps @ 35–40 lbs each",
                            "cue": "Focus on clavicular pec contraction, steady 2-second lowering phase.",
                            "url": "https://musclewiki.com/exercise/incline-dumbbell-bench-press"
                        },
                        {
                            "name": "Seated Cable Row",
                            "target": "3 sets x 12 reps @ 75–85 lbs",
                            "cue": "Controlled negative, feel the lats stretch, squeeze shoulder blades.",
                            "url": "https://musclewiki.com/exercise/cable-seated-row"
                        },
                        {
                            "name": "Farmer's Walk (Grip & Core)",
                            "target": "3 sets x 40 paces @ 40–50 lbs each hand",
                            "cue": "Stand tall, anti-shrug shoulders down, brace core against lateral sway.",
                            "url": "https://musclewiki.com/exercise/farmers-walk"
                        }
                    ],
                    "desk_mobility": "Hamstring and glute foam roll or dynamic stretches."
                },
                "track_b": {
                    "title": "Full Body Strength C2 (Deadlift & Conditioning Consolidation)",
                    "category": "Strength",
                    "goal": "Deadlift strength consolidation, explosive kettlebell conditioning, and upper back pump.",
                    "exercises": [
                        {
                            "name": "Barbell Deadlift",
                            "target": "3 sets x 6-8 reps @ 135–185 lbs",
                            "cue": "Bar against shins, wedge hips, push floor away through heels.",
                            "url": "https://musclewiki.com/exercise/barbell-deadlift"
                        },
                        {
                            "name": "Kettlebell Swings",
                            "target": "4 sets x 15 reps @ 35–45 lbs",
                            "cue": "Explosive hip extension, snap hips, core engaged.",
                            "url": "https://musclewiki.com/exercise/kettlebell-swing"
                        },
                        {
                            "name": "Flat Dumbbell Bench Press",
                            "target": "3 sets x 10 reps @ 35–40 lbs each",
                            "cue": "Retract scapulae, touch lower chest, press with control.",
                            "url": "https://musclewiki.com/exercise/dumbbell-bench-press"
                        },
                        {
                            "name": "Neutral Grip Lat Pulldown or Assisted Pull-ups",
                            "target": "3 sets x 10-12 reps @ 80–90 lbs",
                            "cue": "Elbows straight down, squeeze upper lats at bottom.",
                            "url": "https://musclewiki.com/exercise/cable-lat-pulldown"
                        },
                        {
                            "name": "Farmer's Walk (Grip & Core)",
                            "target": "3 sets x 40 paces @ 40–50 lbs each hand",
                            "cue": "Stand as tall as possible, anti-shrug shoulders, lock ribs down.",
                            "url": "https://musclewiki.com/exercise/farmers-walk"
                        }
                    ],
                    "desk_mobility": "Doorway pec stretch + deep child's pose."
                }
            },
            5: {
                "track_a": {
                    "title": "Weekend Lifestyle Cardio & Exploration",
                    "category": "Active Lifestyle",
                    "goal": "Unstructured outdoor activity, walk, or seasonal run.",
                    "exercises": [
                        {
                            "name": "Chicago Lakefront Walk / Outdoor Jog",
                            "target": "45–60 minutes outdoor movement (~3.0 – 4.0 miles)",
                            "cue": "Enjoy the fresh air, disconnect from screens, maintain brisk pace.",
                            "url": "https://musclewiki.com/exercise/standing-quad-stretch"
                        }
                    ],
                    "desk_mobility": "Full body relaxation & mobility."
                },
                "track_b": {
                    "title": "Weekend Active Outdoor Exploration",
                    "category": "Active Lifestyle",
                    "goal": "Unstructured outdoor cardio, urban hike, or bike ride.",
                    "exercises": [
                        {
                            "name": "Neighborhood Urban Hike / Casual Bike Ride",
                            "target": "60–90 minutes outdoor active movement",
                            "cue": "Explore Chicago neighborhoods, stay active, screen-free reset.",
                            "url": "https://musclewiki.com/exercise/standing-quad-stretch"
                        }
                    ],
                    "desk_mobility": "Full body relaxation & hip mobility."
                }
            },
            6: {
                "track_a": {
                    "title": "Weekly Reset & Weigh-In",
                    "category": "Rest & Evaluation",
                    "goal": "Track weight trend toward 165–170 lb goal and plan the week ahead.",
                    "exercises": [
                        {
                            "name": "Morning Weigh-In (Fasted)",
                            "target": "Log current weight in Health & Fitness.md",
                            "cue": "Compare with 191 lb baseline and evaluate weekly delta.",
                            "url": "https://musclewiki.com/exercise/seated-hamstring-stretch"
                        }
                    ],
                    "desk_mobility": "Gentle yoga / stretching and mental reset."
                },
                "track_b": {
                    "title": "Weekly Reset & Weigh-In",
                    "category": "Rest & Evaluation",
                    "goal": "Track weight trend toward 165–170 lb goal and plan the week ahead.",
                    "exercises": [
                        {
                            "name": "Morning Weigh-In (Fasted)",
                            "target": "Log current weight in Health & Fitness.md",
                            "cue": "Compare with 191 lb baseline and evaluate weekly delta.",
                            "url": "https://musclewiki.com/exercise/seated-hamstring-stretch"
                        }
                    ],
                    "desk_mobility": "Gentle yoga / stretching and mental reset."
                }
            }
        }

        week = timeline.get("week", 1) if timeline else 1
        day = timeline.get("day", weekday + 1) if timeline else weekday + 1

        day_catalog = routines_catalog.get(weekday, routines_catalog[0])

        # Track selection: default to alternating tracks by week number (Week 1 = Track A, Week 2 = Track B)
        selected_track = "track_b" if (week % 2 == 0) else "track_a"

        # Anti-duplication check: if recent history shows the same weekday ran selected_track, switch to the other track!
        same_weekday_routines = workout_history.get("same_weekday_routines", []) if workout_history else []
        if same_weekday_routines:
            last_same_day_title = same_weekday_routines[0].get("title", "").lower()
            track_a_title = day_catalog["track_a"]["title"].lower()
            track_b_title = day_catalog["track_b"]["title"].lower()

            if track_a_title in last_same_day_title or last_same_day_title in track_a_title:
                selected_track = "track_b"
            elif track_b_title in last_same_day_title or last_same_day_title in track_b_title:
                selected_track = "track_a"

        raw_routine = day_catalog.get(selected_track, day_catalog["track_a"])
        routine = dict(raw_routine)

        # Calibrate exercise targets using recent completed session actuals & working weights
        latest_actuals = workout_history.get("latest_actuals", {}) if workout_history else {}
        calibrated_exercises = []
        for ex in raw_routine["exercises"]:
            ex_copy = dict(ex)
            ex_copy["target"] = self._calibrate_target(
                exercise_name=ex["name"],
                default_target=ex["target"],
                latest_actuals=latest_actuals,
                working_weights=working_weights
            )
            calibrated_exercises.append(ex_copy)

        routine["exercises"] = calibrated_exercises
        routine["current_bmi"] = current_bmi
        routine["target_weight"] = self.profile["target_weight_lbs"]
        routine["weight_to_lose"] = round(self.profile["current_weight_lbs"] - 167.5, 1)

        # Attach timeline & context
        routine["program_week"] = week
        routine["program_day"] = day
        routine["cycle_display"] = f"Week {week}, Day {day}"
        routine["working_weights"] = working_weights or {}
        routine["latest_actuals"] = latest_actuals

        return routine

    def format_workout_markdown(self, routine: Dict[str, Any]) -> str:
        """Formats the routine as an interactive Obsidian markdown checklist with diagram links."""
        cycle_str = f" ({routine['cycle_display']})" if routine.get("cycle_display") else ""
        md = []
        md.append(f"## 🏋️ Workout{cycle_str}: {routine['title']}")
        md.append(f"> **Focus:** {routine['goal']}")
        md.append(f"> **Biometrics Context:** Current BMI: `{routine['current_bmi']}` • Target: `165-170 lbs` (`-{routine['weight_to_lose']} lbs` remaining)\n")

        for ex in routine["exercises"]:
            url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
            md.append(f"- [ ] **{url_part}** — {ex['target']}")
            md.append(f"  - Form Cue: *{ex['cue']}*")
            md.append(f"  - Actual: `___ lbs x ___ reps`")

        md.append(f"\n> [!TIP]\n> **Desk Worker Posture Cue:** {routine['desk_mobility']}\n")
        return "\n".join(md)
