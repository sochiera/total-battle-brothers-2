"""Court screen: succession choice, pagination, and end-state banners."""
import pygame

from tbb.app.ui import draw_panel, draw_text, Button, SCREEN_W, SCREEN_H


class CourtScreen:
    PAGE_SIZE = 8

    def __init__(self, app):
        self.app = app
        self.campaign = None
        self.hint = ""
        self.page = 0

    def load(self, campaign):
        self.campaign = campaign
        self.hint = ""
        self.page = 0

    def _back(self):
        self.app.mode = "campaign"
        self.app.audio.sfx("close")

    def _do(self, result):
        self.hint = result.reason if not result.ok else "The succession rolls are amended."
        self.app.audio.sfx("click" if result.ok else "cant")

    def _clear(self):
        self._do(self.campaign.designate_heir(None))

    def _choose(self, uid):
        self._do(self.campaign.designate_heir(uid))

    def _candidates(self):
        realm = self.campaign.player
        return [u for u in realm.living_units(self.campaign.units)
                if u.id != realm.hero]

    def _buttons(self):
        candidates = self._candidates()
        start = self.page * self.PAGE_SIZE
        out = []
        for row, unit in enumerate(candidates[start:start + self.PAGE_SIZE]):
            out.append(Button(30, 165 + row * 38, 520, 32,
                              "Designate %s (%s, age %d)" %
                              (unit.name, unit.origin, unit.age),
                              lambda uid=unit.id: self._choose(uid)))
        y = 165 + self.PAGE_SIZE * 38 + 8
        if self.page > 0:
            out.append(Button(30, y, 150, 30, "Previous", self.previous_page))
        if start + self.PAGE_SIZE < len(candidates):
            out.append(Button(190, y, 150, 30, "Next", self.next_page))
        out.append(Button(350, y, 180, 30, "Clear heir", self._clear))
        out.append(Button(540, y, 180, 30, "Back to map", self._back))
        return out

    def next_page(self):
        if (self.page + 1) * self.PAGE_SIZE < len(self._candidates()):
            self.page += 1

    def previous_page(self):
        self.page = max(0, self.page - 1)

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self._buttons():
                if button.hit(*event.pos):
                    button.on_click()
                    return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._back()

    def draw(self, surface):
        surface.fill((52, 45, 35))
        draw_panel(surface, 80, 40, SCREEN_W - 160, SCREEN_H - 80)
        fonts, realm = self.app.fonts, self.campaign.player
        hero = self.campaign.units.get(realm.hero)
        heir = self.campaign.units.get(realm.heir) if realm.heir else None
        draw_text(surface, fonts["big"], "THE COURT", 120, 70, (50, 30, 15))
        draw_text(surface, fonts["med"], "Hero: %s" % (hero.name if hero else "none"),
                  120, 108)
        draw_text(surface, fonts["med"], "Heir: %s    Morale: %d" %
                  (heir.name if heir else "none", int(realm.morale)), 520, 108)
        draw_text(surface, fonts["small"],
                  "Choose a living non-hero soldier. This is the only heir screen.",
                  120, 135, (80, 55, 30))
        for button in self._buttons():
            button.draw(surface, fonts["small"])
        count = max(1, (len(self._candidates()) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        draw_text(surface, fonts["small"], "Page %d/%d" % (self.page + 1, count),
                  760, 730, (80, 60, 40))
        if self.hint:
            draw_text(surface, fonts["small"], self.hint, 120, 710, (120, 35, 25))
        if self.campaign.ended:
            banner = ("VICTORY — the last ruling duchy endures" if
                      self.campaign.end_reason == "victory" else
                      "DEFEAT — the ducal line is extinguished")
            draw_text(surface, fonts["big"], banner, 120, 350, (140, 28, 20))
