"""world.py: the rules of the game (movement, sprinting, lanterns, shadow, health, ending).
Positions are in tiles. The renderer reads this object; it never changes it."""
import math
import random
from . import config as C

TAU = math.tau


class World:
    def __init__(self, forest, hud_key, practice=False):
        self.f = forest
        self.hud_key = hud_key
        self.flags = C.HUD_MODES[hud_key]
        self.practice = practice                      # practice: one lantern, no shadow, not recorded
        lanterns = forest.lanterns[:1] if practice else forest.lanterns
        self.items = [list(l) for l in lanterns]
        self.total = len(self.items)
        self.found = 0
        self.px, self.py = forest.start
        self.pa = 0.0
        self.vf = self.vs = self.vt = 0.0             # smoothed velocities (forward, sideways, turning)
        self.shadow_on = not practice
        self.shadow_speed = min(C.SHADOW_SPEED, C.WALK_SPEED * C.SHADOW_MAX_RATIO)
        self.sx, self.sy = forest.w - 2.5, forest.h - 2.5
        self.s_freeze = 0.0
        self.trail = []
        self.health = 100.0
        self.stamina, self.exhausted, self.sprinting = 1.0, False, False
        self.slow_until = 0.0
        self.t = 0.0                                  # seconds since the round began
        self.phase = "play"                           # play | won | lost
        self.result = ""
        # stats that are logged
        self.dist = self.sprint_time = 0.0
        self.pauses = self.exhaustions = self.hits = 0
        self.idle = 0.0
        self.idle_counted = False
        self.seen = set()
        # effects used by the renderer
        self.flash = self.shake = self.beat = 0.0
        self.nearest = None
        self.nearest_d = 99.0
        self.shadow_close = 0.0
        self.view_range = C.VIEW_RANGE
        self.bob = 0.0
        self.step_timer = 0.0
        self.next_ping = 0.0
        self.events = []                              # sounds to play: (name, volume, pan)

    # ------------------------------------------------------------------ one frame of game time
    def update(self, dt, ctl):
        """ctl: dict with fwd (-1..1), strafe (-1..1), turn (rad/s wanted), sprint (bool), mouse_turn (radians this frame)."""
        if self.phase != "play":
            return
        self.t += dt
        ease = min(1.0, dt * 10)
        want_fwd, want_str = ctl["fwd"], ctl["strafe"]
        intent = bool(want_fwd or want_str)

        # sprint uses stamina; when it runs out you must walk until you have recovered
        sprinting = ctl["sprint"] and intent and self.stamina > 0 and not self.exhausted
        top = C.WALK_SPEED
        if sprinting:
            top = C.SPRINT_SPEED
            self.stamina = max(0.0, self.stamina - dt / C.SPRINT_SECONDS)
            self.sprint_time += dt
            if self.stamina <= 0:
                self.exhausted = True
                self.exhaustions += 1
                self.events.append(("gasp", 0.8, 0.0))
        else:
            self.stamina = min(1.0, self.stamina + dt / C.SPRINT_RECOVER * (0.5 if intent else 1.0))
            if self.exhausted and self.stamina > 0.3:
                self.exhausted = False
        self.sprinting = sprinting
        if self.t < self.slow_until:
            top *= 0.6                                # slowed for a moment after a hit

        # smooth turning and movement
        self.vt += (ctl["turn"] - self.vt) * ease
        self.pa = (self.pa + self.vt * dt + ctl["mouse_turn"]) % TAU
        self.vf += (want_fwd * (top if want_fwd > 0 else top * 0.6) - self.vf) * ease
        self.vs += (want_str * top * 0.8 - self.vs) * ease
        ox, oy = self.px, self.py
        c, s = math.cos(self.pa), math.sin(self.pa)
        nx = self.px + (c * self.vf - s * self.vs) * dt
        ny = self.py + (s * self.vf + c * self.vs) * dt
        self.px, self.py = self.f.resolve_move(nx, ny)
        moved = math.hypot(self.px - ox, self.py - oy)
        self.dist += moved

        # stats: pauses (standing still for a second) and tiles visited
        if moved < dt * 0.15 and abs(self.vt) < 0.05:
            self.idle += dt
            if self.idle >= 1.0 and not self.idle_counted:
                self.pauses += 1
                self.idle_counted = True
        else:
            self.idle, self.idle_counted = 0.0, False
        self.seen.add((int(self.px), int(self.py)))

        # footsteps and head bob
        speed = moved / dt if dt > 0 else 0.0
        if speed > 0.3:
            self.bob += dt * (6.5 + speed * 1.6)
            self.step_timer -= dt
            if self.step_timer <= 0:
                self.step_timer = 0.5 if not sprinting else 0.29
                self.events.append(("step1" if int(self.bob) % 2 else "step2", 0.35 if not sprinting else 0.5, 0.0))

        # lanterns
        for it in self.items[:]:
            if math.hypot(it[0] - self.px, it[1] - self.py) < 0.6:
                self.items.remove(it)
                self.found += 1
                self.events.append(("pickup", 0.9, 0.0))
        self.nearest, self.nearest_d = None, 99.0
        for it in self.items:
            d = math.hypot(it[0] - self.px, it[1] - self.py)
            if d < self.nearest_d:
                self.nearest, self.nearest_d = it, d

        # effects fade
        self.flash = max(0.0, self.flash - dt * 2.5)
        self.shake = max(0.0, self.shake - dt * 3.0)
        self.beat = max(0.0, self.beat - dt * 4.0)

        # the shadow: slow, swaying, drains your light as it nears
        self.shadow_close = 0.0
        if self.shadow_on:
            ex, ey = self.px - self.sx, self.py - self.sy
            d = math.hypot(ex, ey) or 1.0
            if self.s_freeze > 0:
                self.s_freeze -= dt
            else:
                vx, vy, sway = ex / d, ey / d, math.sin(self.t * 1.1) * 0.5
                self.sx += (vx - vy * sway) * self.shadow_speed * dt
                self.sy += (vy + vx * sway) * self.shadow_speed * dt
            if int(self.t * 8) != int((self.t - dt) * 8):
                self.trail.append((self.sx, self.sy))
                self.trail = self.trail[-9:]
            if d < 0.6 and self.s_freeze <= 0:
                self.health -= C.SHADOW_DAMAGE
                self.hits += 1
                self.flash = self.shake = 1.0
                self.slow_until = self.t + 1.5
                self.events.append(("hit", 1.0, 0.0))
                self.px, self.py = self.f.resolve_move(self.px + ex / d * 1.3, self.py + ey / d * 1.3)
                self.sx, self.sy = self._far_spot()
                self.s_freeze, self.trail = C.SHADOW_FREEZE, []
                if self.health <= 0:
                    self.phase, self.result = "lost", "caught"
                    return
            self.shadow_close = max(0.0, 1.0 - d / 7.0)
        self.view_range = C.VIEW_RANGE * (1 - 0.35 * self.shadow_close) * (1 + 0.03 * math.sin(self.t * 11))   # your light shrinks and flickers

        # heartbeat (world HUD condition): faster when the shadow is near, comes from the shadow's side
        if "ping" in self.flags and self.shadow_close > 0.1 and self.t > self.next_ping:
            rel = math.atan2(self.sy - self.py, self.sx - self.px) - self.pa
            pan = math.sin(rel) if "pan" in self.flags else 0.0
            self.events.append(("heart", 0.35 + 0.65 * self.shadow_close, pan))
            self.beat = 1.0
            self.next_ping = self.t + 1.4 - 1.1 * self.shadow_close

        # ending
        if not self.items:
            self.phase, self.result = "won", "completed"
        elif self.t > C.TIME_LIMIT:
            self.phase, self.result = "lost", "timeUp"

    def _far_spot(self):                              # where the shadow reappears: far away, not inside a tree
        f = self.f
        for _ in range(200):
            x, y = 2 + random.random() * (f.w - 4), 2 + random.random() * (f.h - 4)
            if math.hypot(x - self.px, y - self.py) > min(14, f.w * 0.5) and not any(math.hypot(t.x - x, t.y - y) < 0.8 for t in f.trees_near(x, y)):
                return x, y
        return f.w - 2.5, f.h - 2.5

    def log_row(self, participant):
        return dict(participant=participant, build=C.BUILD, hudCondition=self.hud_key,
                    startedAt="", durationSec=round(self.t, 1), result=self.result, lanternsFound=self.found,
                    lanternsTotal=self.total, distance=round(self.dist * 24), pauses=self.pauses,
                    tilesVisited=len(self.seen), hits=self.hits, sprintSec=round(self.sprint_time, 1), exhaustions=self.exhaustions)
