"""Night Forest (pilot build): a first-person research prototype in Pygame.

Run on a computer:   python main.py            (or python main.py P03 to set the participant ID)
Run in a browser:    pygbag .                  (see README.md)

main.py is written as an async loop so the same file works with pygbag."""
import asyncio
import datetime
import math
import sys

import pygame

from game import config as C
from game import hud as HUD
from game.audio import Audio
from game.logger import Logger
from game.mapgen import build_forest
from game.render import Renderer
from game.world import World

MODES = ["none", "full", "world"]


class App:
    def __init__(self, screen):
        self.screen = screen
        self.pid = sys.argv[1] if len(sys.argv) > 1 else C.PARTICIPANT_ID
        self.forest = build_forest(C.MAP)                 # the same forest for every round
        self.renderer = Renderer(screen)
        self.renderer.set_forest(self.forest)
        self.audio = Audio()
        self.log = Logger(C.LOG_ROUNDS)
        self.state = "menu"                               # menu | play | end
        self.sel = 0                                      # selected HUD condition in the menu
        self.world = None
        self.practice = False
        self.mouse_look = False
        self.started = ""
        self.t = 0.0
        self.backdrop = World(self.forest, "none", practice=True)
        self.keys_override = None                         # used by automatic tests

    # ------------------------------------------------------------------ input
    def pressed(self, *keys):
        k = self.keys_override if self.keys_override is not None else pygame.key.get_pressed()
        return any(k[x] for x in keys)

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_m:                       # mouse look on/off
                self.mouse_look = not self.mouse_look
                pygame.mouse.set_visible(not self.mouse_look)
                pygame.event.set_grab(self.mouse_look)
                pygame.mouse.get_rel()
            elif e.key == pygame.K_o:
                self.audio.toggle()
            elif self.state == "menu":
                if e.key in (pygame.K_UP, pygame.K_w):
                    self.sel = (self.sel - 1) % 3
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    self.sel = (self.sel + 1) % 3
                elif e.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    self.sel = e.key - pygame.K_1
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.start(False)
                elif e.key == pygame.K_p:
                    self.start(True)
            elif self.state == "play":
                if e.key == pygame.K_ESCAPE:
                    self.back_to_menu()
            elif self.state == "end":
                if e.key == pygame.K_r:
                    self.start(self.practice)
                elif e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_SPACE):
                    self.back_to_menu()

    def start(self, practice):
        self.practice = practice
        self.world = World(self.forest, MODES[self.sel], practice)
        self.state = "play"
        self.started = datetime.datetime.now().isoformat(timespec="seconds")
        self.audio.start_ambience()
        pygame.mouse.get_rel()

    def back_to_menu(self):
        self.state = "menu"
        if self.mouse_look:
            self.mouse_look = False
            pygame.mouse.set_visible(True)
            pygame.event.set_grab(False)

    # ------------------------------------------------------------------ one frame
    def update(self, dt):
        self.t += dt
        if self.state == "menu":
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
            for name, vol, pan in w.events:
                self.audio.play(name, vol, pan)
            w.events.clear()
            if w.phase != "play":
                self.state = "end"
                if not self.practice:
                    row = w.log_row(self.pid)
                    row["startedAt"] = self.started
                    self.log.record(row)

    def draw(self):
        r, s, F = self.renderer, self.screen, self.renderer.fonts
        W, H = s.get_size()
        if self.state == "menu":
            r.draw_world(self.backdrop, self.t)
            r.present(self.backdrop, self.t, hud_on=False)
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((2, 4, 10, 150))
            s.blit(veil, (0, 0))
            HUD.text(s, F["xl"], "NIGHT FOREST", (W // 2, 34), (225, 228, 240), "midtop")
            HUD.text(s, F["m"], "Find the lanterns. Don't let the shadow wear you down.", (W // 2, 104), (170, 180, 205), "midtop")
            y = 150
            for i, m in enumerate(MODES):
                rect = pygame.Rect(W // 2 - 230, y, 460, 44)
                HUD.panel(s, rect, 210 if i == self.sel else 110)
                if i == self.sel:
                    pygame.draw.rect(s, (255, 169, 77), rect, 2, border_radius=8)
                HUD.text(s, F["m"], f"{i + 1}   {C.HUD_LABELS[m]}", (rect.x + 20, rect.y + 11), (255, 214, 160) if i == self.sel else (200, 205, 220))
                y += 52
            HUD.panel(s, pygame.Rect(W // 2 - 330, y + 2, 660, 142), 150)
            HUD.text(s, F["s"], "What you will see in this condition:", (W // 2 - 314, y + 16), (150, 165, 195), shadow=False)
            for k, line in enumerate(HUD.LEGEND[MODES[self.sel]]):
                HUD.text(s, F["s"], "- " + line, (W // 2 - 314, y + 42 + k * 21), (220, 225, 238), shadow=False)
            HUD.text(s, F["s"], "Up/Down or 1-3: choose     Enter: start recorded round     P: practice (one lantern, no shadow, not recorded)", (W // 2, H - 58), (150, 165, 195), "midtop", False)
            HUD.text(s, F["s"], "W/S walk   A/D turn   Q/E sidestep   Shift sprint   M mouse look   O sound on/off   Esc back", (W // 2, H - 34), (150, 165, 195), "midtop", False)
        else:
            w = self.world
            r.draw_world(w, w.t)
            r.present(w, w.t, hud_on=True)
            if self.state == "play" and w.t < 9:                   # control reminder (same in every condition)
                a = int(255 * min(1, (9 - w.t) / 2))
                tip = F["s"].render("W/S walk   A/D turn   Q/E sidestep   Hold Shift to sprint   M: mouse look", True, (210, 215, 230))
                tip.set_alpha(a)
                s.blit(tip, tip.get_rect(midbottom=(W // 2, H - 84)))
            if self.state == "end":
                veil = pygame.Surface((W, H), pygame.SRCALPHA)
                veil.fill((2, 4, 10, 170))
                s.blit(veil, (0, 0))
                msg = "All lanterns found" if w.phase == "won" else ("The shadow drained your strength" if w.result == "caught" else "Time is up")
                HUD.text(s, F["xl"], msg, (W // 2, H // 2 - 130), (235, 238, 248), "midtop")
                HUD.panel(s, pygame.Rect(W // 2 - 220, H // 2 - 30, 440, 130), 190)
                lines = [f"Lanterns found: {w.found} / {w.total}", f"Time: {w.t:.0f} s", f"Shadow hits: {w.hits}"]
                for k, l in enumerate(lines):
                    HUD.text(s, F["m"], l, (W // 2 - 190, H // 2 - 14 + k * 36), (220, 226, 238))
                note = "Practice round (not recorded)" if self.practice else "Round recorded"
                HUD.text(s, F["s"], f"{note}.   R: play again    Enter: menu", (W // 2, H // 2 + 120), (160, 172, 198), "midtop", False)


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
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and app.state == "menu":
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
