"""assets.py: all artwork is drawn by code when the game starts (no image files needed).

Sprites are painted at twice the size and shrunk with smoothing, which gives clean,
anti-aliased edges. Glows are black surfaces that are ADDED to the screen, so they
brighten the dark instead of covering it."""
import math
import random
import pygame

SS = 2                      # painting scale (supersampling)


def surf(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def shrink(s, w, h):
    return pygame.transform.smoothscale(s, (w, h))


def make_glow(radius, color, power=2.0):
    """A soft round glow on black, for additive blending."""
    g = pygame.Surface((radius * 2, radius * 2))
    g.fill((0, 0, 0))
    for r in range(radius, 0, -1):
        k = (1 - r / radius) ** power
        pygame.draw.circle(g, (int(color[0] * k), int(color[1] * k), int(color[2] * k)), (radius, radius), r)
    return g


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgradient(w, h, top, bottom, mid=None):
    s = pygame.Surface((w, h))
    for y in range(h):
        t = y / max(1, h - 1)
        c = lerp(top, bottom, t) if mid is None else (lerp(top, mid[1], t / mid[0]) if t < mid[0] else lerp(mid[1], bottom, (t - mid[0]) / (1 - mid[0])))
        pygame.draw.line(s, c, (0, y), (w, y))
    return s


def _taper(s, col, p0, p1, w0, w1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    pygame.draw.polygon(s, col, [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2),
                                 (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)])
    pygame.draw.circle(s, col, (int(p1[0]), int(p1[1])), max(1, int(w1 / 2)))


def _branch(s, rnd, col, x, y, ang, length, width, depth, moss=None):
    """A curving, forking branch. ang is measured from straight up."""
    px, py, a = x, y, ang
    for i in range(3):
        a += rnd.uniform(-0.4, 0.4)
        l = length / 3
        nx, ny = px + math.sin(a) * l, py - math.cos(a) * l * 0.9
        _taper(s, col, (px, py), (nx, ny), width * (1 - i / 3 * 0.6), width * (1 - (i + 1) / 3 * 0.6))
        if depth > 0 and i >= 1 and rnd.random() < 0.85:
            _branch(s, rnd, col, nx, ny, a + rnd.choice((-1, 1)) * rnd.uniform(0.4, 0.95), length * rnd.uniform(0.38, 0.58), width * 0.55, depth - 1, moss)
        px, py = nx, ny
    if depth > 0:
        for sd in (-1, 1):
            _branch(s, rnd, col, px, py, a + sd * rnd.uniform(0.3, 0.75), length * rnd.uniform(0.35, 0.55), width * 0.5, depth - 1, moss)
    elif moss is not None and rnd.random() < 0.35:
        moss.append((px, py))


def dead_tree(seed, w=440, h=640):
    """A tall, bare, twisted tree: flared roots, curving trunk with bark lines, forking branches, hanging moss."""
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    col, rim = (22, 18, 31), (66, 78, 108)
    bx, by = W / 2, H - 6 * SS
    tx, ty = bx + rnd.uniform(-0.05, 0.05) * W, H * 0.42
    bend = rnd.uniform(-0.09, 0.09) * W
    left, right, centre = [], [], []
    n = 26
    for i in range(n + 1):
        t = i / n
        x = bx + (tx - bx) * t + math.sin(t * math.pi) * bend
        y = by + (ty - by) * t
        wd = W * 0.058 * (1 - t * 0.64) * (1 + (1.1 * (1 - t / 0.16) if t < 0.16 else 0))      # flare at the roots
        left.append((x - wd, y)); right.append((x + wd, y)); centre.append((x, y, wd))
    for sd in (-1, 1):                                       # roots
        for k in range(2):
            a = sd * (1.1 + k * 0.35 + rnd.uniform(-0.1, 0.1))
            _taper(s, col, (bx, by - 14 * SS), (bx + math.sin(a) * W * 0.17, by + 4 * SS), W * 0.05, W * 0.012)
    pygame.draw.polygon(s, col, left + right[::-1])
    for _ in range(34):                                       # bark: dark cracks and pale ridges
        t0 = rnd.uniform(0, 0.85)
        i0 = int(t0 * n); i1 = min(n, i0 + rnd.randint(2, 5))
        off = rnd.uniform(-0.8, 0.8)
        c = (11, 9, 17) if rnd.random() < 0.65 else (40, 36, 54)
        pygame.draw.line(s, c, (centre[i0][0] + off * centre[i0][2], centre[i0][1]), (centre[i1][0] + off * centre[i1][2], centre[i1][1]), SS)
    pygame.draw.lines(s, rim, False, left[2:int(n * 0.85)], SS * 2)              # moonlit left edge
    moss = []
    for k in range(7):                                        # branches up the trunk
        t = 0.34 + 0.66 * k / 7
        i = int(t * n)
        x, y, wd = centre[i]
        side = -1 if k % 2 else 1
        _branch(s, rnd, col, x, y, side * rnd.uniform(0.5, 1.15), H * 0.165 * (1.15 - t * 0.55), wd * 0.95, 3, moss)
    _branch(s, rnd, col, tx, ty, rnd.uniform(-0.15, 0.15), H * 0.15, centre[-1][2] * 1.3, 3, moss)     # the crown
    for (mx, my) in moss[:14]:                                # hanging moss
        for k in range(3):
            ln = rnd.uniform(14, 40) * SS
            pygame.draw.line(s, (40, 66, 58), (mx + k * 3 * SS, my), (mx + k * 3 * SS + rnd.uniform(-3, 3) * SS, my + ln), SS)
    return shrink(s, w, h)


def pine(seed, w=250, h=640):
    """A dark, drooping evergreen with a ragged skirt."""
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    pygame.draw.rect(s, (24, 18, 26), (W / 2 - W * 0.025, H * 0.78, W * 0.05, H * 0.22))
    tiers = 8
    for i in range(tiers):
        t = i / (tiers - 1)
        yb = H * (0.86 - t * 0.74)                            # bottom of this tier
        half = W * (0.46 - t * 0.38)
        top = yb - H * 0.14
        pts = [(W / 2, top)]
        for k in range(9):                                    # ragged, drooping lower edge
            px = W / 2 - half + 2 * half * k / 8
            pts.append((px, yb + (H * 0.02 if k % 2 else -H * 0.012) + rnd.uniform(0, H * 0.012)))
        base = lerp((8, 26, 24), (14, 40, 34), rnd.random())
        pygame.draw.polygon(s, base, pts)
        pygame.draw.polygon(s, (52, 74, 88), [pts[0], pts[1], (pts[1][0] + half * 0.15, pts[1][1] - H * 0.01)])     # moonlit edge
        pygame.draw.lines(s, (30, 56, 54), False, pts[:5], SS)
        for k in range(1, 10):                                # drooping needles along the edge
            px = pts[k][0]
            for _ in range(2):
                pygame.draw.line(s, (16, 40, 36), (px, pts[k][1] - 4 * SS), (px + rnd.uniform(-7, 7) * SS, pts[k][1] + rnd.uniform(10, 26) * SS), SS * 2)
        for _ in range(26):                                   # lighter needle clusters
            x = W / 2 + rnd.uniform(-half, half) * (1 - (yb - rnd.uniform(top, yb)) / (yb - top) * 0.6)
            y = rnd.uniform(top + (yb - top) * 0.25, yb)
            pygame.draw.line(s, (34, 66, 58), (x, y), (x + rnd.uniform(-5, 5) * SS, y + rnd.uniform(5, 12) * SS), SS)
    return shrink(s, w, h)


def lantern_post(w=150, h=380):
    """A lantern hanging from an iron post: cage, bright glass, hook."""
    W, H = w * SS, h * SS
    s = surf(W, H)
    iron = (24, 22, 28)
    pygame.draw.rect(s, iron, (W / 2 - 5 * SS, H * 0.12, 10 * SS, H * 0.88))                 # post
    pygame.draw.polygon(s, iron, [(W / 2 - 8 * SS, H), (W / 2 + 8 * SS, H), (W / 2 + 4 * SS, H * 0.9), (W / 2 - 4 * SS, H * 0.9)])
    pygame.draw.line(s, iron, (W / 2, H * 0.14), (W / 2 + 36 * SS, H * 0.1), 6 * SS)          # arm
    pygame.draw.arc(s, iron, (W / 2 + 20 * SS, H * 0.02, 28 * SS, 30 * SS), 0, math.pi, 4 * SS)
    lx, ly, lw, lh = W / 2 + 36 * SS, H * 0.14, 34 * SS, 56 * SS                             # lamp
    pygame.draw.polygon(s, iron, [(lx - lw / 2 - 4 * SS, ly), (lx + lw / 2 + 4 * SS, ly), (lx, ly - 14 * SS)])
    pygame.draw.rect(s, (255, 222, 150), (lx - lw / 2, ly, lw, lh))
    pygame.draw.rect(s, (255, 244, 205), (lx - lw / 4, ly + 6 * SS, lw / 2, lh - 14 * SS))
    for k in range(4):
        pygame.draw.line(s, iron, (lx - lw / 2 + k * lw / 3, ly), (lx - lw / 2 + k * lw / 3, ly + lh), 3 * SS)
    pygame.draw.rect(s, iron, (lx - lw / 2 - 3 * SS, ly + lh, lw + 6 * SS, 8 * SS))
    return shrink(s, w, h)


def gravestone(seed, w=150, h=190):
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    style = seed % 3
    body = (92, 99, 116)
    x0, x1, yt, yb = W * 0.2, W * 0.8, H * (0.28 if style != 2 else 0.2), H * 0.93
    if style == 0:                                            # rounded top
        pts = [(x0, yb), (x0, yt + W * 0.3)] + [(W / 2 + math.cos(math.pi + k * math.pi / 12) * (x1 - x0) / 2, yt + W * 0.3 + math.sin(math.pi + k * math.pi / 12) * W * 0.3) for k in range(13)] + [(x1, yb)]
    elif style == 1:                                          # broken, tilted top
        pts = [(x0, yb), (x0, yt + 20 * SS), (x0 + (x1 - x0) * 0.4, yt), (x0 + (x1 - x0) * 0.6, yt + 30 * SS), (x1, yt + 16 * SS), (x1, yb)]
    else:                                                     # cross
        cx, cw = W / 2, W * 0.09
        pts = [(cx - cw, yb), (cx - cw, yt + H * 0.3), (x0, yt + H * 0.3), (x0, yt + H * 0.2), (cx - cw, yt + H * 0.2), (cx - cw, yt), (cx + cw, yt), (cx + cw, yt + H * 0.2), (x1, yt + H * 0.2), (x1, yt + H * 0.3), (cx + cw, yt + H * 0.3), (cx + cw, yb)]
    pygame.draw.polygon(s, body, pts)
    pygame.draw.polygon(s, (62, 68, 86), pts, 2 * SS)
    pygame.draw.line(s, (130, 140, 166), (x0 + 2 * SS, yb), (x0 + 2 * SS, yt + 30 * SS), 2 * SS)     # moonlit edge
    if style != 2:
        pygame.draw.line(s, (50, 56, 72), (W / 2, yt + H * 0.2), (W / 2, yt + H * 0.42), 3 * SS)     # engraved cross
        pygame.draw.line(s, (50, 56, 72), (W / 2 - 14 * SS, yt + H * 0.28), (W / 2 + 14 * SS, yt + H * 0.28), 3 * SS)
    for _ in range(3):                                        # cracks
        x = rnd.uniform(x0, x1); y = rnd.uniform(yt + 20 * SS, yb - 30 * SS)
        pygame.draw.lines(s, (40, 44, 58), False, [(x, y), (x + rnd.uniform(-9, 9) * SS, y + 12 * SS), (x + rnd.uniform(-9, 9) * SS, y + 26 * SS)], SS)
    for _ in range(5):                                        # moss patches
        pygame.draw.circle(s, (52, 84, 66), (int(rnd.uniform(x0, x1)), int(rnd.uniform(yb - 50 * SS, yb))), rnd.randint(6, 13) * SS)
    for k in range(9):                                        # grass at the foot
        gx = W * 0.12 + k * W * 0.095
        pygame.draw.line(s, (36, 64, 54), (gx, yb + 2 * SS), (gx + rnd.uniform(-6, 6) * SS, yb - rnd.uniform(14, 30) * SS), SS * 2)
    return shrink(s, w, h)


def rock(seed, w=140, h=90):
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    pts = [(W / 2 + math.cos(a / 8 * 6.283) * W * rnd.uniform(0.34, 0.46), H * 0.62 + math.sin(a / 8 * 6.283) * H * rnd.uniform(0.2, 0.32)) for a in range(8)]
    pygame.draw.polygon(s, (46, 54, 66), pts)
    pygame.draw.polygon(s, (92, 104, 126), [pts[4], pts[5], pts[6], (W / 2, H * 0.5)])
    pygame.draw.polygon(s, (30, 36, 46), [pts[0], pts[1], pts[2], (W / 2, H * 0.62)])
    for k in range(7):
        gx = W * 0.2 + k * W * 0.1
        pygame.draw.line(s, (36, 64, 54), (gx, H * 0.88), (gx + rnd.uniform(-5, 5) * SS, H * 0.62), SS * 2)
    return shrink(s, w, h)


def mushrooms(seed, w=110, h=90):
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    for k in range(5):
        x = W * (0.15 + 0.7 * rnd.random()); base = H * (0.8 + 0.1 * rnd.random()); sz = rnd.uniform(0.6, 1.2)
        glow = surf(60 * SS, 60 * SS)
        for r in range(28 * SS, 0, -SS):
            pygame.draw.circle(glow, (120, 240, 170, int(40 * (1 - r / (28 * SS)))), (30 * SS, 30 * SS), r)
        s.blit(glow, (x - 30 * SS, base - 40 * SS))
        pygame.draw.rect(s, (205, 225, 200), (x - 3 * SS * sz, base - 22 * SS * sz, 6 * SS * sz, 22 * SS * sz))
        pygame.draw.ellipse(s, (130, 235, 170), (x - 14 * SS * sz, base - 34 * SS * sz, 28 * SS * sz, 18 * SS * sz))
        pygame.draw.ellipse(s, (210, 255, 225), (x - 6 * SS * sz, base - 31 * SS * sz, 8 * SS * sz, 5 * SS * sz))
    return shrink(s, w, h)


def wraith(frame, w=260, h=560):
    """The shadow: a tall, tattered, hooded figure inside a purple aura, with glowing red eyes. Four frames sway."""
    W, H = w * SS, h * SS
    s = surf(W, H)
    sway = math.sin(frame * math.pi / 2) * W * 0.03
    for r in range(int(W * 0.5), 0, -SS * 3):                 # aura
        pygame.draw.ellipse(s, (120, 60, 200, int(105 * (1 - r / (W * 0.5)) ** 1.4)), (W / 2 + sway - r, H * 0.5 - r * 1.9, r * 2, r * 3.8))
    rnd = random.Random(5)
    body = (14, 4, 26, 238)
    top, hem = H * 0.14, H * 0.92
    pts = [(W / 2 + sway * 0.4, top)]
    pts += [(W / 2 + sway * 0.6 - W * 0.12, top + H * 0.07), (W / 2 + sway * 0.5 - W * 0.16, top + H * 0.2), (W / 2 + sway * 0.2 - W * 0.26, H * 0.55)]
    for k in range(9):                                        # ragged, flowing hem
        t = k / 8
        pts.append((W / 2 + sway * 0.1 - W * 0.3 + W * 0.6 * t, hem + math.sin(t * 17 + frame * 1.7) * H * 0.03 + (H * 0.05 if k % 2 else 0)))
    pts += [(W / 2 + sway * 0.2 + W * 0.26, H * 0.55), (W / 2 + sway * 0.5 + W * 0.16, top + H * 0.2), (W / 2 + sway * 0.6 + W * 0.12, top + H * 0.07)]
    pygame.draw.polygon(s, body, pts)
    for sd in (-1, 1):                                        # long, thin arms
        _taper(s, body, (W / 2 + sd * W * 0.14 + sway * 0.4, top + H * 0.17), (W / 2 + sd * W * 0.3 + sway, H * 0.5), W * 0.05, W * 0.012)
        for f in range(3):
            pygame.draw.line(s, body, (W / 2 + sd * W * 0.3 + sway, H * 0.5), (W / 2 + sd * (W * 0.3 + f * 6 * SS) + sway, H * 0.58 + f * 6 * SS), SS * 2)
    pygame.draw.ellipse(s, (2, 0, 6, 255), (W / 2 + sway * 0.4 - W * 0.085, top + H * 0.035, W * 0.17, H * 0.1))      # the void under the hood
    for sd in (-1, 1):                                        # eyes
        ex, ey = W / 2 + sway * 0.4 + sd * W * 0.035, top + H * 0.075
        pygame.draw.ellipse(s, (255, 60, 90, 90), (ex - 10 * SS, ey - 6 * SS, 20 * SS, 12 * SS))
        pygame.draw.ellipse(s, (255, 210, 215, 255), (ex - 3.5 * SS, ey - 2 * SS, 7 * SS, 4 * SS))
        pygame.draw.ellipse(s, (255, 40, 70, 255), (ex - 5 * SS, ey - 2.5 * SS, 10 * SS, 5 * SS), 0)
        pygame.draw.ellipse(s, (255, 235, 235, 255), (ex - 2 * SS, ey - 1.2 * SS, 4 * SS, 2.4 * SS))
    for k in range(8):                                        # trailing wisps
        x = W / 2 + sway * 0.1 + rnd.uniform(-0.28, 0.28) * W
        pygame.draw.lines(s, (28, 10, 52, 170), False, [(x, hem), (x + rnd.uniform(-9, 9) * SS, hem + 22 * SS), (x + rnd.uniform(-16, 16) * SS, hem + 46 * SS)], SS * 2)
    return shrink(s, w, h)


# ----------------------------------------------------------------------------- sky, horizon, atmosphere
def sky_panorama(pw, ph, moon_angle, fov):
    """The whole sky all the way round (wraps), so turning scrolls it. Stars, a big moon and a purple horizon glow."""
    s = vgradient(pw, ph, (2, 3, 10), (46, 34, 70), mid=(0.62, (16, 12, 40)))
    rnd = random.Random(3)
    for _ in range(420):                                      # stars
        x, y = rnd.randrange(pw), int(rnd.random() ** 1.5 * ph * 0.9)
        b = rnd.randint(110, 255)
        if rnd.random() < 0.08:
            s.blit(make_glow(5, (b // 2, b // 2, b // 2), 1.5), (x - 5, y - 5), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (b, b, min(255, b + 20)), (x, y), 1 if rnd.random() < 0.85 else 2)
    mx, my = int(moon_angle / (math.tau) * pw), int(ph * 0.3)
    for off in (-pw, 0, pw):
        s.blit(make_glow(190, (120, 125, 160), 2.2), (mx + off - 190, my - 190), special_flags=pygame.BLEND_RGB_ADD)
        pygame.draw.circle(s, (236, 232, 206), (mx + off, my), 40)
        pygame.draw.circle(s, (214, 210, 184), (mx + off - 6, my + 4), 40, 0)
        pygame.draw.circle(s, (240, 238, 216), (mx + off - 10, my - 8), 30)
        for dx, dy, r in ((-12, -10, 9), (14, 8, 12), (-5, 18, 6), (16, -16, 5), (-22, 6, 5)):
            pygame.draw.circle(s, (196, 192, 168), (mx + off + dx, my + dy), r)
    return s


def cloud_panorama(pw, ph):
    """Wispy dark clouds that drift across the moon (transparent, wraps)."""
    s = surf(pw, ph)
    rnd = random.Random(8)
    for _ in range(26):
        cx, cy, ln = rnd.randrange(pw), rnd.randint(int(ph * 0.06), int(ph * 0.75)), rnd.randint(160, 520)
        for k in range(5):
            for off in (-pw, 0, pw):
                pygame.draw.ellipse(s, (6, 5, 18, 26 + k * 5), (cx + off - ln / 2 + k * 14, cy - 10 + k * 3, ln - k * 28, 22 - k * 3))
    return s


def horizon_panorama(pw, ph):
    """Far-off silhouettes of dead trees and pines along the horizon (wraps)."""
    s = surf(pw, ph)
    rnd = random.Random(11)
    for layer, (col, hmax) in enumerate(((( 26, 22, 46, 255), 0.7), ((14, 12, 28, 255), 1.0))):
        x = rnd.randint(0, 30)
        while x < pw + 40:
            th = ph * rnd.uniform(0.35, hmax) * (0.7 + 0.3 * layer)
            wd = th * rnd.uniform(0.16, 0.3)
            if rnd.random() < 0.55:
                for k in range(5):
                    yb = ph - th * (0.05 + k * 0.17)
                    pygame.draw.polygon(s, col, [(x, yb - th * 0.17), (x + wd * (1 - k * 0.17), yb), (x - wd * (1 - k * 0.17), yb)])
            else:
                _taper(s, col, (x, ph), (x + rnd.uniform(-5, 5), ph - th * 0.55), wd * 0.18, wd * 0.07)
                for k in range(4):
                    sd = -1 if k % 2 else 1
                    a, b = (x, ph - th * (0.35 + k * 0.1)), (x + sd * wd * rnd.uniform(0.6, 1.2), ph - th * (0.55 + k * 0.1))
                    _taper(s, col, a, b, wd * 0.08, wd * 0.02)
            x += int(wd * rnd.uniform(0.9, 1.9))
        pygame.draw.rect(s, col, (0, ph - 6, pw, 6))
    return s


def mist_panorama(pw, ph):
    """Low drifting ground mist (transparent, wraps)."""
    low = surf(pw // 8, ph // 4)
    rnd = random.Random(21)
    for _ in range(70):
        cx, cy, rx, ry = rnd.randrange(low.get_width()), rnd.randrange(low.get_height()), rnd.randint(20, 70), rnd.randint(4, 12)
        for off in (-low.get_width(), 0, low.get_width()):
            pygame.draw.ellipse(low, (160, 180, 210, rnd.randint(8, 22)), (cx + off - rx, cy - ry, rx * 2, ry * 2))
    return shrink(low, pw, ph)


def vignette(w, h, strength=1.0, color=(0, 0, 0), inner=0.45, power=2.2):
    """A soft darkened border (transparent in the middle)."""
    sw, sh = 96, 54
    s = surf(sw, sh)
    for y in range(sh):
        for x in range(sw):
            d = math.hypot((x / sw - 0.5) * 2 * 0.95, (y / sh - 0.5) * 2)
            t = max(0.0, (d - inner) / (1.45 - inner))
            s.set_at((x, y), (*color, int(255 * min(1.0, (t ** power) * strength))))
    return shrink(s, w, h)


def grain(w, h):
    """Very faint film grain, made from random bytes (fast)."""
    n = w * h
    g = random.randbytes(n)
    rgba = bytearray(n * 4)
    rgba[0::4] = g; rgba[1::4] = g; rgba[2::4] = g
    rgba[3::4] = bytes([7]) * n
    return pygame.image.frombuffer(bytes(rgba), (w, h), "RGBA").convert_alpha()


def grass_tuft(seed, w=90, h=64):
    """A clump of dark, dead-looking grass blades with pale tips."""
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    for k in range(14):
        x0 = W * (0.2 + 0.6 * rnd.random())
        ln = H * rnd.uniform(0.5, 0.95)
        lean = rnd.uniform(-0.45, 0.45)
        col = lerp((20, 44, 40), (40, 78, 62), rnd.random())
        pts = [(x0 - 3 * SS, H), (x0 + lean * ln * 0.5 - 1 * SS, H - ln * 0.6), (x0 + lean * ln, H - ln), (x0 + lean * ln * 0.5 + 2 * SS, H - ln * 0.6), (x0 + 3 * SS, H)]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.line(s, (72, 104, 94), pts[2], ((pts[1][0] + pts[2][0]) / 2, (pts[1][1] + pts[2][1]) / 2), SS)
    return shrink(s, w, h)




# ---------------------------------------------------------------- landmarks (one per glade; they help you find your way)
def _halo(s, cx, cy, rad, col, strength):
    for r in range(int(rad), 0, -SS):
        pygame.draw.circle(s, (col[0], col[1], col[2], int(strength * (1 - r / rad) ** 1.6)), (int(cx), int(cy)), r)


def shrine(w=260, h=340):
    """A broken stone arch with a softly glowing blue rune."""
    W, H = w * SS, h * SS
    s = surf(W, H)
    stone, dark, lite = (86, 94, 112), (48, 54, 70), (128, 140, 166)
    cx, cy = W / 2, H * 0.56
    _halo(s, cx, cy, W * 0.34, (110, 220, 255), 90)
    pygame.draw.rect(s, dark, (W * 0.06, H * 0.9, W * 0.88, H * 0.07))
    for x0 in (W * 0.13, W * 0.75):
        pygame.draw.rect(s, stone, (x0, H * 0.22, W * 0.12, H * 0.69))
        pygame.draw.line(s, lite, (x0 + 2 * SS, H * 0.22), (x0 + 2 * SS, H * 0.9), 2 * SS)
        pygame.draw.rect(s, dark, (x0 - W * 0.02, H * 0.2, W * 0.16, H * 0.05))
    lintel = [(W * 0.1, H * 0.2), (W * 0.9, H * 0.2), (W * 0.9, H * 0.12), (W * 0.62, H * 0.1), (W * 0.54, H * 0.17), (W * 0.42, H * 0.07), (W * 0.1, H * 0.12)]
    pygame.draw.polygon(s, stone, lintel)
    pygame.draw.polygon(s, dark, lintel, 2 * SS)
    pygame.draw.circle(s, (190, 248, 255), (int(cx), int(cy)), int(W * 0.1), 3 * SS)
    pygame.draw.line(s, (190, 248, 255), (cx, cy - W * 0.16), (cx, cy + W * 0.16), 3 * SS)
    pygame.draw.line(s, (190, 248, 255), (cx - W * 0.1, cy + W * 0.04), (cx + W * 0.1, cy - W * 0.04), 3 * SS)
    for k in range(9):
        gx = W * 0.06 + k * W * 0.1
        pygame.draw.line(s, (36, 64, 54), (gx, H * 0.93), (gx + (k % 3 - 1) * 5 * SS, H * 0.8), 2 * SS)
    return shrink(s, w, h)


def stones(w=330, h=240):
    """A row of tall standing stones with warm amber marks."""
    W, H = w * SS, h * SS
    s = surf(W, H)
    rnd = random.Random(5)
    for i, (xc, hh, ww) in enumerate(((0.12, 0.62, 0.1), (0.3, 0.84, 0.12), (0.5, 0.95, 0.13), (0.7, 0.8, 0.12), (0.88, 0.58, 0.1))):
        x, top, bw = W * xc, H * (1 - hh), W * ww
        pts = [(x - bw / 2, H * 0.93), (x - bw / 2 * 0.9, top + H * 0.06), (x - bw * 0.15, top), (x + bw * 0.35, top + H * 0.03), (x + bw / 2, top + H * 0.09), (x + bw / 2, H * 0.93)]
        _halo(s, x, top + (H * 0.93 - top) * 0.35, bw * 1.6, (255, 170, 80), 55)
        pygame.draw.polygon(s, (74, 80, 98), pts)
        pygame.draw.polygon(s, (44, 48, 62), pts, 2 * SS)
        pygame.draw.line(s, (120, 130, 156), (x - bw / 2 + 2 * SS, H * 0.93), (x - bw / 2 * 0.9 + 2 * SS, top + H * 0.07), 2 * SS)
        my = top + (H * 0.93 - top) * 0.3
        for j in range(3):
            pygame.draw.line(s, (255, 200, 120), (x - 6 * SS, my + j * 12 * SS), (x + 6 * SS, my + j * 12 * SS + rnd.uniform(-3, 3) * SS), 2 * SS)
    pygame.draw.rect(s, (30, 44, 40), (0, H * 0.92, W, H * 0.08))
    return shrink(s, w, h)


def mushroom_ring(w=340, h=130):
    """A ring of glowing mushrooms in the grass."""
    W, H = w * SS, h * SS
    s = surf(W, H)
    rnd = random.Random(9)
    _halo(s, W / 2, H * 0.72, W * 0.5, (110, 240, 170), 38)
    for i in range(15):
        a = i / 15 * 6.283
        x = W / 2 + math.cos(a) * W * 0.42
        base = H * 0.72 + math.sin(a) * H * 0.2
        sz = 0.65 + 0.35 * (math.sin(a) + 1) / 2 + rnd.uniform(-0.1, 0.1)
        _halo(s, x, base - 14 * SS * sz, 26 * SS * sz, (120, 240, 170), 90)
        pygame.draw.rect(s, (205, 225, 200), (x - 3 * SS * sz, base - 20 * SS * sz, 6 * SS * sz, 20 * SS * sz))
        pygame.draw.ellipse(s, (130, 235, 170), (x - 13 * SS * sz, base - 32 * SS * sz, 26 * SS * sz, 17 * SS * sz))
        pygame.draw.ellipse(s, (215, 255, 228), (x - 5 * SS * sz, base - 29 * SS * sz, 8 * SS * sz, 5 * SS * sz))
    return shrink(s, w, h)


def fallen_log(seed, w=240, h=80):
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    y = H * 0.62
    body = [(W * 0.04, y + H * 0.2), (W * 0.06, y - H * 0.16), (W * 0.5, y - H * 0.22), (W * 0.94, y - H * 0.14), (W * 0.97, y + H * 0.2)]
    pygame.draw.polygon(s, (52, 40, 34), body)
    pygame.draw.polygon(s, (30, 24, 22), body, 2 * SS)
    pygame.draw.ellipse(s, (88, 70, 56), (W * 0.9, y - H * 0.16, W * 0.1, H * 0.36))             # the cut end
    pygame.draw.ellipse(s, (60, 46, 38), (W * 0.93, y - H * 0.08, W * 0.04, H * 0.2))
    for _ in range(10):
        x = rnd.uniform(W * 0.1, W * 0.85)
        pygame.draw.line(s, (36, 28, 24), (x, y - H * 0.18), (x + rnd.uniform(-8, 8) * SS, y + H * 0.14), SS)
    for _ in range(9):
        pygame.draw.circle(s, (52, 84, 66), (int(rnd.uniform(W * 0.1, W * 0.8)), int(y - H * 0.2 + rnd.uniform(0, 8) * SS)), rnd.randint(5, 11) * SS)
    for k in range(10):
        gx = W * 0.05 + k * W * 0.095
        pygame.draw.line(s, (36, 64, 54), (gx, y + H * 0.22), (gx + rnd.uniform(-5, 5) * SS, y + H * 0.02), 2 * SS)
    return shrink(s, w, h)


def stump(seed, w=120, h=110):
    rnd = random.Random(seed)
    W, H = w * SS, h * SS
    s = surf(W, H)
    pts = [(W * 0.18, H * 0.95), (W * 0.26, H * 0.4), (W * 0.22, H * 0.22), (W * 0.4, H * 0.3), (W * 0.52, H * 0.12), (W * 0.66, H * 0.3), (W * 0.78, H * 0.24), (W * 0.76, H * 0.45), (W * 0.84, H * 0.95)]
    pygame.draw.polygon(s, (48, 38, 34), pts)
    pygame.draw.polygon(s, (28, 22, 20), pts, 2 * SS)
    pygame.draw.line(s, (92, 78, 70), (W * 0.27, H * 0.9), (W * 0.31, H * 0.4), 2 * SS)
    for _ in range(5):
        pygame.draw.circle(s, (52, 84, 66), (int(rnd.uniform(W * 0.25, W * 0.75)), int(rnd.uniform(H * 0.55, H * 0.9))), rnd.randint(5, 10) * SS)
    for k in range(7):
        gx = W * 0.1 + k * W * 0.12
        pygame.draw.line(s, (36, 64, 54), (gx, H * 0.97), (gx + rnd.uniform(-5, 5) * SS, H * 0.8), 2 * SS)
    return shrink(s, w, h)
