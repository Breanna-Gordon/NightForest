"""hud.py: the HUD conditions.

The two non-empty conditions give the SAME information in different ways:

   Information                  Full on-screen HUD        Built into the world
   Progress                     count (counter)           orbs (found lanterns glow beside your lantern)
   Direction to nearest goal    compass (arrow)           wisp (a blue firefly drifts towards it)
   Where everything is          map (mini-map)            beacon (lanterns glow through the dark, with a shaft of light)
   Health (damage)              health (bar)              blood (red mist) + cracks (your lantern cracks and dims)
   Danger (shadow near)         warn (warning panel)      cold (blue frost and a cold blue flame) + ping (heartbeat)
   Which side the shadow is on  map (red dot)             pan (the heartbeat and whispers come from that ear)

   Two separate channels in the world version: RED + CRACKS = you are hurt. BLUE + HEARTBEAT = the shadow is close.

NOTE: the map shows more than the world cues do. Describe the conditions as packages in your report.
Conditions are lists of these feature names in config.py."""
import math
import pygame
from . import config as C

LEGEND = {
    "full": ["Counter (top left): lanterns found out of the total.",
             "Health bar (under the counter).",
             "Compass arrow (top centre): points to the nearest lantern.",
             "Mini-map (top right): trees, lanterns (orange diamonds), the shadow (red) and you (white arrow).",
             "DANGER panel (bottom): the shadow is close."],
    "world": ["Small lights beside your lantern: one for each lantern found.",
              "A glowing blue wisp floats towards the nearest lantern. Follow it.",
              "Lanterns glow through the dark from far away, with a shaft of light.",
              "SHADOW NEAR: your flame turns cold blue, frost creeps in at the edges, whispers and a heartbeat grow (from its side).",
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
    """Clear map of the whole forest: trees, lanterns, the shadow and you, with a key underneath."""
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
        for it in w.items:                                           # lanterns: orange diamonds
            x, y = X(it[0]), Y(it[1])
            pts = [(x, y - 7), (x + 5, y), (x, y + 7), (x - 5, y)]
            pygame.draw.polygon(surface, (255, 169, 77), pts)
            pygame.draw.polygon(surface, (255, 255, 255), pts, 1)
        if w.shadow_on:                                              # the shadow: pulsing red dot
            pygame.draw.circle(surface, (255, 59, 59), (int(X(w.sx)), int(Y(w.sy))), int(6 + math.sin(t * 4)))
            pygame.draw.circle(surface, (255, 255, 255), (int(X(w.sx)), int(Y(w.sy))), int(6 + math.sin(t * 4)), 1)
        pygame.draw.polygon(surface, (255, 255, 255), rot([(9, 0), (-6, -6), (-6, 6)], w.pa, X(w.px), Y(w.py)))   # you: arrow
        ky = y0 + self.h + 12
        text(surface, fonts["s"], "you", (x0, ky), (255, 255, 255), shadow=False)
        text(surface, fonts["s"], "lantern", (x0 + 48, ky), (255, 169, 77), shadow=False)
        text(surface, fonts["s"], "shadow", (x0 + 120, ky), (255, 90, 90), shadow=False)


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
    if has(w, "compass") and w.nearest:
        cx, cy = W // 2, 62
        pygame.draw.circle(surface, (4, 6, 12), (cx, cy), 40)
        pygame.draw.circle(surface, (120, 135, 165), (cx, cy), 40, 2)
        rel = math.atan2(w.nearest[1] - w.py, w.nearest[0] - w.px) - w.pa
        pygame.draw.polygon(surface, (255, 169, 77), rot([(0, -28), (-17, 18), (0, 9), (17, 18)], rel, cx, cy))
    if has(w, "warn") and w.shadow_close > 0.35:
        panel(surface, pygame.Rect(W // 2 - 110, H - 64, 220, 46), 200)
        pygame.draw.polygon(surface, (255, 107, 107), [(W // 2 - 86, H - 28), (W // 2 - 70, H - 28), (W // 2 - 78, H - 48)])
        text(surface, fonts["m"], "DANGER", (W // 2 - 56, H - 56), (255, 107, 107))
    if has(w, "map"):
        minimap.draw(surface, w, fonts, t)
