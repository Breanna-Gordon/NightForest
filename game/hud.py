"""hud.py: the two HUD conditions give the SAME four kinds of information in different ways:

   Information               Full on-screen HUD        Built into the world (diegetic)
   Progress                  count (counter)           orbs (a light beside your lantern for each lantern found)
   Health                    health (bar)              blood (red mist) + cracks (your lantern cracks and dims)
   Shadow near               warn (DANGER panel)       cold (blue frost + cold flame + whispers) + ping (heartbeat)
   Where you have been       map (explored ground)     trail (faintly glowing footprints)
   Lantern nearby            near (warmth bar) + compass   glow (lantern brightens) + beacon (faint shaft of light)

NEITHER condition points at the lanterns or the shadow, so the HUD does not make the task easier or harder.
Conditions are lists of these feature names in config.py."""
import math
import pygame
from . import config as C

LEGEND = {
    "full": ["Counter (top left): lanterns found out of the total.",
             "Health bar (under the counter).",
             "Mini-map (top right): the trees, the ground you have covered, and you (white arrow).",
             "Warmth bar (under the health bar): fills as the nearest lantern gets closer. Once a lantern is close, a compass arrow (top centre) points to it.",
             "DANGER panel (bottom): the shadow is close."],
    "world": ["Small lights beside your lantern: one for each lantern found.",
              "Faintly glowing footprints show where you have been.",
              "Your lantern burns brighter as a lost lantern gets closer. Once one is close, a faint shaft of light rises from it into the sky.",
              "SHADOW NEAR: your flame turns cold blue, frost creeps in at the edges, whispers and a heartbeat grow.",
              "HURT: red mist at the edges, and your lantern cracks and dims. Red = damage. Blue = the shadow is close."],
}


def has(w, feature):
    return feature in w.flags


def panel(surface, rect, alpha=170):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (4, 6, 12, alpha), s.get_rect(), border_radius=8)
    pygame.draw.rect(s, (120, 135, 165, 90), s.get_rect(), 1, border_radius=8)
    surface.blit(s, rect.topleft)


def text(surface, font, msg, pos, color=(235, 238, 245), anchor="topleft", shadow=True):
    img = font.render(msg, True, color)
    r = img.get_rect(**{anchor: pos})
    if shadow:
        surface.blit(font.render(msg, True, (0, 0, 0)), r.move(2, 2))
    surface.blit(img, r)
    return r


def rot(points, ang, cx, cy):
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in points]


class MiniMap:
    """Navigation aid only: trees, the ground you have covered, and you. It does NOT show lanterns or the shadow."""
    def __init__(self, forest):
        self.f = forest
        self.k = max(3, int(210 / forest.w))
        self.w, self.h = forest.w * self.k, forest.h * self.k
        self.base = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for t in forest.trees:
            pygame.draw.circle(self.base, (52, 112, 72), (int(t.x * self.k), int(t.y * self.k)), max(1, int(self.k * 0.28)))
        for p in forest.props:
            if p.kind == "grave":
                pygame.draw.rect(self.base, (150, 160, 185), (int(p.x * self.k) - 1, int(p.y * self.k) - 1, 3, 3))

    def draw(self, surface, w, fonts, t):
        W = surface.get_width()
        x0, y0 = W - self.w - 24, 18
        panel(surface, pygame.Rect(x0 - 8, y0 - 8, self.w + 16, self.h + 40), 190)
        surface.blit(self.base, (x0, y0))
        X = lambda v: x0 + v * self.k
        Y = lambda v: y0 + v * self.k
        for (tx, ty) in w.explored:                                  # explored ground, a soft glow
            pygame.draw.rect(surface, (60, 78, 100), (x0 + tx * self.k, y0 + ty * self.k, self.k, self.k))
        pygame.draw.polygon(surface, (255, 255, 255), rot([(9, 0), (-6, -6), (-6, 6)], w.pa, X(w.px), Y(w.py)))   # you: arrow
        ky = y0 + self.h + 12
        text(surface, fonts["s"], "you", (x0, ky), (255, 255, 255), shadow=False)
        pygame.draw.rect(surface, (60, 78, 100), (x0 + 48, ky + 3, 10, 10))
        text(surface, fonts["s"], "explored", (x0 + 64, ky), (170, 185, 210), shadow=False)


