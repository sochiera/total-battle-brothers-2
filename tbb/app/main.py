"""Total Battle Brothers - pygame application entry.

Screens: title, campaign, settlement, hex battle, save/load. Regulations live
in tbb.rules and are read-only through the Campaign object; presentation never
reaches into rules internals.
"""
import random

import pygame
from pathlib import Path

from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.app import audio, art
from tbb.app.campaign_screen import CampaignScreen
from tbb.app.settlement_screen import SettlementScreen
from tbb.app.battle_screen import BattleScreen
from tbb.app.save_screen import SaveScreen
from tbb.app.court_screen import CourtScreen
from tbb.app.ui import draw_text, Button, SCREEN_W, SCREEN_H


def generated_seed():
    """A fresh numeric campaign seed for the Generate button."""
    return random.randint(10000, 999999)


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
        return pygame.Rect(SCREEN_W // 2 - 110, 330, 170, 30)

    def _generate_rect(self):
        return pygame.Rect(SCREEN_W // 2 + 70, 330, 120, 30)

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

    def generate(self):
        self.seed_text = str(generated_seed())
        self.app.audio.sfx("click")

    def quit(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._generate_rect().collidepoint(ev.pos):
                self.generate()
                return
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
            elif ev.key == pygame.K_g:
                self.generate()
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
        draw_text(surf, f["small"], "Seed:", SCREEN_W // 2 - 160, 342,
                  (60, 70, 40))
        rect = self._seed_rect()
        pygame.draw.rect(surf, (240, 226, 190), rect)
        pygame.draw.rect(surf, (80, 50, 28), rect, 2)
        seed = self.seed_text or str(C.DEFAULT_SEED)
        draw_text(surf, f["small"], seed, rect.x + 6, rect.y + 12,
                  (30, 20, 12))
        gen = self._generate_rect()
        pygame.draw.rect(surf, (188, 140, 92), gen)
        pygame.draw.rect(surf, (60, 38, 24), gen, 2)
        gtext = "Generate (G)"
        tw = f["small"].size(gtext)[0]
        surf.blit(f["small"].render(gtext, True, (30, 20, 12)),
                  (gen.x + gen.w // 2 - tw // 2, gen.y + 12))
        for b in self._buttons():
            b.draw(surf, f["small"])
        draw_text(surf, f["small"],
                  "Type a seed or Generate - Enter starts. Arrows pan the map.",
                  SCREEN_W // 2 - 280, SCREEN_H - 80, (120, 110, 90))


class EpilogueScreen:
    """A full-window, unambiguous end to a campaign."""
    def __init__(self, app):
        self.app = app

    def handle(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self.app.mode = "title"

    def draw(self, surf):
        victory = self.app.campaign.end_reason == "victory"
        surf.fill((32, 48, 38) if victory else (55, 32, 30))
        colour = (220, 198, 126) if victory else (220, 116, 92)
        draw_text(surf, self.app.fonts["big"],
                  "VICTORY" if victory else "DEFEAT",
                  SCREEN_W // 2 - 120, 250, colour)
        draw_text(surf, self.app.fonts["med"],
                  ("The last ruling duchy endures." if victory else
                   "The ducal line is extinguished."),
                  SCREEN_W // 2 - 220, 315, (230, 220, 190))
        draw_text(surf, self.app.fonts["small"],
                  "Press Enter or Escape to return to the title screen.",
                  SCREEN_W // 2 - 220, 400, (190, 180, 160))


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
        self.epilogue_screen = EpilogueScreen(self)
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
        self.audio.sfx("open")

    def enter_court(self):
        self.court_screen.load(self.campaign)
        self.mode = "court"
        self.audio.sfx("open")

    def start_battle(self, battle):
        self.battle_screen.load(battle)
        self.mode = "battle"
        self.audio.sfx("open")

    def show_epilogue(self):
        if self.campaign is not None and self.campaign.ended:
            self.mode = "epilogue"
            self.audio.sfx("close")

    def finish_battle(self):
        self.battle_screen.battle = None
        if self.campaign is not None:
            self.campaign_screen.load(self.campaign)
        if self.campaign is not None and self.campaign.ended:
            self.show_epilogue()
        else:
            self.mode = "campaign"
            self.audio.sfx("close")

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
        elif self.mode == "epilogue":
            self.epilogue_screen.handle(ev)

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
        elif self.mode == "epilogue":
            self.epilogue_screen.draw(self.display)


def dump_frames(directory, seed=C.DEFAULT_SEED, ending="victory"):
    """Render title, campaign, settlement, court, battle and epilogue PNGs."""
    from tbb.rules import battle as battle_rules

    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    app = None
    try:
        app = App()

        def capture(name):
            pygame.display.flip()
            pygame.image.save(app.display, str(output / name))

        # Capture the real title screen as part of the public smoke.
        app._draw()
        capture("title.png")
        app.new_game(seed)

        app._draw()
        capture("campaign.png")

        app.mode = "settlement"
        app.settlement_screen.load(app.campaign,
                                   app.campaign.player.settlement_ids[0])
        app._draw()
        capture("settlement.png")

        app.enter_court()
        app._draw()
        capture("court.png")

        hero_party = app.campaign.hero_party(C.PLAYER_REALM_KEY)
        bandit_party = next(
            (party for party in app.campaign.parties
             if party.kind == "bandit" and
             party.alive_units(app.campaign.units)), None)
        battle = battle_rules.battle_from_contact(
            app.campaign, hero_party, bandit_party) if bandit_party else None
        if battle is None:
            raise RuntimeError("could not build a battle against a living robber party")
        app.start_battle(battle)
        # Keep the public battle PNG honest about ranged juice as well as the
        # melee/wound chrome: this is a short presentation sample, not a rule
        # action and therefore does not consume AP or RNG.
        ranged_unit = app.campaign.units[battle.sides["attacker"][0]]
        ranged_target = app.campaign.units[battle.sides["defender"][0]]
        app.battle_screen._fx_from_record({
            "kind": "ranged", "unit": ranged_unit.id,
            "target": ranged_target.id, "hit": False, "reason": "miss"})
        app._draw()
        capture("battle.png")

        app.campaign.ended = True
        app.campaign.end_reason = ending
        app.mode = "epilogue"
        app._draw()
        capture("epilogue.png")
    finally:
        if app is not None:
            app.audio.music_stop()
        pygame.quit()


if __name__ == "__main__":
    App().run()
