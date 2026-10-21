"""render.py: draws the first-person view.

Trees, gravestones, lanterns and the shadow are sprites drawn from far to near, so nearer
things cover farther ones, and they fade into the dark with distance. The sky, clouds,
distant tree line and mist are wrap-around panoramas that scroll as you turn (parallax)."""
import math
import random
import pygame
from . import config as C
from . import assets as A
from . import hud as HUD

TAU = math.tau
LEVELS = [0.10, 0.22, 0.38, 0.56, 0.78, 1.0]


def clamp(v, a, b):
    return max(a, min(b, v))


class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.W, self.H = screen.get_size()
        W, H = self.W, self.H
        self.canvas = pygame.Surface((W, H))
        self.fonts = {"s": pygame.font.Font(None, 22), "m": pygame.font.Font(None, 32), "l": pygame.font.Font(None, 48), "xl": pygame.font.Font(None, 84)}
        pw = int(TAU / C.FOV * W)
        self.pw = pw
        self.sky_h = int(H * 0.72)
        self.sky = A.sky_panorama(pw, self.sky_h, 0.9, C.FOV)
        self.clouds = A.cloud_panorama(pw, int(H * 0.5))
        self.horizon = A.horizon_panorama(pw, int(H * 0.30))
        self.mist = A.mist_panorama(pw, int(H * 0.22))
        self.ground = A.vgradient(W, int(H * 0.62), (26, 46, 46), (3, 7, 8), mid=(0.10, (14, 28, 30)))
        self.vig_dark = A.vignette(W, H, 1.0, (0, 0, 0), 0.38, 1.9)
        self.vig_red = A.vignette(W, H, 1.0, (180, 0, 12), 0.34, 1.7)
        self.vig_cold = A.vignette(W, H, 1.0, (110, 150, 255), 0.4, 1.8)
        self.grain = A.grain(W * 2, H * 2)
        self.dead = [A.dead_tree(i) for i in range(6)]
        self.pines = [A.pine(i) for i in range(3)]
        self.graves = [A.gravestone(i) for i in range(3)]
        self.rocks = [A.rock(i) for i in range(3)]
        self.mush = [A.mushrooms(i) for i in range(2)]
        self.logs = [A.fallen_log(i) for i in range(2)]
        self.stumps = [A.stump(i) for i in range(2)]
        self.landmarks = {"shrine": A.shrine(), "stones": A.stones(), "ring": A.mushroom_ring()}
        self.grassy = [A.grass_tuft(i) for i in range(4)]
        self.lamp = A.lantern_post()
        self.wraith = [A.wraith(i) for i in range(4)]
        self.glow = {name: A.make_glow(96, col, 2.0) for name, col in (("orange", (255, 170, 70)), ("blue", (110, 180, 255)), ("red", (255, 40, 70)), ("green", (90, 230, 150)), ("print", (80, 190, 205)))}
        self.cache, self.gcache = {}, {}
        self.minimap = None
        self.blend = 0.0                       # smooth sprint field-of-view change

    # ------------------------------------------------------------------ helpers
    def set_forest(self, forest):
        if getattr(self, "_forest", None) is not forest:
            self._forest = forest
            self.minimap = HUD.MiniMap(forest)

    def _pano(self, pano, yaw, y, parallax=1.0, drift=0.0, alpha=None):
        W, PW = self.W, self.pw
        sx = int(((yaw * parallax + drift - C.FOV / 2) / TAU * PW) % PW)
        w1 = min(W, PW - sx)
        if alpha is not None:
            pano.set_alpha(alpha)
        self.canvas.blit(pano, (0, y), pygame.Rect(sx, 0, w1, pano.get_height()))
        if w1 < W:
            self.canvas.blit(pano, (w1, y), pygame.Rect(0, 0, W - w1, pano.get_height()))

    def _scaled(self, key, base, h_px, light):
        li = min(5, int(light * 6))
        b = int(math.log(max(h_px, 4)) / math.log(1.12))
        ck = (key, b, li)
        s = self.cache.get(ck)
        if s is None:
            if len(self.cache) > 2500:
                self.cache.clear()
            hh = max(2, int(1.12 ** b))
            ww = max(1, int(base.get_width() * hh / base.get_height()))
            s = pygame.transform.smoothscale(base, (ww, hh)) if hh < base.get_height() else pygame.transform.scale(base, (ww, hh))
            k = int(255 * LEVELS[li])
            s.fill((k, k, k, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self.cache[ck] = s
        return s

    def _glow(self, name, size, level=1.0):
        size = int(clamp(size, 6, 520))
        b = int(math.log(size) / math.log(1.2))
        lv = int(clamp(level, 0, 1) * 5)
        ck = (name, b, lv)
        g = self.gcache.get(ck)
        if g is None:
            if len(self.gcache) > 600:
                self.gcache.clear()
            sz = max(6, int(1.2 ** b))
            g = pygame.transform.smoothscale(self.glow[name], (sz, sz))
            k = int(255 * (0.2 + 0.8 * lv / 5))
            g.fill((k, k, k), special_flags=pygame.BLEND_RGB_MULT)
            self.gcache[ck] = g
        return g

    def _add_glow(self, name, cx, cy, size, level=1.0):
        g = self._glow(name, size, level)
        self.canvas.blit(g, (cx - g.get_width() // 2, cy - g.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)

    def _beacons(self, w, now, hy, fov):
        """A faint shaft of light rises from each lantern once it is within NEAR_RANGE. It is soft and thin, a clue
        rather than a signpost, and trees in front of it hide it. The full HUD gets the same clue from its compass."""
        W, H = self.W, self.H
        if not hasattr(self, "_beam"):
            beam = pygame.Surface((9, 64))
            for yy in range(64):
                for xx in range(9):
                    edge = 1 - abs(xx - 4) / 4.5
                    k = int(150 * (yy / 63) ** 2.2 * edge ** 1.5)
                    beam.set_at((xx, yy), (k, int(k * 0.72), int(k * 0.3)))
            self._beam = beam
        for it in w.items:
            d = math.hypot(it[0] - w.px, it[1] - w.py)
            if d > C.NEAR_RANGE or d < 0.8:
                continue
            a = math.atan2(it[1] - w.py, it[0] - w.px) - w.pa
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > fov / 2 + 0.3:
                continue
            S = min(H * 3.0, H / max(0.35, d * math.cos(a)) * 0.9)
            x, gy = (a / fov + 0.5) * W, hy + 0.45 * S
            al = clamp(1 - d / C.NEAR_RANGE, 0, 1) ** 0.7
            bw = max(10, int(S * 0.34))
            gh = max(8, int(gy - 4))
            beam = pygame.transform.smoothscale(self._beam, (bw, gh))
            beam.set_alpha(255)
            lvl = clamp(0.25 + 0.75 * al, 0, 1) * (0.9 + 0.1 * math.sin(now * 2.1 + it[0]))
            if lvl < 0.99:
                dim = pygame.Surface(beam.get_size())
                dim.fill((int(255 * lvl),) * 3)
                beam.blit(dim, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            self.canvas.blit(beam, (x - bw / 2, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _ponds(self, w, now, hy, fov, rng):
        """Still pools on the ground: dark water that catches a little moonlight. Scenery only."""
        W, H = self.W, self.H
        for (px, py, r) in w.f.ponds:
            d = math.hypot(px - w.px, py - w.py)
            if d > rng * 1.3:
                continue
            a = math.atan2(py - w.py, px - w.px) - w.pa
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > fov / 2 + 0.6:
                continue
            S = min(H * 3.0, H / max(0.35, d * math.cos(a)) * 0.9)
            sx, gy = (a / fov + 0.5) * W, hy + 0.45 * S
            ww, hh = int(min(2600, 2 * r * S)), int(max(3, min(500, 2 * r * S * 0.16)))
            fade = clamp((1 - d / (rng * 1.3)) * 1.6, 0, 1) * clamp((d - r * 0.4) / 1.2, 0, 1)
            if fade <= 0.03:
                continue
            pool = pygame.Surface((ww, hh), pygame.SRCALPHA)
            pygame.draw.ellipse(pool, (6, 16, 24, int(235 * fade)), (0, 0, ww, hh))
            pygame.draw.ellipse(pool, (70, 100, 130, int(90 * fade)), (ww * 0.18, hh * 0.2, ww * 0.64, hh * 0.5))
            sh = (math.sin(now * 1.7 + px) * 0.5 + 0.5) * ww * 0.3
            pygame.draw.ellipse(pool, (200, 220, 240, int(110 * fade)), (ww * 0.3 + sh * 0.4, hh * 0.3, ww * 0.16, max(2, hh * 0.18)))
            self.canvas.blit(pool, (sx - ww / 2, gy - hh / 2))

    def _footprints(self, w, now, hy, fov, rng):
        """Faint glowing footprints on the ground: the world version of 'where I have been'. Older and farther = fainter."""
        W, H = self.W, self.H
        for (x, y, t0, ang) in w.prints:
            d = math.hypot(x - w.px, y - w.py)
            if d < 0.9 or d > min(rng, 7.0):
                continue
            a = math.atan2(y - w.py, x - w.px) - w.pa
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > fov / 2 + 0.2:
                continue
            S = min(H * 3.0, H / max(0.25, d * math.cos(a)) * 0.9)
            sx, gy = (a / fov + 0.5) * W, hy + 0.45 * S
            level = clamp((1 - d / 7.0) * max(0.25, 1 - (w.t - t0) / 120.0) * 0.55, 0.05, 0.5)
            g = self._glow("print", max(8, 0.30 * S), level)
            g = pygame.transform.scale(g, (g.get_width(), max(2, int(g.get_height() * 0.35))))
            self.canvas.blit(g, (sx - g.get_width() // 2, gy - g.get_height() // 2), special_flags=pygame.BLEND_RGB_ADD)

    # ------------------------------------------------------------------ the 3D view
    def draw_world(self, w, now):
        W, H, cv = self.W, self.H, self.canvas
        sprint = 1.0 if w.sprinting else 0.0
        self.blend += (sprint - self.blend) * 0.08
        fov = C.FOV * (1 + 0.08 * self.blend)                                   # the view widens a little when you sprint
        hy = H * 0.5 + math.sin(w.bob) * (4 + 5 * self.blend)                   # head bob
        rng = max(3.0, w.view_range)

        cv.fill((2, 5, 6))
        self._pano(self.sky, w.pa, int(hy - self.sky_h))
        self._pano(self.clouds, w.pa, int(hy - self.H * 0.62), 1.25, now * 0.004, 150)
        cv.blit(self.ground, (0, int(hy)))
        self._pano(self.horizon, w.pa, int(hy - self.horizon.get_height() + 10), 1.0)
        self._pano(self.mist, w.pa, int(hy - self.H * 0.13), 1.15, now * 0.006, 110)

        self._ponds(w, now, hy, fov, rng)
        if HUD.has(w, "trail"):
            self._footprints(w, now, hy, fov, rng)
        if HUD.has(w, "beacon"):
            self._beacons(w, now, hy, fov)

        f = w.f
        todo = []
        for t in f.trees:
            d = math.hypot(t.x - w.px, t.y - w.py)
            if 0.25 < d < rng:
                todo.append((d, "tree", t))
        for p in f.props:
            d = math.hypot(p.x - w.px, p.y - w.py)
            if 0.25 < d < (rng * 1.7 if p.kind in self.landmarks else rng):
                todo.append((d, p.kind, p))
        gr = min(rng * 0.8, 7.0)
        for p in f.grass:
            if abs(p.x - w.px) < gr and abs(p.y - w.py) < gr:
                d = math.hypot(p.x - w.px, p.y - w.py)
                if 0.4 < d < gr:
                    todo.append((d, "grass", p))
        lr = rng * C.LANTERN_SEE
        for it in w.items if w.phase == "play" else [list(l) for l in f.lanterns]:
            d = math.hypot(it[0] - w.px, it[1] - w.py)
            if d < lr:
                todo.append((d, "lantern", it))
        if w.shadow_on:
            todo.append((math.hypot(w.sx - w.px, w.sy - w.py), "shadow", None))
        todo.sort(key=lambda e: -e[0])

        for d, kind, o in todo:
            if kind == "shadow":
                ox, oy = w.sx, w.sy
            else:
                ox, oy = (o[0], o[1]) if kind == "lantern" else (o.x, o.y)
            a = math.atan2(oy - w.py, ox - w.px) - w.pa
            a = math.atan2(math.sin(a), math.cos(a))
            if abs(a) > fov / 2 + 0.5:
                continue
            dp = max(0.25, d * math.cos(a))
            S = min(H * 3.0, H / dp * 0.9)                                     # screen pixels per tile at this distance
            x = (a / fov + 0.5) * W
            gy = hy + 0.45 * S
            light = clamp(1 - d / rng, 0, 1)
            if kind == "tree":
                if light < 0.07:
                    continue
                fade = clamp((d - 0.45) / 0.9, 0, 1)
                if fade <= 0:
                    continue
                dead = o.kind == "dead"
                base = self.dead[int(o.v * 997) % len(self.dead)] if dead else self.pines[int(o.v * 997) % len(self.pines)]
                s = self._scaled(("d" if dead else "p", int(o.v * 997) % (6 if dead else 3)), base, min(1700, (2.9 if dead else 3.0) * S), light)
                if fade < 1:
                    s.set_alpha(int(255 * fade))
                cv.blit(s, (x - s.get_width() / 2, gy - s.get_height()))
                s.set_alpha(255)
            elif kind == "grass":
                if light < 0.1:
                    continue
                idx = int(o.v * 997) % len(self.grassy)
                s = self._scaled(("g", idx), self.grassy[idx], min(500, (0.2 + 0.12 * o.v) * S), light)
                cv.blit(s, (x - s.get_width() / 2, gy - s.get_height() + 0.03 * S))
            elif kind in self.landmarks:                                          # landmarks: seen from further away than ordinary scenery
                al = clamp(1 - d / (rng * 1.7), 0, 1)
                if al <= 0.04:
                    continue
                hh = min(1500, {"shrine": 2.3, "stones": 1.5, "ring": 0.95}[kind] * S)
                s = self._scaled((kind, 0), self.landmarks[kind], hh, clamp(al * 1.4, 0.3, 1.0))
                cv.blit(s, (x - s.get_width() / 2, gy - s.get_height() + 0.04 * S))
                col = {"shrine": "blue", "stones": "orange", "ring": "green"}[kind]
                self._add_glow(col, int(x), int(gy - hh * 0.45), 1.5 * S, 0.45 * al)
            elif kind in ("grave", "rock", "mush", "log", "stump"):
                if light < 0.07:
                    continue
                lst, hf = {"grave": (self.graves, 0.8), "rock": (self.rocks, 0.3), "mush": (self.mush, 0.4), "log": (self.logs, 0.3), "stump": (self.stumps, 0.55)}[kind]
                idx = int(o.v * 997) % len(lst)
                s = self._scaled((kind, idx), lst[idx], min(900, hf * S), light)
                cv.blit(s, (x - s.get_width() / 2, gy - s.get_height() + 0.04 * S))
            elif kind == "lantern":
                al = clamp(1 - d / lr, 0, 1)
                if al <= 0.02:
                    continue
                hh = min(1500, 1.6 * S)
                s = self._scaled(("lamp", 0), self.lamp, hh, 1.0)
                top = gy - s.get_height()
                lx, ly = x - s.get_width() / 2 + 0.74 * s.get_width(), top + 0.215 * s.get_height()    # where the lamp is in the sprite
                s.set_alpha(int(255 * clamp(al * 1.6, 0.25, 1)))
                cv.blit(s, (x - s.get_width() / 2, top))
                s.set_alpha(255)
                flick = 0.85 + 0.15 * math.sin(now * 9 + o[0] * 7)
                self._add_glow("orange", lx, ly, 1.7 * S * flick, clamp(al * 1.4, 0.2, 1))
            else:                                                                 # the shadow
                body = light
                eyes = clamp(1 - d / (rng * 2.6), 0, 1)
                if eyes <= 0:
                    continue
                frame = self.wraith[int(now * 5) % 4]
                hh = min(1800, 2.5 * S)
                ww = frame.get_width() * hh / frame.get_height()
                top = gy - hh - 0.05 * S
                if body > 0.08:
                    s = pygame.transform.scale(frame, (max(1, int(ww)), max(1, int(hh))))
                    s.set_alpha(int(255 * clamp(body * 1.5, 0.15, 1)))
                    cv.blit(s, (x - ww / 2, top))
                ey = top + 0.215 * hh
                for sd in (-1, 1):
                    self._add_glow("red", int(x + sd * 0.035 * ww), int(ey), max(8, 0.16 * hh * 0.5), eyes)

        # mist in front of the trees, and the dark closing in round the edges of your torch light
        self._pano(self.mist, w.pa, int(hy - self.H * 0.02), 1.5, -now * 0.01, 90)
        dark = 0.80 + 0.2 * (1 - rng / C.VIEW_RANGE)
        self.vig_dark.set_alpha(int(255 * clamp(dark, 0, 1)))
        cv.blit(self.vig_dark, (0, 0))

        # world cues that belong to the "built into the world" condition
        self._world_cues(w, now, fov, hy)
        if w.relight > 0.01:                                                    # warm flash when a lantern is found / the forest lights up on a win
            a = w.relight * (0.7 if w.phase == "play" else 0.8)
            tint = pygame.Surface((W, H))
            tint.fill((int(110 * a), int(70 * a), int(22 * a)))
            cv.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # the held lantern (bottom right). In the world condition it is also a gauge:
        #   COLD  = the shadow is near (the flame turns blue and flickers)
        #   CRACKS = you are hurt (glass cracks, the light dims)
        cold = w.shadow_close if HUD.has(w, "cold") else 0.0
        cracks = int((100 - w.health) / 25 + 0.01) if HUD.has(w, "cracks") else 0
        flick = 0.9 + (0.1 + 0.25 * cold) * math.sin(now * (13 + 22 * cold))
        warm = w.near if HUD.has(w, "glow") else 0.0
        lit = (0.6 + 0.4 * rng / C.VIEW_RANGE) * flick * (1 - 0.14 * cracks) * ((0.45 + 1.4 * warm) if HUD.has(w, "glow") else 1.0)     # diegetic: dim and small when no lantern is near, big and bright when one is
        k = 1.3 + (0.35 * warm if HUD.has(w, "glow") else 0.1)                                                                           # the held lantern grows as you get warmer
        lx, ly = W - 130 + math.sin(w.bob * 0.5) * 3, H - 80 + abs(math.sin(w.bob)) * 5
        self._add_glow("orange", int(lx), int(ly), 190 * lit * (0.8 + 0.5 * warm), 0.85 * (1 - cold))
        if warm > 0.1:                                                                                  # a warm pulsing halo
            self._add_glow("orange", int(lx), int(ly), 120 + 150 * warm + 25 * math.sin(now * 5), 0.5 + 0.4 * warm)
        if cold > 0.02:
            self._add_glow("blue", int(lx), int(ly), 200 * lit, 0.9 * cold)
        glass = A.lerp((255, 226, 160), (160, 200, 255), cold)
        core = A.lerp((255, 246, 214), (225, 240, 255), cold)
        if HUD.has(w, "glow"):
            glass = A.lerp((150, 105, 60), glass, min(1.0, 0.45 + warm * 1.1 + cold))                 # a cold, dull glass when nothing is near
        iron = (30, 22, 14)
        P = lambda dx, dy: (lx + dx * k, ly + dy * k)
        pygame.draw.polygon(cv, iron, [P(-18, -18), P(18, -18), P(14, -34), P(-14, -34)])
        pygame.draw.rect(cv, glass, (*P(-15, -16), 30 * k, 42 * k), border_radius=3)
        pygame.draw.rect(cv, core, (*P(-8, -10), 16 * k, 28 * k * (0.55 + 0.45 * min(1.0, warm * 1.5 + cold) if HUD.has(w, "glow") else 1.0)), border_radius=3)
        for j in range(3):
            pygame.draw.line(cv, iron, P(-15 + j * 15, -16), P(-15 + j * 15, 26), 3)
        pygame.draw.rect(cv, iron, (*P(-20, 24), 40 * k, 8 * k), border_radius=3)
        pygame.draw.arc(cv, iron, (*P(-12, -52), 24 * k, 34 * k), 0, math.pi, 4)
        if cracks >= 1:
            pygame.draw.lines(cv, (50, 30, 24), False, [P(-13, -14), P(-3, 2), P(-10, 12), P(-4, 24)], 2)
        if cracks >= 2:
            pygame.draw.lines(cv, (50, 30, 24), False, [P(12, -14), P(3, 0), P(11, 10), P(5, 24)], 2)
            pygame.draw.polygon(cv, (10, 8, 6), [P(15, -16), P(15, -4), P(6, -16)])          # a chip of glass is missing
        if cracks >= 3:
            for dx, dy in ((-12, 6), (10, 8), (0, -4)):
                pygame.draw.line(cv, (50, 30, 24), P(0, 4), P(dx, dy + 10), 2)
            pygame.draw.polygon(cv, (10, 8, 6), [P(-15, 10), P(-15, 26), P(-4, 26)])

    def _world_cues(self, w, now, fov, hy):
        W, H, cv = self.W, self.H, self.canvas
        if HUD.has(w, "blood"):                     # RED mist = you are hurt (it only depends on your health, not on the shadow)
            a = min(0.9, (1 - w.health / 100) * 1.0)
            if a > 0.02:
                self.vig_red.set_alpha(int(255 * a))
                cv.blit(self.vig_red, (0, 0))
        if HUD.has(w, "cold") and w.shadow_close > 0.03:   # BLUE frost = the shadow is near (it only depends on distance), pulsing with the heartbeat
            a = min(0.9, w.shadow_close ** 1.1 * 0.8 + w.beat * 0.15 * w.shadow_close)
            self.vig_cold.set_alpha(int(255 * a))
            cv.blit(self.vig_cold, (0, 0))
        if HUD.has(w, "orbs"):                      # one light beside your lantern for each lantern found
            for i in range(w.found):
                ox = W - 130 + math.cos(i * 0.9 - 1.3) * 66
                oy = H - 128 - math.sin(i * 0.9) * 30 + math.sin(now * 3 + i) * 3
                self._add_glow("orange", int(ox), int(oy), 54, 0.9)
                pygame.draw.circle(cv, (255, 236, 200), (int(ox), int(oy)), 5)

    # ------------------------------------------------------------------ final frame
    def present(self, w, now, hud_on=True):
        W, H = self.W, self.H
        scr = self.screen
        ox = oy = 0
        if w.shake > 0:
            ox, oy = int((random.random() - 0.5) * 26 * w.shake), int((random.random() - 0.5) * 20 * w.shake)
        scr.fill((0, 0, 0))
        scr.blit(self.canvas, (ox, oy))
        if w.flash > 0:                             # red flash when the shadow hits
            self.vig_red.set_alpha(int(255 * w.flash))
            scr.blit(self.vig_red, (0, 0))
            tint = pygame.Surface((W, H))
            tint.fill((150, 10, 20))
            tint.set_alpha(int(110 * w.flash))
            scr.blit(tint, (0, 0))
        rx, ry = random.randrange(0, W), random.randrange(0, H)               # film grain
        scr.blit(self.grain, (0, 0), pygame.Rect(rx, ry, W, H))
        if hud_on:
            HUD.draw_hud(scr, w, self.fonts, self.minimap, C.FOV, now)
