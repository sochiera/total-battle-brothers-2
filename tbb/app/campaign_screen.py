"""Campaign screen: the large hex world, parties, settlements, realm
resources, date, selected settlement/company, march actions, end-month."""
import pygame

from tbb.rules import constants as C
from tbb.rules import terrain as G
from tbb.app.ui import (hex_center, pick_hex, draw_panel, draw_text, Button,
                        PANEL_W, SCREEN_W, SCREEN_H, TS, realm_index)


def _f(n):
    return str(int(round(n))) if isinstance(n, float) else str(n)


class CampaignScreen:
    def __init__(self, app):
        self.app = app
        self.campaign = None
        self.map_surf = None
        self.ox, self.oy = 30, 20
        self.selected_pid = None
        self.selected_sid = None
        self.hint = ""
        self._buttons = []

    # ------------------------------------------------------------ loading
    def load(self, campaign):
        self.campaign = campaign
        self._build_map()
        self.selected_sid = (campaign.player.settlement_ids or [None])[0]

    def _build_map(self):
        cmap = self.campaign
        w, h = cmap.world.width, cmap.world.height
        self.map_w = int(TS * 1.72 * (w + h * 0.5)) + 400
        self.map_h = int(TS * 1.5 * h) + 300
        surf = pygame.Surface((self.map_w, self.map_h))
        t = self.app.art["terrain"]
        for (q, r), terr in cmap.world.grid.items():
            cx, cy = hex_center(q, r, ts=TS)
            img = t[terr]
            surf.blit(img, (cx - img.get_width() // 2,
                            cy - img.get_height() // 2))
        self.map_surf = surf

    # ------------------------------------------------------------ buttons
    def _make_buttons(self):
        x0 = SCREEN_W - PANEL_W + 12
        y = 150
        out = []
        pending = bool(self.campaign and self.campaign.pending_battles)
        items = [
            ("Press B: battle waits", self.resolve_battle, pending),
            ("End Month (M)", self.end_month, True),
            ("Open Settlement (O)", self.open_selected, True),
            ("Found a Village (F)", self.toggle_found, True),
            ("Save (S)", lambda: self.app.enter_save(True), True),
            ("Load (L)", lambda: self.app.enter_save(False), True),
            ("Return to Title (Esc)", self.to_title, True),
        ]
        for label, fn, enabled in items:
            out.append(Button(x0, y, PANEL_W - 24, 32, label, fn, enabled))
            y += 38
        return out

    # ------------------------------------------------------------ actions
    def _sel_size_ok(self):
        return True

    def end_month(self):
        c = self.campaign
        if c.pending_battles:
            self.resolve_battle()
            self.app.audio.sfx("cant")
            return
        res = c.end_turn()
        if not res.ok:
            self.hint = res.reason
            self.app.audio.sfx("cant")
            return
        self.app.audio.sfx("close")
        self.hint = "Month turned - %s" % res.reason
        if c.ended:
            self.hint = ("The realm has ended: %s" % c.end_reason)

    def resolve_battle(self):
        if not self.campaign.pending_battles:
            return
        b = self.campaign.pending_battles[0]
        self.app.start_battle(b)
        self.app.audio.sfx("click")

    def open_selected(self):
        c = self.app
        sid = self.selected_sid
        if sid is None:
            self.hint = "Select one of your settlements first"
            self.app.audio.sfx("cant")
            return
        h = self.campaign.settlements[sid]
        if h.owner != self.campaign.player.key:
            self.hint = "That is not your holding"
            self.app.audio.sfx("cant")
            return
        self.app.settlement_screen.load(self.campaign, sid)
        self.app.mode = "settlement"
        self.app.audio.sfx("click")

    def toggle_found(self):
        self.app.found_mode = not getattr(self.app, "found_mode", False)
        self.hint = (("Found mode ON - click empty plains beside your own "
                      "land") if self.app.found_mode else "Found mode off")
        self.app.audio.sfx("click")

    def to_title(self):
        self.app.mode = "title"
        self.app.audio.sfx("click")

    # -------------------------------------------------------------- events
    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in self._button_build():
                if b.hit(ev.pos[0], ev.pos[1]):
                    b.on_click()
                    return
            self._click_hex(ev.pos)
        elif ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_b:
                self.resolve_battle()
            elif k == pygame.K_m:
                self.end_month()
            elif k == pygame.K_o:
                self.open_selected()
            elif k == pygame.K_s:
                self.app.enter_save(True)
            elif k == pygame.K_l:
                self.app.enter_save(False)
            elif k == pygame.K_ESCAPE or k == pygame.K_q:
                self.selected_pid = None
                if self.app.found_mode:
                    self.app.found_mode = False
                else:
                    self.app.mode = "title"
            elif k in (pygame.K_LEFT, pygame.K_a):
                self.ox += 40
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.ox -= 40
            elif k in (pygame.K_UP, pygame.K_w):
                self.oy += 40
            elif k == pygame.K_DOWN:
                self.oy += 40

    def _button_build(self):
        self._buttons = self._make_buttons()
        return self._buttons

    def _click_hex(self, pos):
        c = self.campaign
        q, r = pick_hex(pos[0], pos[1], self.ox, self.oy)
        if not c.world.in_bounds((q, r)):
            return
        hexpos = (q, r)
        # march the selected hero company
        if self.selected_pid is not None:
            party = next((p for p in self.campaign.parties
                          if p.pid == self.selected_pid), None)
            if party is not None and tuple(party.hex) != hexpos:
                res = self.campaign.move_party(party.pid, hexpos)
                if res.ok:
                    self.app.audio.sfx("hit")
                    if self.campaign.pending_battles:
                        self.hint = "Contact! Press B for battle"
                else:
                    self.app.audio.sfx("cant")
                    self.hint = res.reason
                return
        if getattr(self.app, "found_mode", False):
            res = self.campaign.order_found(hexpos)
            if res.ok:
                self.hint = "A village is being seeded there"
                self.app.audio.sfx("close")
            else:
                self.app.audio.sfx("cant")
                self.hint = res.reason
            return
        # pick what stands there
        sid = self.campaign.settlement_id_at(hexpos)
        party = next((p for p in self.campaign.parties
                      if tuple(p.hex) == hexpos), None)
        if party is not None and party.realm == self.campaign.player.key \
                and party.kind == "hero":
            self.selected_pid = party.pid
            self.selected_sid = sid
            self.hint = ("Company of %d men, %d moves left - click an "
                         "adjacent hex to march"
                         % (party.size(), party.mp))
        elif sid is not None:
            self.selected_pid = None
            self.selected_sid = sid
            h = self.campaign.settlements[sid]
            self.hint = "%s (%s)%s" % (
                h.name, h.size,
                " - yours" if h.owner == self.campaign.player.key else
                (" - " + self.campaign.realms[h.owner].name
                 if h.owner is not None else " - free lands"))
        else:
            self.selected_pid = None
            self.hint = "empty %s" % self.campaign.world.terrain(hexpos)

    def _world_visible(self, hexpos):
        return True

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill((66, 70, 58))
        surf.blit(self.map_surf, (self.ox, self.oy))
        self._overlays(surf)
        draw_panel(surf, SCREEN_W - PANEL_W, 0, PANEL_W, SCREEN_H)
        self._panel(surf)
        for b in self._button_build():
            b.draw(surf, self.app.fonts["small"])
        if getattr(self.app, "found_mode", False):
            draw_text(surf, self.app.fonts["med"],
                      "FOUND MODE: pick empty plains", SCREEN_W - PANEL_W + 8,
                      118, (150, 40, 20))

    def _overlays(self, surf):
        c = self.campaign
        sf = self.app.fonts["small"]
        settle_art = self.app.art["settle"]
        for p in c.parties:
            cx, cy = hex_center(*p.hex, self.ox, self.oy)
            if p.kind == "bandit":
                # the robber bands are the sharpest trouble on the roads
                if p.unit_ids:
                    u = c.units[p.unit_ids[0]]
                    sp = self.app.art["unit"].get((6, u.kit, u.is_hero))
                    if sp:
                        surf.blit(sp, (cx - 8, cy - 10))
                pygame.draw.circle(surf, (160, 30, 20), (cx, cy - 12), 3)
                pygame.draw.circle(surf, (120, 20, 14), (cx, cy - 12), 5, 1)
                draw_text(surf, sf, "%d robbers" % len(p.unit_ids),
                          cx + 10, cy - 4, (30, 20, 12))
                continue
            if p.unit_ids:
                u = c.units[p.unit_ids[0]]
                si = realm_index(c, u.realm)
                sp = self.app.art["unit"].get((si, u.kit, u.is_hero))
                if sp:
                    surf.blit(sp, (cx - 8, cy - 10))
        # settlements
        for h in c.settlements.values():
            sxx, syy = hex_center(*h.hex, self.ox, self.oy)
            sector = realm_index(c, h.owner)
            sp = settle_art[(sector, h.size)]
            surf.blit(sp, (sxx - sp.get_width() // 2,
                           syy - sp.get_height() // 2))
        # hero banner + company counts
        for p in c.parties:
            if p.kind != "hero":
                continue
            cx, cy = hex_center(*p.hex, self.ox, self.oy)
            pygame.draw.circle(surf, (255, 240, 200), (cx, cy - 12), 3)
            draw_text(surf, sf, "%d" % len(p.unit_ids), cx + 8, cy + 8,
                      (30, 20, 12))
        # reachable moves for the selected hero
        if self.selected_pid is not None:
            party = next((p for p in c.parties
                          if p.pid == self.selected_pid), None)
            if party is not None:
                for n in G.neighbours(*party.hex, c.world.width,
                                      c.world.height):
                    if not c.world.is_passable(n):
                        continue
                    if any(tuple(o.hex) == n for o in c.parties):
                        continue
                    mx, my = hex_center(*n, self.ox, self.oy)
                    pygame.draw.polygon(
                        surf, (90, 200, 90) if party.mp else (120, 110, 90),
                        [(mx - 9, my), (mx + 9, my), (mx, my - 11)], 2)

    def _panel(self, surf):
        c = self.campaign
        pl = c.player
        f = self.app.fonts
        x = SCREEN_W - PANEL_W + 12
        if pl is None:
            return
        draw_text(surf, f["big"], pl.name.split(" of ")[0], x, 12, (40, 26, 14))
        draw_text(surf, f["small"], c.calendar.label(), x, 56, (80, 60, 30))
        draw_text(surf, f["small"], "Gold %s" % _f(pl.gold), x, 76)
        draw_text(surf, f["small"], "Wheat %s" % _f(pl.wheat), x, 94)
        draw_text(surf, f["small"], "Population %d" % pl.population, x, 112)
        draw_text(surf, f["small"], "Morale %d" % int(pl.morale), x, 130)
        if self.selected_sid is not None:
            h = c.settlements.get(self.selected_sid)
            if h:
                gp = c.garrison_party(self.selected_sid)
                hp = c.hero_party(pl.key)
                draw_text(surf, f["small"],
                          "Garrison %d/%d  Field %d/%d" % (
                              len(gp.unit_ids) if gp else 0,
                              h.garrison_cap(), len(hp.unit_ids) if hp else 0,
                              1 + C.COMPANY_CAP), x, 148, (70, 50, 30))
        if self.hint:
            draw_text(surf, f["small"], self.hint[:46], x, 260, (90, 40, 30))
        y = 360
        for note in c.notes[-6:][::-1]:
            draw_text(surf, f["small"], note[:48], x, y, (90, 74, 52))
            y += 20
        if c.ended:
            word = "DEFEAT - the realm is gone" if c.end_reason == \
                "defeat" else "VICTORY - the last realm endures"
            draw_text(surf, f["big"], word, x - 20, 220, (150, 20, 14))

    @staticmethod
    def _f(v):
        return _f(v)