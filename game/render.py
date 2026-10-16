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
        self.vig_red = A.vignette(W, H, 1.0, (180, 0, 12), 0.2, 1.5)
        self.grain = A.grain(W * 2, H * 2)
        self.dead = [A.dead_tree(i) for i in range(6)]
        self.pines = [A.pine(i) for i in range(3)]
        self.graves = [A.gravestone(i) for i in range(3)]
        self.rocks = [A.rock(i) for i in range(3)]
        self.mush = [A.mushrooms(i) for i in range(2)]
        self.grassy = [A.grass_tuft(i) for i in range(4)]
        self.lamp = A.lantern_post()
        self.wraith = [A.wraith(i) for i in range(4)]
        self.glow = {name: A.make_glow(96, col, 2.0) for name, col in (("orange", (255, 170, 70)), ("blue", (110, 180, 255)), ("red", (255, 40, 70)), ("green", (90, 230, 150)))}
        self.cache, self.gcache = {}, {}
        self.minimap = None
        self.blend = 0.0                       # smooth sprint field-of-view change

    # ------------------------------------------------------------------ helpers
    def set_forest(self, forest):
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

        f = w.f
        todo = []
        for t in f.trees:
            d = math.hypot(t.x - w.px, t.y - w.py)
            if 0.25 < d < rng:
                todo.append((d, "tree", t))
        for p in f.props:
            d = math.hypot(p.x - w.px, p.y - w.py)
            if 0.25 < d < rng:
                todo.append((d, p.kind, p))
        gr = min(rng * 0.8, 7.0)
        for p in f.grass:
            if abs(p.x - w.px) < gr and abs(p.y - w.py) < gr:
                d = math.hypot(p.x - w.px, p.y - w.py)
                if 0.4 < d < gr:
                    todo.append((d, "grass", p))
        beacon = HUD.has(w, "beacon")
        lr = rng * (4.0 if beacon else 1.8)
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
            elif kind in ("grave", "rock", "mush"):
                if light < 0.07:
                    continue
                lst, hf = {"grave": (self.graves, 0.8), "rock": (self.rocks, 0.3), "mush": (self.mush, 0.4)}[kind]
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
                if beacon and ly > 4:                                             # a faint shaft of light up into the sky
                    bw = max(4, int(S * 0.16))
                    beam = pygame.Surface((1, 64))
                    for yy in range(64):
                        k = int(150 * (yy / 63) ** 2 * al)
                        beam.set_at((0, yy), (k, int(k * 0.72), int(k * 0.3)))
                    cv.blit(pygame.transform.scale(beam, (bw, int(ly))), (lx - bw / 2, 0), special_flags=pygame.BLEND_RGB_ADD)
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

        # the held lantern (bottom right): flickers, dims with your light
        flick = 0.9 + 0.1 * math.sin(now * 13)
        lit = (0.6 + 0.4 * rng / C.VIEW_RANGE) * flick
        lx, ly = W - 130 + math.sin(w.bob * 0.5) * 3, H - 74 + abs(math.sin(w.bob)) * 5
        self._add_glow("orange", int(lx), int(ly), 190 * lit, 0.85)
        pygame.draw.polygon(cv, (30, 22, 14), [(lx - 18, ly - 18), (lx + 18, ly - 18), (lx + 14, ly - 34), (lx - 14, ly - 34)])
        pygame.draw.rect(cv, (255, 226, 160), (lx - 15, ly - 16, 30, 42), border_radius=3)
        pygame.draw.rect(cv, (255, 246, 214), (lx - 8, ly - 10, 16, 28), border_radius=3)
        for k in range(3):
            pygame.draw.line(cv, (30, 22, 14), (lx - 15 + k * 15, ly - 16), (lx - 15 + k * 15, ly + 26), 3)
        pygame.draw.rect(cv, (30, 22, 14), (lx - 20, ly + 24, 40, 8), border_radius=3)
        pygame.draw.arc(cv, (30, 22, 14), (lx - 12, ly - 52, 24, 34), 0, math.pi, 4)

    def _world_cues(self, w, now, fov, hy):
        W, H, cv = self.W, self.H, self.canvas
        if HUD.has(w, "vignette"):                  # red mist: more when hurt, more when the shadow is close, pulses with the heartbeat
            a = min(0.9, (1 - w.health / 100) * 0.75 + w.shadow_close * 0.3 + w.beat * 0.22)
            self.vig_red.set_alpha(int(255 * a))
            cv.blit(self.vig_red, (0, 0))
        if HUD.has(w, "orbs"):                      # one light beside your lantern for each lantern found
            for i in range(w.found):
                ox = W - 130 + math.cos(i * 0.9 - 1.3) * 66
                oy = H - 128 - math.sin(i * 0.9) * 30 + math.sin(now * 3 + i) * 3
                self._add_glow("orange", int(ox), int(oy), 54, 0.9)
                pygame.draw.circle(cv, (255, 236, 200), (int(ox), int(oy)), 5)
        if HUD.has(w, "wisp") and w.nearest:        # a blue firefly drifts towards the nearest lantern
            a = math.atan2(w.nearest[1] - w.py, w.nearest[0] - w.px) - w.pa
            a = math.atan2(math.sin(a), math.cos(a))
            x = clamp((a / fov + 0.5) * W, 90, W - 90)
            y = hy - 50 + math.sin(now * 2.4) * 7
            self._add_glow("blue", int(x), int(y), 96 + math.sin(now * 5) * 8, 1.0)
            pygame.draw.circle(cv, (235, 248, 255), (int(x), int(y)), 4)
            for k in range(4):                      # sparkles
                aa = now * 2.2 + k * 1.57
                pygame.draw.circle(cv, (190, 225, 255), (int(x + math.cos(aa) * 20), int(y + math.sin(aa * 1.3) * 14)), 2)

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
