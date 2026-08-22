"""Save / load screen: named slots from the title screen or in-game."""
import os

import pygame

from tbb.rules import persistence as Persist
from tbb.app.ui import draw_panel, draw_text, Button, SCREEN_W, SCREEN_H


class SaveScreen:
    def __init__(self, app):
        self.app = app
        self.mode = "load"   # "load" | "save"
        self.slots = []
        self.selected = None
        self.name = ""
        self.hint = ""
        self._buttons = []

    def refresh(self):
        self.slots = Persist.list_slots()
        self._buttons = self._make_buttons()
        if self.selected is not None and self.selected not in self.slots:
            self.selected = None

    # ------------------------------------------------------------ actions
    def do_save(self):
        if self.app.campaign is None:
            self.hint = "no game in progress"
            return
        name = (self.name.strip() or self.selected or "autosave").strip()
        if not name:
            name = "autosave"
        try:
            Persist.save(self.app.campaign, name)
            self.hint = "saved to %s" % name
            self.selected = name
            self.name = ""
            self.refresh()
            self.app.audio.sfx("click")
        except Exception as e:
            self.hint = "save failed: %s" % e

    def do_load(self):
        name = self.name.strip() or self.selected
        if not name:
            self.hint = "type or pick a slot"
            return
        try:
            camp = Persist.load(name)
        except Exception as e:
            camp = None
            self.hint = "load failed: %s" % e
        if camp is not None:
            self.app.campaign = camp
            self.app.campaign_screen.load(camp)
            self.app.settlement_screen.load(camp, (camp.player.settlement_ids
                                                   or [None])[0])
            self.app.found_mode = False
            self.app.mode = "campaign"
            self.app.campaign_screen.hint = "Loaded from '%s'" % name
            self.app.audio.sfx("click")

    def do_delete(self):
        if not self.selected:
            self.hint = "pick a slot first"
            return
        Persist.delete(self.selected)
        self.selected = None
        self.refresh()
        self.hint = "deleted"

    def do_back(self):
        self.app.mode = "title" if self.app.campaign is None else "campaign"
        self.app.audio.sfx("close")

    # ------------------------------------------------------------- events
    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._name_rect().collidepoint(ev.pos):
                return
            self._buttons = self._make_buttons()
            for b in self._buttons:
                if b.hit(ev.pos[0], ev.pos[1]):
                    b.on_click()
                    return
            # click a slot row
            row = self._slots_row(ev.pos)
            if row is not None:
                self.selected = self.slots[row]
                return
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_BACKSPACE:
                if self.name:
                    self.name = self.name[:-1]
                else:
                    self.selected = None
                    self.app.mode = "title" if self.app.campaign is None else \
                        "campaign"
                return
            if ev.key == pygame.K_ESCAPE:
                self.do_back()
                return
            if ev.key == pygame.K_RETURN:
                if self.mode == "save":
                    self.do_save()
                elif self.selected or self.name.strip():
                    self.do_load()
                return
            if ev.unicode and len(self.name) < 24 and \
                    (ev.unicode.isalnum() or ev.unicode in "_-"):
                self.name += ev.unicode

    # -------------------------------------------------------------- makes
    def _name_rect(self):
        return pygame.Rect(80, 220, 320, 30)

    def _make_buttons(self):
        x, y = 60, 300
        items = []
        if self.mode == "save":
            items.append(("Save to slot", self.do_save))
        else:
            items.append(("Load slot", self.do_load))
        items += [("Delete slot", self.do_delete), ("Back", self.do_back)]
        out = []
        for label, cb in items:
            out.append(Button(x, y, 160, 30, label, cb))
            y += 36
        return out

    def _slots_row_rect(self, i):
        return pygame.Rect(24, 92 + i * 30, 520, 26)

    def _slots_row(self, pos):
        y = pos[1]
        if 92 <= y < 92 + len(self.slots) * 30:
            return (y - 92) // 30
        return None

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        draw_panel(surf, 0, 0, SCREEN_W, SCREEN_H)
        f = self.app.fonts
        draw_text(surf, f["big"], "Save / Load", 24, 20, (40, 26, 14))
        draw_text(surf, f["small"],
                  "Save the game" if self.mode == "save" else
                  "Choose a slot to load", 24, 60, (90, 70, 40))
        rect = self._name_rect()
        pygame.draw.rect(surf, (240, 226, 190), rect)
        pygame.draw.rect(surf, (80, 50, 28), rect, 2)
        draw_text(surf, f["small"], self.name, rect.x + 6, rect.y + 12)
        for i, name in enumerate(self.slots):
            row = self._slots_row_rect(i)
            if name == self.selected:
                pygame.draw.rect(surf, (170, 150, 110), row)
            pygame.draw.rect(surf, (92, 60, 34), row, 1)
            draw_text(surf, f["small"], name, row.x + 6, row.y + 10,
                      (30, 20, 12))
        self._buttons = self._make_buttons()
        for b in self._buttons:
            b.draw(surf, f["small"])
        if self.hint:
            draw_text(surf, f["small"], self.hint, 24, SCREEN_H - 40,
                      (150, 40, 30))
