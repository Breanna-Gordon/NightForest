"""Night Forest (study build): a first-person research prototype in Pygame.

Run on a computer:   python main.py           (optionally: python main.py P03)
Run in a browser:    pygbag .

Flow (the researcher runs it, the participant plays):
  setup  -> researcher types the participant ID (P01, P02, ...). The HUD order and map order come from the
            counterbalancing table in config.SCHEDULE. The participant never chooses the condition.
  brief  -> participant sees the story, goal and controls (identical in both conditions). P = practice, Enter = start.
  play   -> one recorded round (HUD shown or hidden, on map A or B).
  end    -> stats. The researcher gives the post-test questionnaires here, then presses Enter.
  (round 2 repeats brief/play/end with the other HUD condition and the other map)  ->  done.

main.py is written as an async loop so the same file works with pygbag."""
import asyncio
import datetime
import sys

import pygame

from game import config as C
from game import hud as HUD
from game.audio import Audio
from game.logger import Logger
from game.mapgen import build_forest
from game.render import Renderer
from game.world import World

ROUNDS = 2
STORY = ["The village lanterns have been stolen and the forest has gone dark.",
         "Find all {n} lanterns before the shadow wears you down.",
         "The shadow is slow, but it never stops."]
HUD_NAME = {"full": "Full on-screen HUD", "world": "HUD built into the world"}   # researcher-only labels


def wrap(msg, font, width):
    lines, cur = [], ""
    for word in msg.split():
        t = (cur + " " + word).strip()
        if font.size(t)[0] > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = t
    return lines + [cur] if cur else lines


def participant_number(pid):
    digits = "".join(ch for ch in pid if ch.isdigit())
    return int(digits) if digits else 1


