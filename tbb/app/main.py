"""Total Battle Brothers - pygame application entry.

Screens: title, campaign, settlement, hex battle, save/load. Regulations live
in tbb.rules and are read-only through the Campaign object; presentation never
reaches into rules internals.
"""
import pygame

from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.app import audio, art
from tbb.app.campaign_screen import CampaignScreen
from tbb.app.settlement_screen import SettlementScreen
from tbb.app.battle_screen import BattleScreen
from tbb.app.save_screen import SaveScreen
from tbb.app.court_screen import CourtScreen
from tbb.app.ui import draw_text, Button, SCREEN_W, SCREEN_H


def build_art():
    return {
        "terrain": art.terrain_sprites(),
        "settle": art.settlement_sprite_sheet(),
        "unit": art.unit_sprite_sheet(),
        "bandit": art.bandit_sprite(),
        "hero": art.hero_banner((255, 220, 120)),
        "banner": art.banner_sprites(),
        "ui": art.ui_chrome(),
    }


class TitleScreen:
    def __init__(self, app):
        self.app = app
        self.seed_text = ""
        self.msg = ""

    def _seed_rect(self):
        return pygame.Rect(SCREEN_W // 2 - 80, 330, 160, 30)

    def _buttons(self):
        x, y, w, h = SCREEN_W // 2 - 120, 400, 240, 40
        return [
            Button(x, y, w, h, "New Game", self._start),
            Button(x, y + 52, w, h, "Load Game",
                   lambda: self.app.enter_save(False)),
            Button(x, y + 104, w, h, "Quit", self.quit),
        ]

    def _seed(self):
        try:
            return int(self.seed_text) if self.seed_text else C.DEFAULT_SEED
        except ValueError:
            return C.DEFAULT_SEED

    def _start(self):
        self.app.new_game(self._seed())

    def quit(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._seed_rect().collidepoint(ev.pos):
                self.app.focus_seed = True
                return
            for b in self._buttons():
                if b.hit(ev.pos[0], ev.pos[1]):
                    b.on_click()
                    self.app.audio.sfx("click")
                    return
            self.app.focus_seed = False
        elif ev.type == pygame.KEYDOWN:
            if self.app.focus_seed and ev.key == pygame.K_RETURN:
                self._start()
            elif ev.key == pygame.K_RETURN:
                self._start()
            elif self.app.focus_seed:
                if ev.key == pygame.K_BACKSPACE:
                    self.seed_text = self.seed_text[:-1]
                elif ev.unicode and ev.unicode.isdigit():
                    self.seed_text += ev.unicode

    def draw(self, surf):
        import random as rng
        rng.seed(4)
        for y in range(0, SCREEN_H, 3):
            for x in range(0, SCREEN_W, 3):
                c = (58 + rng.randint(-4, 4), 48 + rng.randint(-4, 4),
                     34 + rng.randint(-2, 2))
                surf.fill(c, (x, y, 3, 3))
        f = self.app.fonts
        draw_text(surf, f["big"], "TOTAL BATTLE BROTHERS",
                  SCREEN_W // 2 - 280, 150, (206, 184, 144))
        draw_text(surf, f["small"],
                  "Grim medieval rule - no magic, only iron and wheat",
                  SCREEN_W // 2 - 250, 210, (150, 138, 120))
        draw_text(surf, f["small"], "Seed:", SCREEN_W // 2 - 130, 342,
                  (60, 70, 40))
        rect = self._seed_rect()
        pygame.draw.rect(surf, (240, 226, 190), rect)
        pygame.draw.rect(surf, (80, 50, 28), rect, 2)
        seed = self.seed_text or str(C.DEFAULT_SEED)
        draw_text(surf, f["small"], seed, rect.x + 6, rect.y + 12,
                  (30, 20, 12))
        for b in self._buttons():
            b.draw(surf, f["small"])
        draw_text(surf, f["small"],
                  "Arrows to pan the map - details in README.md",
                  SCREEN_W // 2 - 250, SCREEN_H - 80, (120, 110, 90))


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Total Battle Brothers")
        self.fonts = {
            "big": pygame.font.SysFont("dejavusans", 34),
            "med": pygame.font.SysFont("dejavusans", 24),
            "small": pygame.font.SysFont("dejavusans", 17),
        }
        self.audio = audio.AudioEngine()
        self.art = build_art()
        self.display = pygame.display.set_mode((SCREEN_W, SCREEN_H),
                                               pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()
        self.mode = "title"
        self.focus_seed = False
        self.found_mode = False
        self.campaign = None
        self.title_screen = TitleScreen(self)
        self.campaign_screen = CampaignScreen(self)
        self.settlement_screen = SettlementScreen(self)
        self.battle_screen = BattleScreen(self)
        self.save_screen = SaveScreen(self)
        self.court_screen = CourtScreen(self)
        self.audio.music_start()

    # ------------------------------------------------------------- flow
    def new_game(self, seed=None):
        if seed is None:
            seed = self.title_screen._seed()
        self.campaign = Campaign(seed)
        self.campaign_screen.load(self.campaign)
        self.settlement_screen.load(self.campaign,
                                    (self.campaign.player.settlement_ids
                                     or [None])[0])
        self.battle_screen.battle = None
        self.found_mode = False
        self.mode = "campaign"
        self.campaign_screen.hint = ("Your banner holds the realm. March the "
                                     "hero, build and staff holdings, keep "
                                     "wheat and gold - no magic, only iron.")
        self.audio.sfx("close")

    def enter_save(self, is_save):
        self.save_screen.refresh()
        self.save_screen.mode = "save" if is_save else "load"
        self.mode = "savegame"
        self.audio.sfx("click")

    def enter_court(self):
        self.court_screen.load(self.campaign)
        self.mode = "court"
        self.audio.sfx("click")

    def start_battle(self, battle):
        self.battle_screen.load(battle)
        self.mode = "battle"

    def finish_battle(self):
        self.battle_screen.battle = None
        if self.campaign is not None:
            self.campaign_screen.load(self.campaign)
        self.mode = "campaign"

    # --------------------------------------------------------------- loop
    def run(self, frames=None):
        running = True
        drawn = 0
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                else:
                    self._dispatch(ev)
            self._draw()
            pygame.display.flip()
            self.clock.tick(60)
            drawn += 1
            if frames is not None and drawn >= frames:
                running = False
        self.audio.music_stop()
        pygame.quit()

    def _dispatch(self, ev):
        if self.mode == "title":
            self.title_screen.handle(ev)
        elif self.mode == "savegame":
            self.save_screen.handle(ev)
        elif self.mode == "campaign":
            self.campaign_screen.handle(ev)
        elif self.mode == "settlement":
            self.settlement_screen.handle(ev)
        elif self.mode == "battle":
            self.battle_screen.handle(ev)
        elif self.mode == "court":
            self.court_screen.handle(ev)

    def _draw(self):
        if self.mode == "title":
            self.title_screen.draw(self.display)
        elif self.mode == "savegame":
            self.save_screen.draw(self.display)
        elif self.mode == "campaign":
            self.campaign_screen.draw(self.display)
        elif self.mode == "settlement":
            self.settlement_screen.draw(self.display)
        elif self.mode == "battle":
            self.battle_screen.draw(self.display)
        elif self.mode == "court":
            self.court_screen.draw(self.display)


if __name__ == "__main__":
    App().run()
