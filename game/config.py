"""config.py: every setting you are likely to change lives here (pilot build)."""

TITLE = "Night Forest - Study"
BUILD = "study"
PARTICIPANT_ID = "P00"          # or run:  python main.py P03

# --- window
SCREEN_W, SCREEN_H = 960, 540
FPS = 60

# --- forest (the same seed gives the same forest every time, so every participant plays the same map)
MAP = dict(
    w=44, h=30,                 # forest size in tiles (bigger forest: more to explore)
    seed=37,                    # overridden per round by MAP_SEEDS below
    max_trees=675,              # the spacing rules below decide how many really fit
    spacing_open=2.2,           # trees in open areas are at least this far apart (tiles)
    spacing_dense=1.5,          # trees in denser woodland are at least this far apart (tiles)
    clear_radius=3.0,           # no trees this close to the start
    lanterns=6,
    min_start_distance=14.0,    # lanterns start at least this far from the player
    glades=3,                   # clearings, each with a landmark (shrine, standing stones, mushroom ring)
    glade_radius=3.3,
    ponds=3,                    # scenery pools
    min_spacing=9.6,            # lanterns are at least this far apart
)
TIME_LIMIT = 300                # seconds per round (not shown on screen in either condition)

# --- player
WALK_SPEED = 2.2                # tiles per second
SPRINT_SPEED = 4.0              # hold Shift
SPRINT_SECONDS = 4.0            # stamina: seconds of sprinting before you run out of breath
SPRINT_RECOVER = 7.0            # seconds to get your breath back
TURN_SPEED = 2.0                # radians per second (keyboard)
MOUSE_SENSITIVITY = 0.0025      # radians per pixel (press M to switch mouse look on)

# --- the shadow
SHADOW_SPEED = 1.0              # tiles per second. Always slower than walking:
SHADOW_RAMP = 0.06              # extra speed for every lantern you have found (tension builds). Always capped at SHADOW_MAX_RATIO.
RELIGHT_HEAL = 15               # health restored when you find a lantern (and the shadow is pushed back)
RELIGHT_FREEZE = 3.0            # seconds the shadow is stunned after a lantern is found
SHADOW_MAX_RATIO = 0.6          # ...it can never be faster than this share of walking speed
SHADOW_DAMAGE = 25              # health lost per hit (100 health)
SHADOW_FREEZE = 2.5             # seconds it pauses after a hit
SHADOW_START = (0.55, 0.55)     # where it begins, as a share of the map (about 17 tiles from the player: it is felt early)

# --- light
NEAR_RANGE = 11.0               # how close (tiles) the nearest lantern must be before the "getting warmer" cue starts (guidance only starts inside this range, so you still explore)
LANTERN_SEE = 1.0               # how far you can see a lantern, as a multiple of your torch range (was 1.8: you could spot them from across the forest)
VIEW_RANGE = 9.0                # how far (tiles) your torch lets you see. Shrinks when the shadow is near
FOV = 1.15                      # field of view (radians)

# --- STUDY DESIGN. Two maps of matched difficulty (same route length, same tree count) so nobody replays a map.
# Seeds were chosen by comparing route length / tree count / lantern distance over seeds 1-59 (see README).
MAP_SEEDS = {"A": 42, "B": 75, "P": 20}   # P = practice map (never used in a recorded round)

# Counterbalancing: participant number n gets row (n-1) % 4. Each row = [(hud, map) for round 1, (hud, map) for round 2].
# Every HUD condition appears equally often first/second and on each map, so order and map are not confounded with HUD.
SCHEDULE = [
    [("full", "A"), ("world", "B")],
    [("world", "A"), ("full", "B")],
    [("full", "B"), ("world", "A")],
    [("world", "B"), ("full", "A")],
]

# --- data logging: one row per recorded round is added to data/rounds.csv
LOG_ROUNDS = True

# --- HUD conditions. Each is a list of features (see hud.py). The researcher's schedule decides which one a round uses.
HUD_MODES = {
    # Both conditions give the same four kinds of information: progress, health, shadow-near, where you have been.
    # Neither points at the lanterns or the shadow, so the HUD does not change how hard the task is.
    "full":  ["count", "health", "warn", "map", "near", "compass"],
    "world": ["orbs", "blood", "cracks", "cold", "ping", "trail", "glow", "beacon"],
}
HUD_LABELS = {"full": "Full on-screen HUD", "world": "Built into the world (diegetic)"}
