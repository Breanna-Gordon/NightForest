"""config.py: every setting you are likely to change lives here (pilot build)."""

TITLE = "Night Forest - Pilot"
BUILD = "pilot"
PARTICIPANT_ID = "P00"          # or run:  python main.py P03

# --- window
SCREEN_W, SCREEN_H = 960, 540
FPS = 60

# --- forest (the same seed gives the same forest every time, so every participant plays the same map)
MAP = dict(
    w=24, h=16,                 # forest size in tiles
    seed=52,
    max_trees=200,              # the spacing rules below decide how many really fit
    spacing_open=2.2,           # trees in open areas are at least this far apart (tiles)
    spacing_dense=1.5,          # trees in denser woodland are at least this far apart (tiles)
    clear_radius=3.0,           # no trees this close to the start
    lanterns=3,
    min_start_distance=12.0,    # lanterns start at least this far from the player
    min_spacing=8.0,            # lanterns are at least this far apart
)
TIME_LIMIT = 180                # seconds per round

# --- player
WALK_SPEED = 2.2                # tiles per second
SPRINT_SPEED = 4.0              # hold Shift
SPRINT_SECONDS = 4.0            # stamina: seconds of sprinting before you run out of breath
SPRINT_RECOVER = 7.0            # seconds to get your breath back
TURN_SPEED = 2.0                # radians per second (keyboard)
MOUSE_SENSITIVITY = 0.0025      # radians per pixel (press M to switch mouse look on)

# --- the shadow
SHADOW_SPEED = 1.2              # tiles per second. Always slower than walking:
SHADOW_MAX_RATIO = 0.6          # ...it can never be faster than this share of walking speed
SHADOW_DAMAGE = 25              # health lost per hit (100 health)
SHADOW_FREEZE = 2.5             # seconds it pauses after a hit

# --- light
VIEW_RANGE = 9.0                # how far (tiles) your torch lets you see. Shrinks when the shadow is near
FOV = 1.15                      # field of view (radians)

# --- data logging: one row per recorded round is added to data/rounds.csv
LOG_ROUNDS = True

# --- HUD conditions. Each is a list of features (see hud.py). The researcher picks one in the menu.
HUD_MODES = {
    "full":  ["count", "compass", "health", "warn", "map"],
    "world": ["orbs", "wisp", "beacon", "blood", "cracks", "cold", "ping", "pan"],
}
HUD_LABELS = {"full": "Full on-screen HUD", "world": "Built into the world (diegetic)"}
