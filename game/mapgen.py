"""mapgen.py: builds the forest from config.MAP.

Trees are individual round objects placed so they are never closer together than
spacing_dense. That guarantees wide gaps to walk through (a wood, not a maze).
Density changes smoothly across the map, giving thicker woods and clearings.
A ring of dense trees round the edge keeps the player inside."""
import math
import random

PLAYER_R = 0.25


class Tree:
    __slots__ = ("x", "y", "r", "v", "kind")

    def __init__(self, x, y, r, v):
        self.x, self.y, self.r, self.v = x, y, r, v
        self.kind = "pine" if v < 0.28 else "dead"      # what it looks like


class Prop:
    __slots__ = ("x", "y", "v", "kind")

    def __init__(self, x, y, v, kind):
        self.x, self.y, self.v, self.kind = x, y, v, kind


class Forest:
    def __init__(self, w, h, trees, lanterns, props, start, grass=(), glades=(), ponds=()):
        self.w, self.h, self.trees, self.lanterns, self.props, self.start = w, h, trees, lanterns, props, start
        self.ponds = list(ponds)                          # (x, y, radius): still pools of water (scenery, you can wade through)
        self.glades = list(glades)                        # (x, y, kind): clearings, each with one landmark
        self.grass = list(grass)                          # ground cover: tufts of dead grass
        self._cells = {}                                  # grid of trees for fast collision tests
        for t in trees:
            self._cells.setdefault((int(t.x), int(t.y)), []).append(t)

    def trees_near(self, x, y):
        cx, cy = int(x), int(y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                yield from self._cells.get((cx + dx, cy + dy), ())

    def resolve_move(self, x, y):
        """Slide the player (a circle) round tree trunks (circles): no invisible walls."""
        for _ in range(2):
            for t in self.trees_near(x, y):
                dx, dy = x - t.x, y - t.y
                d = math.hypot(dx, dy)
                m = t.r + PLAYER_R
                if d < m:
                    nx, ny = (dx / d, dy / d) if d > 1e-4 else (1.0, 0.0)
                    x, y = t.x + nx * m, t.y + ny * m
        return min(max(x, 1.0), self.w - 1.0), min(max(y, 1.0), self.h - 1.0)


def build_forest(cfg, seed=None, attempt=0):
    seed = cfg["seed"] if seed is None else seed
    rnd = random.Random(seed)
    w, h = cfg["w"], cfg["h"]
    trees = []
    add = lambda x, y, r: trees.append(Tree(x, y, r, rnd.random()))

    for i in range(w):                                    # edge ring
        add(i + 0.5, 0.5, 0.35)
        add(i + 0.5, h - 0.5, 0.35)
    for j in range(1, h - 1):
        add(0.5, j + 0.5, 0.35)
        add(w - 0.5, j + 0.5, 0.35)
    ring = len(trees)

    ph = [rnd.random() * 6.28 for _ in range(3)]          # smooth "how dense is the wood here" field
    def density(x, y):
        v = 0.5 + 0.25 * math.sin(x * 0.35 + ph[0]) * math.cos(y * 0.3 + ph[1]) + 0.25 * math.sin((x + y) * 0.2 + ph[2])
        return min(1.0, max(0.0, v))

    start = (2.5, 2.5)
    grid = {}                                             # spatial hash so placing trees stays fast
    def near(x, y, rad):
        cx, cy = int(x), int(y)
        k = int(rad) + 1
        for gx in range(cx - k, cx + k + 1):
            for gy in range(cy - k, cy + k + 1):
                for t in grid.get((gx, gy), ()):
                    yield t
    for t in trees:
        grid.setdefault((int(t.x), int(t.y)), []).append(t)

    glades, gl = [], random.Random(seed + 31)             # clearings with a landmark each. Own random stream, so trees elsewhere are unaffected.
    for _ in range(600):
        if len(glades) >= cfg.get("glades", 3):
            break
        gx, gy = 6 + gl.random() * (w - 12), 6 + gl.random() * (h - 12)
        if math.hypot(gx - start[0], gy - start[1]) < 12 or any(math.hypot(gx - a, gy - b) < 12 for a, b, _ in glades):
            continue
        glades.append((gx, gy, ("shrine", "stones", "ring")[len(glades) % 3]))
    gr = cfg.get("glade_radius", 3.3)

    tries = 0
    while len(trees) - ring < cfg["max_trees"] and tries < 30000:
        tries += 1
        x, y = 1.5 + rnd.random() * (w - 3), 1.5 + rnd.random() * (h - 3)
        if math.hypot(x - start[0], y - start[1]) < cfg["clear_radius"]:
            continue
        if any(math.hypot(x - a, y - b) < gr for a, b, _ in glades):
            continue
        gap = cfg["spacing_open"] + (cfg["spacing_dense"] - cfg["spacing_open"]) * density(x, y)
        if all(math.hypot(t.x - x, t.y - y) >= gap for t in near(x, y, gap)):
            t = Tree(x, y, 0.2 + rnd.random() * 0.1, rnd.random())
            trees.append(t)
            grid.setdefault((int(x), int(y)), []).append(t)

    pick = random.Random(7 + seed)                        # lanterns: far from the start and from each other, clear of trees
    lanterns = []
    for _ in range(8000):
        if len(lanterns) >= cfg["lanterns"]:
            break
        x, y = 2 + pick.random() * (w - 4), 2 + pick.random() * (h - 4)
        if math.hypot(x - start[0], y - start[1]) < cfg["min_start_distance"]:
            continue
        if any(math.hypot(t.x - x, t.y - y) < t.r + 0.8 for t in near(x, y, 2)):
            continue
        if any(math.hypot(x - a, y - b) < 2.4 for a, b, _ in glades):
            continue
        if any(math.hypot(lx - x, ly - y) < cfg["min_spacing"] for lx, ly in lanterns):
            continue
        lanterns.append((x, y))
    if len(lanterns) < cfg["lanterns"]:
        if attempt > 20:
            raise RuntimeError("Could not place the lanterns. Reduce lanterns or distances in config.py.")
        return build_forest(cfg, seed + 1, attempt + 1)
    lanterns.sort(key=lambda p: math.hypot(p[0] - start[0], p[1] - start[1]))

    dec = random.Random(seed + 99)                        # scenery for atmosphere: gravestones, rocks, mushrooms
    props = []
    for _ in range(5000):
        if len(props) >= w * h * 0.07:
            break
        x, y, k = 1.5 + dec.random() * (w - 3), 1.5 + dec.random() * (h - 3), dec.random()
        if math.hypot(x - start[0], y - start[1]) < 2:
            continue
        if any(math.hypot(t.x - x, t.y - y) < t.r + 0.6 for t in near(x, y, 2)):
            continue
        if any(math.hypot(lx - x, ly - y) < 1.2 for lx, ly in lanterns):
            continue
        if any(math.hypot(x - a, y - b) < 1.8 for a, b, _ in glades):
            continue
        props.append(Prop(x, y, dec.random(), "grave" if k < 0.22 else "rock" if k < 0.5 else "mush" if k < 0.72 else "log" if k < 0.88 else "stump"))

    grass = []                                            # dense dead grass, so the ground has texture and a sense of movement
    for _ in range(int(w * h * 3.2)):
        x, y = 1.2 + dec.random() * (w - 2.4), 1.2 + dec.random() * (h - 2.4)
        if any(math.hypot(t.x - x, t.y - y) < t.r + 0.1 for t in near(x, y, 1)):
            continue
        grass.append(Prop(x, y, dec.random(), "grass"))
    ponds, pr = [], random.Random(seed + 57)               # scenery only: pools placed where no tree stands, so trees and lanterns are unchanged
    for _ in range(3000):
        if len(ponds) >= cfg.get("ponds", 3):
            break
        x, y, rad = 4 + pr.random() * (w - 8), 4 + pr.random() * (h - 8), 1.0 + pr.random() * 0.7
        if math.hypot(x - start[0], y - start[1]) < 5 or any(math.hypot(x - a, y - b) < 4.5 for a, b, _ in glades):
            continue
        if any(math.hypot(x - a, y - b) < 5 for a, b, _ in ponds) or any(math.hypot(lx - x, ly - y) < rad + 1.5 for lx, ly in lanterns):
            continue
        if any(math.hypot(t.x - x, t.y - y) < rad + 0.7 for t in near(x, y, 3)):
            continue
        ponds.append((x, y, rad))
    props = [p for p in props if not any(math.hypot(p.x - a, p.y - b) < r + 0.5 for a, b, r in ponds)]
    for a, b, kind in glades:
        props.append(Prop(a, b, 0.5, kind))                # the landmark stands in the middle of its glade
    return Forest(w, h, trees, lanterns, props, start, grass, glades, ponds)
