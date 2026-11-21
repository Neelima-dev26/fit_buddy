"""Exercise library: structured data, so plans are built by code and every preference has a real effect.

Fields: id, name, pattern, equipment (bw/db/band/gym), level (1-3), joints it stresses, unit (reps/secs),
easier version, harder version, one-line cue, high-impact flag. 'kb' notes in the knowledge base explain form.
"""
EXERCISES_API = 2

_RAW = [
    # id, name, pattern, equip, level, stress, unit, easier, harder, cue, impact
    ("chair_squat", "Chair squat (sit to stand)", "squat", "bw", 1, "", "reps", "", "bw_squat", "Sit back to the chair, then stand tall.", 0),
    ("bw_squat", "Bodyweight squat", "squat", "bw", 1, "knee", "reps", "chair_squat", "", "Chest up, knees over toes.", 0),
    ("goblet_squat", "Goblet squat", "squat", "db", 1, "knee", "reps", "bw_squat", "", "Hold one dumbbell at your chest.", 0),
    ("band_squat", "Banded squat", "squat", "band", 1, "knee", "reps", "bw_squat", "", "Push your knees out against the band.", 0),
    ("leg_press", "Leg press machine", "squat", "gym", 1, "knee", "reps", "", "", "Press through your whole foot and do not lock your knees.", 0),
    ("glute_bridge", "Glute bridge", "hinge", "bw", 1, "", "reps", "", "single_leg_bridge", "Squeeze your glutes at the top.", 0),
    ("single_leg_bridge", "Single-leg glute bridge", "hinge", "bw", 2, "", "reps", "glute_bridge", "", "Keep your hips level.", 0),
    ("db_rdl", "Dumbbell Romanian deadlift", "hinge", "db", 1, "back", "reps", "glute_bridge", "", "Hips back, back flat, weights close.", 0),
    ("band_pull_through", "Band pull-through", "hinge", "band", 1, "", "reps", "glute_bridge", "", "Hinge at the hips and squeeze your glutes.", 0),
    ("leg_curl", "Leg curl machine", "hinge", "gym", 1, "", "reps", "", "", "Slow and controlled both ways.", 0),
    ("step_up", "Step-up", "lunge", "bw", 1, "knee", "reps", "", "reverse_lunge", "Use a sturdy low step and drive through your heel.", 0),
    ("reverse_lunge", "Reverse lunge", "lunge", "bw", 2, "knee,hip", "reps", "step_up", "", "Step back and keep your front knee over your ankle.", 0),
    ("split_squat", "Split squat", "lunge", "bw", 2, "knee,hip", "reps", "step_up", "", "Lower straight down, torso tall.", 0),
    ("db_reverse_lunge", "Dumbbell reverse lunge", "lunge", "db", 2, "knee,hip", "reps", "step_up", "", "Hold dumbbells at your sides.", 0),
    ("wall_pushup", "Wall push-up", "push", "bw", 1, "", "reps", "", "incline_pushup", "Keep your body in a straight line.", 0),
    ("incline_pushup", "Incline push-up (hands on a counter)", "push", "bw", 1, "wrist", "reps", "wall_pushup", "knee_pushup", "Lower your chest to the counter.", 0),
    ("knee_pushup", "Knee push-up", "push", "bw", 1, "wrist", "reps", "incline_pushup", "pushup", "Straight line from knees to head.", 0),
    ("pushup", "Push-up", "push", "bw", 2, "wrist,shoulder", "reps", "knee_pushup", "", "Elbows at about 45 degrees.", 0),
    ("db_chest_press", "Dumbbell chest press", "push", "db", 1, "", "reps", "", "", "Press up, lower slowly.", 0),
    ("band_chest_press", "Band chest press", "push", "band", 1, "", "reps", "", "", "Anchor the band behind you.", 0),
    ("machine_chest_press", "Machine chest press", "push", "gym", 1, "", "reps", "", "", "Set the handles at chest height.", 0),
    ("db_shoulder_press", "Dumbbell shoulder press", "vpush", "db", 1, "shoulder", "reps", "", "", "Ribs down, press straight up.", 0),
    ("band_overhead_press", "Band overhead press", "vpush", "band", 1, "shoulder", "reps", "", "", "Stand on the band and press overhead.", 0),
    ("machine_shoulder_press", "Machine shoulder press", "vpush", "gym", 1, "shoulder", "reps", "", "", "Keep your back against the pad.", 0),
    ("pike_pushup", "Pike push-up", "vpush", "bw", 3, "shoulder,wrist", "reps", "pushup", "", "Hips high, head between your arms.", 0),
    ("prone_yt", "Prone Y-T raise", "pull", "bw", 1, "", "reps", "", "table_row", "Lift your arms and squeeze your upper back.", 0),
    ("table_row", "Table row (lie under a sturdy table)", "pull", "bw", 2, "shoulder", "reps", "prone_yt", "", "Pull your chest to the table edge.", 0),
    ("band_row", "Band row", "pull", "band", 1, "", "reps", "prone_yt", "", "Squeeze your shoulder blades together.", 0),
    ("db_row", "One-arm dumbbell row", "pull", "db", 1, "back", "reps", "band_row", "", "Pull toward your hip, back flat.", 0),
    ("seated_row", "Seated cable row machine", "pull", "gym", 1, "", "reps", "", "", "Sit tall and pull your elbows back.", 0),
    ("lat_pulldown", "Lat pulldown machine", "pull", "gym", 1, "shoulder", "reps", "seated_row", "", "Pull the bar to your upper chest.", 0),
    ("band_pullapart", "Band pull-apart", "pull", "band", 1, "", "reps", "", "", "Arms straight, pull the band wide.", 0),
    ("db_curl", "Dumbbell biceps curl", "arms", "db", 1, "", "reps", "", "", "Elbows by your sides, no swinging.", 0),
    ("band_curl", "Band biceps curl", "arms", "band", 1, "", "reps", "", "", "Stand on the band and curl up.", 0),
    ("db_tricep", "Overhead triceps extension", "arms", "db", 1, "shoulder", "reps", "", "", "Elbows close to your head.", 0),
    ("band_pushdown", "Band triceps pushdown", "arms", "band", 1, "", "reps", "", "", "Anchor the band high and press down.", 0),
    ("cable_pushdown", "Cable triceps pushdown", "arms", "gym", 1, "", "reps", "", "", "Keep your elbows pinned to your sides.", 0),
    ("dead_bug", "Dead bug", "core", "bw", 1, "", "reps", "", "forearm_plank", "Lower opposite arm and leg slowly.", 0),
    ("forearm_plank", "Forearm plank", "core", "bw", 1, "", "secs", "dead_bug", "side_plank", "Straight line, squeeze your glutes.", 0),
    ("bird_dog", "Bird dog", "core", "bw", 1, "wrist", "reps", "dead_bug", "", "Reach opposite arm and leg, hips level.", 0),
    ("side_plank", "Side plank", "core", "bw", 2, "shoulder", "secs", "forearm_plank", "", "Stack your hips and stay long.", 0),
    ("db_chest_fly", "Dumbbell chest fly", "push", "db", 2, "shoulder", "reps", "db_chest_press", "", "Open your arms wide with soft elbows.", 0),
    ("db_reverse_fly", "Dumbbell reverse fly", "pull", "db", 1, "", "reps", "band_pullapart", "", "Hinge forward and lift your arms out to the sides.", 0),
    ("db_lateral_raise", "Dumbbell lateral raise", "vpush", "db", 1, "shoulder", "reps", "", "", "Lift to shoulder height with a slight elbow bend.", 0),
    ("db_hammer_curl", "Hammer curl", "arms", "db", 1, "", "reps", "", "", "Palms face each other, elbows by your sides.", 0),
    ("db_hip_thrust", "Dumbbell hip thrust", "hinge", "db", 2, "", "reps", "glute_bridge", "", "Rest your upper back on a bench and drive your hips up.", 0),
    ("leg_extension", "Leg extension machine", "squat", "gym", 1, "knee", "reps", "", "", "Control the weight both up and down.", 0),
    ("pallof_press", "Band Pallof press", "core", "band", 1, "", "reps", "dead_bug", "", "Press the band straight out and resist the twist.", 0),
    ("bicycle_crunch", "Bicycle crunch", "core", "bw", 2, "", "reps", "dead_bug", "", "Slow turns, elbow to opposite knee.", 0),
    ("band_glute_kickback", "Band glute kickback", "hinge", "band", 1, "", "reps", "glute_bridge", "", "Kick back and squeeze, no arching.", 0),
    ("band_face_pull", "Band face pull", "pull", "band", 1, "", "reps", "", "", "Pull toward your face with elbows high.", 0),
    ("lat_pulldown_close", "Machine row (chest supported)", "pull", "gym", 1, "", "reps", "", "", "Keep your chest on the pad and squeeze your back.", 0),
    ("farmer_carry", "Farmer's carry (walk holding dumbbells)", "carry", "db", 1, "", "secs", "", "", "Walk tall holding a dumbbell in each hand.", 0),
    ("calf_raise", "Calf raise", "calf", "bw", 1, "ankle", "reps", "", "", "Rise high, lower slowly.", 0),
    ("single_leg_stand", "Single-leg stand (hold a wall)", "balance", "bw", 1, "", "secs", "", "", "Stand tall and breathe.", 0),
]
_KEYS = ["id", "name", "pattern", "equip", "level", "stress", "unit", "easier", "harder", "cue", "impact"]
EXERCISES = []
for _r in _RAW:
    _e = dict(zip(_KEYS, _r))
    _e["stress"] = frozenset(x for x in _e["stress"].split(",") if x)
    EXERCISES.append(_e)
BY_ID = {e["id"]: e for e in EXERCISES}

EQUIP_RANK = {"gym": 0, "db": 1, "band": 2, "bw": 3}