def draw_hud(surface, w, fonts, minimap, fov, t):
    W, H = surface.get_size()
    if has(w, "count"):
        panel(surface, pygame.Rect(16, 16, 210, 44))
        text(surface, fonts["m"], f"Lanterns  {w.found}/{w.total}", (28, 24))
    if has(w, "health"):
        panel(surface, pygame.Rect(16, 66, 210, 38))
        text(surface, fonts["s"], "Health", (28, 76), shadow=False)
        pygame.draw.rect(surface, (50, 52, 60), (92, 76, 120, 16), border_radius=5)
        pygame.draw.rect(surface, (90, 210, 110) if w.health > 40 else (240, 90, 90), (92, 76, int(120 * w.health / 100), 16), border_radius=5)
    if has(w, "compass") and w.nearest and w.near > 0.08:            # appears only within range: same as the light shafts
        cx, cy = W // 2, 62
        pygame.draw.circle(surface, (4, 6, 12), (cx, cy), 40)
        pygame.draw.circle(surface, (120, 135, 165), (cx, cy), 40, 2)
        rel = math.atan2(w.nearest[1] - w.py, w.nearest[0] - w.px) - w.pa
        pygame.draw.polygon(surface, (255, 169, 77), rot([(0, -28), (-17, 18), (0, 9), (17, 18)], rel, cx, cy))
    if has(w, "near"):
        panel(surface, pygame.Rect(16, 110, 210, 38))
        text(surface, fonts["s"], "Warmth", (28, 120), shadow=False)
        pygame.draw.rect(surface, (50, 52, 60), (92, 120, 120, 16), border_radius=5)
        pygame.draw.rect(surface, (255, 169, 77), (92, 120, int(120 * w.near), 16), border_radius=5)
    if has(w, "warn") and w.shadow_close > 0.35:
        panel(surface, pygame.Rect(W // 2 - 110, H - 64, 220, 46), 200)
        pygame.draw.polygon(surface, (255, 107, 107), [(W // 2 - 86, H - 28), (W // 2 - 70, H - 28), (W // 2 - 78, H - 48)])
        text(surface, fonts["m"], "DANGER", (W // 2 - 56, H - 56), (255, 107, 107))
    if has(w, "map"):
        minimap.draw(surface, w, fonts, t)


def draw_recap(surface, w, rect, fonts):
    """End-of-round map: the forest, the route you walked, and where every lantern was (found = lit, missed = hollow)."""
    f = w.f
    panel(surface, rect, 205)
    k = min((rect.w - 24) / f.w, (rect.h - 24) / f.h)
    ox, oy = rect.x + (rect.w - f.w * k) / 2, rect.y + (rect.h - f.h * k) / 2
    X = lambda v: ox + v * k
    Y = lambda v: oy + v * k
    for t in f.trees:
        pygame.draw.circle(surface, (46, 100, 66), (int(X(t.x)), int(Y(t.y))), max(1, int(k * 0.22)))
    for (px, py, r) in f.ponds:
        pygame.draw.ellipse(surface, (40, 70, 100), (X(px - r), Y(py - r * 0.7), 2 * r * k, 1.4 * r * k))
    marks = {"shrine": (110, 220, 255), "stones": (255, 170, 80), "ring": (120, 240, 170)}
    for (gx, gy, kind) in f.glades:
        pygame.draw.circle(surface, marks[kind], (int(X(gx)), int(Y(gy))), max(3, int(k * 0.5)), 1)
    if len(w.route) > 1:
        pygame.draw.lines(surface, (240, 210, 150), False, [(X(x), Y(y)) for x, y in w.route], 2)
    pygame.draw.circle(surface, (255, 255, 255), (int(X(f.start[0])), int(Y(f.start[1]))), 4)
    left = [tuple(i) for i in w.items]
    for (lx, ly) in f.lanterns[:w.total]:
        x, y = X(lx), Y(ly)
        pts = [(x, y - 8), (x + 6, y), (x, y + 8), (x - 6, y)]
        if (lx, ly) in left:
            pygame.draw.polygon(surface, (150, 150, 160), pts, 2)
        else:
            pygame.draw.polygon(surface, (255, 169, 77), pts)
            pygame.draw.polygon(surface, (255, 255, 255), pts, 1)
    text(surface, fonts["s"], "Your route (white dot = start)", (rect.x + 12, rect.bottom - 22), (170, 185, 210), shadow=False)


def draw_lantern_icon(surface, cx, cy, lit, s=1.0):
    col = (255, 205, 120) if lit else (70, 74, 88)
    pygame.draw.polygon(surface, (30, 24, 20), [(cx - 11 * s, cy - 10 * s), (cx + 11 * s, cy - 10 * s), (cx + 8 * s, cy - 20 * s), (cx - 8 * s, cy - 20 * s)])
    pygame.draw.rect(surface, col, (cx - 9 * s, cy - 10 * s, 18 * s, 26 * s), border_radius=3)
    pygame.draw.rect(surface, (30, 24, 20), (cx - 12 * s, cy + 15 * s, 24 * s, 5 * s), border_radius=2)
    pygame.draw.arc(surface, (30, 24, 20), (cx - 7 * s, cy - 31 * s, 14 * s, 20 * s), 0, math.pi, 3)
