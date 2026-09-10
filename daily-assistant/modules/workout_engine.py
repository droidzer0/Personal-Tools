from datetime import date
from typing import Dict, List

class WorkoutEngine:
    def __init__(self, profile: Dict[str, any]):
        self.profile = profile

    def calculate_bmi(self, weight_lbs: float, height_in: float) -> float:
        """Calculates Body Mass Index (BMI)."""
        if height_in <= 0:
            return 0.0
        return round((weight_lbs * 703) / (height_in ** 2), 1)

    def get_today_routine(self, target_date: date) -> Dict[str, any]:
        """
        Determines the optimal routine based on day of week and Square 1 On-Ramp protocol.
        Weekday indices: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        """
        weekday = target_date.weekday()
        current_bmi = self.calculate_bmi(
            self.profile["current_weight_lbs"],
            self.profile["height_in"]
        )

        routines = {
            0: {
                "title": "Full Body Strength A (Squat & Horizontal Focus)",
                "category": "Strength",
                "goal": "Neuromuscular activation, controlled 2-second eccentrics, 90s rest.",
                "exercises": [
                    {
                        "name": "Goblet Squat (or Barbell Squat)",
                        "target": "3 sets x 10 reps @ 35 lbs",
                        "cue": "Knees track over toes, pause at depth to open tight hips.",
                        "url": "https://musclewiki.com/exercise/dumbbell-goblet-squat"
                    },
                    {
                        "name": "Dumbbell Bench Press",
                        "target": "3 sets x 10 reps @ 35 lbs each",
                        "cue": "Retract scapula into bench, protect shoulders.",
                        "url": "https://musclewiki.com/exercise/dumbbell-bench-press"
                    },
                    {
                        "name": "Chest-Supported Dumbbell / Cable Row",
                        "target": "3 sets x 12 reps @ 70 lbs",
                        "cue": "Drive elbows back, squeeze upper back to reverse desk slouch.",
                        "url": "https://musclewiki.com/exercise/cable-seated-row"
                    },
                    {
                        "name": "Dumbbell Romanian Deadlift (RDL)",
                        "target": "3 sets x 10 reps @ 30 lbs each",
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
            1: {
                "title": "Cardio & Spine Decompression (Lap Swim)",
                "category": "Cardio & Recovery",
                "goal": "Low-impact high-calorie burn, decompress spine and shoulders after desk work.",
                "exercises": [
                    {
                        "name": "Warmup Freestyle Laps",
                        "target": "100m easy pace",
                        "cue": "Focus on smooth breathing and long body rotation.",
                        "url": "https://www.youtube.com/results?search_query=freestyle+swimming+technique+drills"
                    },
                    {
                        "name": "Main Set: Freestyle Intervals",
                        "target": "6 x 50m moderate pace (30s rest between laps)",
                        "cue": "Steady stroke rate, engage core.",
                        "url": "https://www.youtube.com/results?search_query=freestyle+swimming+pacing"
                    },
                    {
                        "name": "Kickboard or Breaststroke Finisher",
                        "target": "100m steady pace",
                        "cue": "Active groin and hip stretch.",
                        "url": "https://musclewiki.com/exercise/flutter-kicks"
                    },
                    {
                        "name": "Cooldown Easy Float / Swim",
                        "target": "50m relaxed",
                        "cue": "Decompress spine, deep diaphragmatic breathing.",
                        "url": "https://www.youtube.com/results?search_query=swimming+cooldown+stretches"
                    }
                ],
                "desk_mobility": "Child's pose and thoracic rotation stretches post-swim."
            },
            2: {
                "title": "Full Body Strength B (Hinge & Vertical Focus)",
                "category": "Strength",
                "goal": "Upper back posture reinforcement and vertical pressing strength.",
                "exercises": [
                    {
                        "name": "Dumbbell Split Squat (or Leg Press)",
                        "target": "3 sets x 10 reps per side @ moderate load",
                        "cue": "Fix unilateral imbalances from sitting.",
                        "url": "https://musclewiki.com/exercise/dumbbell-split-squat"
                    },
                    {
                        "name": "Standing or Seated Dumbbell Overhead Press",
                        "target": "3 sets x 10 reps @ 25 lbs each",
                        "cue": "Squeeze glutes and abs, do not arch lower back.",
                        "url": "https://musclewiki.com/exercise/dumbbell-overhead-press"
                    },
                    {
                        "name": "Neutral Grip Lat Pulldown or Assisted Pull-ups",
                        "target": "3 sets x 10 reps @ moderate load",
                        "cue": "Pull elbows straight down into back pockets.",
                        "url": "https://musclewiki.com/exercise/cable-lat-pulldown"
                    },
                    {
                        "name": "Cable Face Pulls (Desk Posture Cure)",
                        "target": "3 sets x 15 reps @ light weight",
                        "cue": "Pull rope to forehead, rotate hands outwards to hit rear delts.",
                        "url": "https://musclewiki.com/exercise/cable-face-pull"
                    },
                    {
                        "name": "Forearm Plank",
                        "target": "3 sets x 30-45 seconds",
                        "cue": "Full body tension, glutes locked.",
                        "url": "https://musclewiki.com/exercise/plank"
                    }
                ],
                "desk_mobility": "Cat-cow stretch and neck chin tucks."
            },
            3: {
                "title": "Active Recovery & Desk Worker Step Goal",
                "category": "Recovery",
                "goal": "Active circulation, lymphatic drainage, and posture reset.",
                "exercises": [
                    {
                        "name": "Outdoor Walk / Treadmill Step Target",
                        "target": "8,000 – 10,000 steps total today",
                        "cue": "Head outside along Lakefront/Chicago trail or indoor treadmill incline.",
                        "url": "https://musclewiki.com/exercise/standing-calf-raises"
                    },
                    {
                        "name": "Standing Desk Intervals",
                        "target": "3 x 30-minute standing sessions during workday",
                        "cue": "Shift weight, engage calves.",
                        "url": "https://musclewiki.com/exercise/glute-bridge"
                    }
                ],
                "desk_mobility": "Deep couch stretch / hip flexor kneeling stretch (2 min per side)."
            },
            4: {
                "title": "Full Body Strength C (Endurance & Hypertrophy)",
                "category": "Strength",
                "goal": "Full-body pump and muscular endurance before the weekend.",
                "exercises": [
                    {
                        "name": "Kettlebell Swings",
                        "target": "4 sets x 15 reps @ 35 lbs",
                        "cue": "Powerful hip snap, fire glutes, keep back neutral.",
                        "url": "https://musclewiki.com/exercise/kettlebell-swing"
                    },
                    {
                        "name": "Incline Dumbbell Press",
                        "target": "3 sets x 10 reps @ 35 lbs each",
                        "cue": "Focus on clavicular pec contraction.",
                        "url": "https://musclewiki.com/exercise/incline-dumbbell-bench-press"
                    },
                    {
                        "name": "Seated Cable Row",
                        "target": "3 sets x 12 reps @ 75 lbs",
                        "cue": "Controlled negative, feel the lats stretch.",
                        "url": "https://musclewiki.com/exercise/cable-seated-row"
                    },
                    {
                        "name": "Dumbbell Romanian Deadlift",
                        "target": "3 sets x 10 reps @ 35 lbs each",
                        "cue": "Hips back, chest tall.",
                        "url": "https://musclewiki.com/exercise/dumbbell-romanian-deadlift"
                    },
                    {
                        "name": "Farmer's Walk (Grip & Core)",
                        "target": "3 sets x 40 paces @ 40 lbs each hand",
                        "cue": "Stand as tall as possible, anti-shrug shoulders.",
                        "url": "https://musclewiki.com/exercise/farmers-walk"
                    }
                ],
                "desk_mobility": "Hamstring and glute foam roll or dynamic stretches."
            },
            5: {
                "title": "Weekend Lifestyle Cardio & Exploration",
                "category": "Active Lifestyle",
                "goal": "Unstructured outdoor activity, walk, or seasonal run.",
                "exercises": [
                    {
                        "name": "Chicago Lakefront Walk / Light Jog",
                        "target": "45–60 minutes outdoor movement",
                        "cue": "Enjoy the fresh air, disconnect from screens.",
                        "url": "https://musclewiki.com/exercise/standing-quad-stretch"
                    }
                ],
                "desk_mobility": "Full body relaxation & mobility."
            },
            6: {
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
                "desk_mobility": "Gentle yoga / stretching."
            }
        }

        routine = routines.get(weekday, routines[0])
        routine["current_bmi"] = current_bmi
        routine["target_weight"] = self.profile["target_weight_lbs"]
        routine["weight_to_lose"] = round(self.profile["current_weight_lbs"] - 167.5, 1)

        return routine

    def format_workout_markdown(self, routine: Dict[str, any]) -> str:
        """Formats the routine as an interactive Obsidian markdown checklist with diagram links."""
        md = []
        md.append(f"## 🏋️ Workout: {routine['title']}")
        md.append(f"> **Focus:** {routine['goal']}")
        md.append(f"> **Biometrics Context:** Current BMI: `{routine['current_bmi']}` • Target: `165-170 lbs` (`-{routine['weight_to_lose']} lbs` remaining)\n")

        for ex in routine["exercises"]:
            url_part = f"[{ex['name']}]({ex.get('url', 'https://musclewiki.com')}) ↗"
            md.append(f"- [ ] **{url_part}** — {ex['target']}")
            md.append(f"  - Form Cue: *{ex['cue']}*")
            md.append(f"  - Actual: `___ lbs x ___ reps`")

        md.append(f"\n> [!TIP]\n> **Desk Worker Posture Cue:** {routine['desk_mobility']}\n")
        return "\n".join(md)