class App:
    def __init__(self, screen):
        self.screen = screen
        self.pid = sys.argv[1] if len(sys.argv) > 1 else ""      # blank: the researcher types it on the setup screen
        self.forests = {}                                   # built once each: maps A, B and the practice map P
        for name, seed in C.MAP_SEEDS.items():
            cfg = dict(C.MAP)
            cfg["seed"] = seed
            self.forests[name] = build_forest(cfg)
        self.renderer = Renderer(screen)
        self.audio = Audio()
        self.log = Logger(C.LOG_ROUNDS)
        self.state = "setup"                                # setup | brief | play | end | done
        self.rnd = 0                                        # 0 = round 1, 1 = round 2
        self.schedule = C.SCHEDULE[0]
        self.world = None
        self.practice = False
        self.mouse_look = False
        self.started = ""
        self.t = 0.0
        self.backdrop = World(self.forests["P"], "full", practice=True)
        self.keys_override = None                           # used by automatic tests
        self.set_participant(self.pid)

    # ---- participant / condition handling
    def set_participant(self, pid):
        self.pid = pid
        self.schedule = C.SCHEDULE[(participant_number(self.pid) - 1) % len(C.SCHEDULE)]
        self.rnd = 0

    def cond(self):                                         # (hud, map) of the current round
        return self.schedule[self.rnd]

    def order_label(self):
        return ">".join(h for h, _ in self.schedule)        # e.g. full>none

    # ---- input
    def pressed(self, *keys):
        k = self.keys_override if self.keys_override is not None else pygame.key.get_pressed()
        return any(k[x] for x in keys)

    def handle_event(self, e):
        if e.type != pygame.KEYDOWN:
            return
        if e.key == pygame.K_o:
            self.audio.toggle()
            return
        if self.state == "setup":
            if e.key == pygame.K_RETURN and self.pid.strip():
                self.set_participant(self.pid.strip())
                self.state = "brief"
            elif e.key == pygame.K_BACKSPACE:
                self.pid = self.pid[:-1]
            elif e.unicode and e.unicode.isprintable() and len(self.pid) < 8 and e.key != pygame.K_RETURN:
                self.pid += e.unicode.upper()
        elif self.state == "brief":
            if e.key == pygame.K_m:
                self.toggle_mouse()
            elif e.key == pygame.K_p:
                self.start(True)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start(False)
            elif e.key == pygame.K_F2:                      # researcher: back to setup (change participant)
                self.pid = ""
                self.state = "setup"
        elif self.state == "play":
            if e.key == pygame.K_m:
                self.toggle_mouse()
            elif e.key == pygame.K_ESCAPE:                  # abandon the round (recorded as "abandoned" so it is not lost)
                self.release_mouse()
                w = self.world
                if not self.practice:
                    w.result = "abandoned"
                    self.log_round(w)
                self.state = "brief"
        elif self.state == "end":
            if e.key == pygame.K_r and self.practice:
                self.start(True)
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.practice:
                    self.state = "brief"
                elif self.rnd + 1 < ROUNDS:
                    self.rnd += 1
                    self.state = "brief"
                else:
                    self.state = "done"
        elif self.state == "done":
            if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.pid = ""
                self.state = "setup"

    def toggle_mouse(self):
        self.mouse_look = not self.mouse_look
        pygame.mouse.set_visible(not self.mouse_look)
        pygame.event.set_grab(self.mouse_look)
        pygame.mouse.get_rel()

    def release_mouse(self):
        if self.mouse_look:
            self.mouse_look = False
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

    def start(self, practice):
        hud, mp = self.cond()
        self.practice = practice
        forest = self.forests["P" if practice else mp]      # practice always uses its own map
        self.renderer.set_forest(forest)
        self.world = World(forest, hud, practice)           # practice shows the HUD condition of the coming round
        self.state = "play"
        self.started = datetime.datetime.now().isoformat(timespec="seconds")
        self.audio.start_ambience()
        pygame.mouse.get_rel()

    def log_round(self, w):
        hud, mp = self.cond()
        row = w.log_row(self.pid)
        row.update(startedAt=self.started, round=self.rnd + 1, order=self.order_label(), map=mp)
        self.log.record(row)

    # ---- one frame
    def update(self, dt):
        self.t += dt
        if self.state in ("setup", "brief", "done"):
            self.backdrop.pa = self.t * 0.12
            self.backdrop.bob += dt * 0.8
        elif self.state == "play":
            w = self.world
            ctl = dict(
                fwd=(1 if self.pressed(pygame.K_w, pygame.K_UP) else 0) - (1 if self.pressed(pygame.K_s, pygame.K_DOWN) else 0),
                strafe=(1 if self.pressed(pygame.K_e) else 0) - (1 if self.pressed(pygame.K_q) else 0),
                turn=((1 if self.pressed(pygame.K_d, pygame.K_RIGHT) else 0) - (1 if self.pressed(pygame.K_a, pygame.K_LEFT) else 0)) * C.TURN_SPEED,
                sprint=self.pressed(pygame.K_LSHIFT, pygame.K_RSHIFT),
                mouse_turn=pygame.mouse.get_rel()[0] * C.MOUSE_SENSITIVITY if self.mouse_look else 0.0,
            )
            w.update(dt, ctl)
            self.audio.whisper(w.shadow_close ** 1.4 * 0.55 if "cold" in w.flags else 0.0)
            for name, vol, pan in w.events:
                self.audio.play(name, vol, pan)
            w.events.clear()
            self.audio.ambient(dt)
            if w.phase != "play":
                if not getattr(w, "_logged", False):
                    w._logged = True
                    if not self.practice:
                        self.log_round(w)
                if w.phase == "won" and w.fin_t < 2.8:      # the forest lights up before the end screen
                    return
                self.release_mouse()
                self.state = "end"

    # ---- drawing
    def veil(self, a):
        W, H = self.screen.get_size()
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((2, 4, 10, a))
        self.screen.blit(v, (0, 0))

    def draw_backdrop(self, veil=150):
        r = self.renderer
        r.set_forest(self.forests["P"])
        r.draw_world(self.backdrop, self.t)
        r.present(self.backdrop, self.t, hud_on=False)
        self.veil(veil)

    def draw(self):
        r, s, F = self.renderer, self.screen, self.renderer.fonts
        W, H = s.get_size()
        if self.state == "setup":
            self.draw_backdrop(190)
            HUD.text(s, F["l"], "RESEARCHER SETUP", (W // 2, 40), (255, 169, 77), "midtop")
            HUD.text(s, F["s"], "This screen is for the researcher. Set it up before the participant sits down.", (W // 2, 92), (170, 180, 205), "midtop", False)
            HUD.panel(s, pygame.Rect(W // 2 - 260, 130, 520, 70), 210)
            HUD.text(s, F["s"], "Participant ID (type, then Enter)", (W // 2 - 240, 140), (150, 165, 195), shadow=False)
            cur = "_" if int(self.t * 2) % 2 == 0 else " "
            HUD.text(s, F["l"], self.pid + cur, (W // 2 - 240, 160), (235, 238, 248))
            sched = C.SCHEDULE[(participant_number(self.pid) - 1) % len(C.SCHEDULE)]
            HUD.panel(s, pygame.Rect(W // 2 - 260, 222, 520, 150), 190)
            HUD.text(s, F["s"], "Counterbalanced order for this participant:", (W // 2 - 240, 234), (150, 165, 195), shadow=False)
            for i, (hd, mp) in enumerate(sched):
                HUD.text(s, F["m"], f"Round {i + 1}:  {HUD_NAME[hd]}   on map {mp}", (W // 2 - 240, 264 + i * 36), (255, 214, 160))
            HUD.text(s, F["s"], "Post-test questionnaires after EACH round. Pre-test (demographics) once, before Round 1.", (W // 2 - 240, 338), (200, 205, 220), shadow=False)
            HUD.text(s, F["s"], "Participant number n uses row (n-1) mod 4 of the counterbalancing table in config.py.", (W // 2, H - 60), (130, 145, 175), "midtop", False)
        elif self.state in ("brief", "done"):
            self.draw_backdrop(165)
            HUD.text(s, F["xl"], "NIGHT FOREST", (W // 2, 30), (225, 228, 240), "midtop")
            if self.state == "done":
                HUD.text(s, F["l"], "Thank you for playing", (W // 2, 190), (235, 238, 248), "midtop")
                HUD.text(s, F["m"], "Please tell the researcher you have finished.", (W // 2, 250), (190, 200, 222), "midtop")
                HUD.text(s, F["s"], "Researcher: Enter returns to setup for the next participant.", (W // 2, H - 40), (130, 145, 175), "midtop", False)
                return
            y = 84
            for line in STORY:
                HUD.text(s, F["m"], line.format(n=C.MAP["lanterns"]), (W // 2, y), (200, 208, 230), "midtop")
                y += 30
            hud, _ = self.cond()
            HUD.panel(s, pygame.Rect(W // 2 - 330, 184, 660, 92), 170)
            HUD.text(s, F["m"], f"Round {self.rnd + 1} of {ROUNDS}", (W // 2, 190), (255, 214, 160), "midtop")
            for k, line in enumerate(["W / S  walk     A / D  turn     Q / E  sidestep     Hold Shift  sprint (you get out of breath)",
                                      "M  mouse look     O  sound on / off     Your torch shrinks when the shadow is near."]):
                HUD.text(s, F["s"], line, (W // 2, 222 + k * 22), (220, 225, 238), "midtop", False)
            ly = 292
            HUD.text(s, F["s"], "In this round the game tells you:", (W // 2 - 330, ly), (255, 214, 160), shadow=False)
            ly += 24
            for item in HUD.LEGEND[hud]:
                for j, seg in enumerate(wrap(item, F["s"], 640)):
                    HUD.text(s, F["s"], ("-  " if j == 0 else "    ") + seg, (W // 2 - 330, ly), (205, 212, 230), shadow=False)
                    ly += 20
            HUD.text(s, F["m"], "P  practice round (not recorded)          Enter  begin Round " + str(self.rnd + 1), (W // 2, H - 100), (255, 214, 160), "midtop")
            HUD.text(s, F["s"], "Headphones recommended.   Researcher: F2 returns to setup.", (W // 2, H - 56), (130, 145, 175), "midtop", False)
        else:
            w = self.world
            r.draw_world(w, w.t)
            r.present(w, w.t, hud_on=self.state != "end")
            if self.state == "play" and w.t < 9:                   # control reminder (same in every condition)
                a = int(255 * min(1, (9 - w.t) / 2))
                tip = F["s"].render("W/S walk   A/D turn   Q/E sidestep   Hold Shift to sprint   M: mouse look", True, (210, 215, 230))
                tip.set_alpha(a)
                s.blit(tip, tip.get_rect(midbottom=(W // 2, H - 84)))
            if self.state == "end":
                self.veil(185)
                won = w.phase == "won"
                title, sub = {"won": ("The forest is lit again", "Every lantern is home. The shadow has gone."),
                              "caught": ("The shadow found you", "Your light failed before all the lanterns were home."),
                              "timeUp": ("The night ran out", "The shadow is still out there.")}["won" if won else w.result if w.result in ("caught", "timeUp") else "timeUp"]
                HUD.text(s, F["l"], title, (W // 2, 22), (255, 224, 170) if won else (235, 238, 248), "midtop")
                HUD.text(s, F["m"], sub, (W // 2, 76), (190, 200, 222), "midtop", False)
                HUD.draw_recap(s, w, pygame.Rect(40, 118, 510, 340), F)
                px0 = 580
                HUD.panel(s, pygame.Rect(px0, 118, 340, 340), 205)
                HUD.text(s, F["s"], f"Lanterns found: {w.found} of {w.total}", (px0 + 16, 130), (255, 214, 160), shadow=False)
                for i in range(w.total):
                    HUD.draw_lantern_icon(s, px0 + 34 + i * 54, 188, i < w.found)
                stats = [("Time", f"{w.t:.0f} s"), ("Shadow hits", f"{w.hits}"), ("Distance walked", f"{w.dist:.0f} tiles"), ("Health left", f"{max(0, w.health):.0f}%")]
                for k, (lab, val) in enumerate(stats):
                    y = 240 + k * 40
                    HUD.text(s, F["m"], lab, (px0 + 16, y), (170, 185, 210), shadow=False)
                    HUD.text(s, F["m"], val, (px0 + 324, y), (235, 238, 248), "topright", False)
                    pygame.draw.line(s, (60, 70, 92), (px0 + 16, y + 32), (px0 + 324, y + 32), 1)
                if self.practice:
                    foot = "Practice round (not recorded).   R: practice again    Enter: continue"
                    HUD.text(s, F["s"], foot, (W // 2, H - 64), (160, 172, 198), "midtop", False)
                else:
                    HUD.text(s, F["m"], f"Round {self.rnd + 1} of {ROUNDS} complete. Please tell the researcher.", (W // 2, H - 76), (255, 214, 160), "midtop")
                    HUD.text(s, F["s"], "Researcher: give the post-round questionnaire, then press Enter.", (W // 2, H - 42), (160, 172, 198), "midtop", False)


async def main():
    pygame.init()
    pygame.display.set_caption(C.TITLE)
    screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
    clock = pygame.time.Clock()
    app = App(screen)
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and app.state in ("setup", "done"):
                running = False
            else:
                app.handle_event(e)
        dt = min(0.05, clock.tick(C.FPS) / 1000)
        app.update(dt)
        app.draw()
        pygame.display.flip()
        await asyncio.sleep(0)                          # lets the browser breathe (needed by pygbag)
    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
