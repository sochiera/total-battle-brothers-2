"""Campaign screen: the large hex world, parties, settlements, realm
resources, date, selected settlement card, company roster, march actions and
end-month.  Party movement tweens between hexes and owned holdings pulse;
the rules underneath stay instant and headless."""
import math

import pygame

from tbb.rules import constants as C
from tbb.rules import terrain as G
from tbb.app.ui import (hex_center, pick_hex, draw_panel, draw_text, Button,
                        PANEL_W, SCREEN_W, SCREEN_H, TS, realm_index)

TWEEN_FRAMES = 10


def _f(n):
    return str(int(round(n))) if isinstance(n, float) else str(n)


class CampaignScreen:
    RESOURCE_Y = 248
    SETTLEMENT_Y = 306
    def __init__(self, app):
        self.app = app
        self.campaign = None
        self.map_surf = None
        self.ox, self.oy = 30, 20
        self.selected_pid = None
        self.selected_sid = None
        self.hint = ""
        self._buttons = []
        self.anims = []          # party march tweens, presentation only
        self._walkers = {}

    # ------------------------------------------------------------ loading
    def load(self, campaign):
        self.campaign = campaign
        self._build_map()
        self.selected_sid = (campaign.player.settlement_ids or [None])[0]
        self.anims = []

    def _build_map(self):
        cmap = self.campaign
        w, h = cmap.world.width, cmap.world.height
        self.map_w = int(TS * 1.72 * (w + h * 0.5)) + 400
        self.map_h = int(TS * 1.5 * h) + 300
        surf = pygame.Surface((self.map_w, self.map_h))
        t = self.app.art["terrain"]
        for (q, r), terr in cmap.world.grid.items():
            cx, cy = hex_center(q, r, ts=TS)
            img = t.get((terr, cmap.world.crossing((q, r))), t[terr])
            surf.blit(img, (cx - img.get_width() // 2,
                            cy - img.get_height() // 2))
        self.map_surf = surf

    # ------------------------------------------------------------ buttons
    def _make_buttons(self):
        x1 = SCREEN_W - PANEL_W + 12
        x2 = x1 + 162
        out = []
        pending = bool(self.campaign and self.campaign.pending_battles)
        items = [
            (x1, 70, "Battle waits (B)", self.resolve_battle, pending),
            (x2, 70, "Auto-resolve (A)", self.auto_resolve, pending),
            (x1, 106, "End Month (M)", self.end_month, True),
            (x2, 106, "Open (O)", self.open_selected, True),
            (x1, 142, "Court (C)", self.app.enter_court, True),
            (x2, 142, "Found (F)", self.toggle_found, True),
            (x1, 178, "Save (S)", lambda: self.app.enter_save(True), True),
            (x2, 178, "Load (L)", lambda: self.app.enter_save(False), True),
            (x1, 214, "Title (Esc)", self.to_title, True),
        ]
        for x, y, label, fn, enabled in items:
            out.append(Button(x, y, 158, 30, label, fn, enabled))
        return out

    def layout_contract(self):
        """Geometry contract used by UI smoke tests and future skins."""
        buttons = self._make_buttons()
        resource = (SCREEN_W - PANEL_W + 8, self.RESOURCE_Y, PANEL_W - 16, 42)
        settlement = (SCREEN_W - PANEL_W + 8, self.SETTLEMENT_Y,
                      PANEL_W - 16, 150)
        return {"resource": resource, "settlement": settlement,
                "buttons": [b.rect for b in buttons]}

    # ------------------------------------------------------------ actions
    def end_month(self):
        c = self.campaign
        if c.pending_battles:
            self.resolve_battle()
            self.app.audio.sfx("cant")
            return
        self._snapshot_walkers()
        res = c.end_turn()
        if not res.ok:
            self.hint = res.reason
            self.app.audio.sfx("cant")
            return
        self._tween_walkers()
        self.app.audio.sfx("close")
        self.hint = "Month turned - %s" % res.reason
        if c.ended:
            self.hint = ("The realm has ended: %s" % c.end_reason)
            self.app.show_epilogue()

    def _tween_walkers(self):
        """Turn the end-of-month walker steps into visible tweens."""
        for party in self.campaign.parties:
            if party.kind not in ("hero", "bandit"):
                continue
            was = self._walkers.get(party.pid)
            if was is not None and was != party.hex:
                self.anims.append({"pid": party.pid, "from": was,
                                   "to": party.hex, "t": 0})

    def _snapshot_walkers(self):
        """Remember where the hero and robber bands stand so their end-of-
        month steps can be tweened (presentation only)."""
        c = self.campaign
        self._walkers = {p.pid: p.hex for p in c.parties
                         if p.kind in ("hero", "bandit")}

    def resolve_battle(self):
        if not self.campaign.pending_battles:
            return
        b = self.campaign.pending_battles[0]
        self.app.start_battle(b)
        self.app.audio.sfx("click")

    def open_selected(self):
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
        self.app.audio.sfx("open")

    def toggle_found(self):
        self.app.found_mode = not getattr(self.app, "found_mode", False)
        self.hint = (("Found mode ON - click empty plains, ruins, or "
                      "farmland beside your own land")
                     if self.app.found_mode else "Found mode off")
        self.app.audio.sfx("click")

    def to_title(self):
        self.app.mode = "title"
        self.app.audio.sfx("close")

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
            elif k == pygame.K_a:
                self.auto_resolve()
            elif k == pygame.K_f:
                self.toggle_found()
            elif k == pygame.K_m:
                self.end_month()
            elif k == pygame.K_o:
                self.open_selected()
            elif k == pygame.K_c:
                self.app.enter_court()
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
            elif k == pygame.K_LEFT:
                self.ox += 40
            elif k == pygame.K_RIGHT:
                self.ox -= 40
            elif k == pygame.K_UP:
                self.oy += 40
            elif k == pygame.K_DOWN:
                self.oy -= 40

    def auto_resolve(self):
        if not self.campaign.pending_battles:
            self.hint = "No battle is waiting"
            return
        self.campaign.auto_resolve_pending()
        self.hint = "Pending battle auto-resolved"
        self.app.audio.sfx("close")

    def _button_build(self):
        self._buttons = self._make_buttons()
        return self._buttons

    def _click_hex(self, pos):
        c = self.campaign
        q, r = pick_hex(pos[0], pos[1], self.ox, self.oy)
        if not c.world.in_bounds((q, r)):
            return
        hexpos = (q, r)
        if getattr(self.app, "found_mode", False):
            res = self.campaign.order_found(hexpos)
            if res.ok:
                self.hint = "A village is being seeded there"
                self.app.found_mode = False
                self.app.audio.sfx("close")
            else:
                self.app.audio.sfx("cant")
                self.hint = res.reason
            return
        # march the selected hero company
        if self.selected_pid is not None:
            party = next((p for p in self.campaign.parties
                          if p.pid == self.selected_pid), None)
            if party is not None and tuple(party.hex) != hexpos:
                before = party.hex
                res = self.campaign.move_party(party.pid, hexpos)
                if res.ok:
                    self.app.audio.sfx("hit")
                    self.anims.append({"pid": party.pid, "from": before,
                                       "to": party.hex, "t": 0})
                    if self.campaign.pending_battles:
                        self.hint = "Contact! Press B for battle"
                else:
                    self.app.audio.sfx("cant")
                    self.hint = res.reason
                return
        # pick what stands there
        sid = self.campaign.settlement_id_at(hexpos)
        parties_here = [p for p in self.campaign.parties
                        if tuple(p.hex) == hexpos]
        party = next((p for p in parties_here if p.kind == "bandit"),
                     parties_here[0] if parties_here else None)
        if party is not None and party.realm == self.campaign.player.key \
                and party.kind == "hero":
            self.selected_pid = party.pid
            self.selected_sid = sid
            self.hint = ("Company of %d men, %d moves left - click an "
                          "adjacent hex to march"
                          % (party.size(), party.mp))
        elif party is not None and party.kind == "bandit":
            leader = c.units.get(party.unit_ids[0]) if party.unit_ids else None
            name = leader.name if leader else "unknown raider"
            self.selected_pid = None
            self.hint = ("Robber band %d, led by %s: %d men - raid threat"
                          % (party.pid, name, party.size()))
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

    def bandit_parties(self):
        return [p for p in self.campaign.parties if p.kind == "bandit"
                and any(self.campaign.units[u].alive for u in p.unit_ids)]

    def visible_bandit_pids(self):
        """IDs presented on the map, useful to the UI and smoke tests."""
        return [p.pid for p in self.bandit_parties()]

    def _world_visible(self, hexpos):
        return True

    # ---------------------------------------------------------------- draw
    def draw(self, surf):
        surf.fill((66, 70, 58))
        surf.blit(self.map_surf, (self.ox, self.oy))
        tint = {C.SEASON_WINTER: (100, 140, 190, 34),
                C.SEASON_HARVEST: (210, 150, 55, 28),
                C.SEASON_OPEN: (80, 150, 70, 12)}[
                    self.campaign.calendar.season]
        veil = pygame.Surface((SCREEN_W - PANEL_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill(tint)
        surf.blit(veil, (0, 0))
        self._overlays(surf)
        draw_panel(surf, SCREEN_W - PANEL_W, 0, PANEL_W, SCREEN_H)
        self._panel(surf)
        for b in self._button_build():
            b.draw(surf, self.app.fonts["small"])
        if getattr(self.app, "found_mode", False):
            draw_text(surf, self.app.fonts["med"],
                      "FOUND MODE: pick empty ground", 24, 20, (150, 40, 20))

    def _party_pixel(self, party):
        """Where the token is drawn this frame, honouring active tweens."""
        for anim in self.anims:
            if anim["pid"] == party.pid:
                fx, fy = hex_center(*anim["from"], self.ox, self.oy)
                tx, ty = hex_center(*anim["to"], self.ox, self.oy)
                k = anim["t"] / float(TWEEN_FRAMES)
                return int(fx + (tx - fx) * k), int(fy + (ty - fy) * k)
        return hex_center(*party.hex, self.ox, self.oy)

    def _advance_anims(self):
        for anim in self.anims:
            anim["t"] += 1
        self.anims = [a for a in self.anims if a["t"] <= TWEEN_FRAMES]

    def _overlays(self, surf):
        c = self.campaign
        sf = self.app.fonts["small"]
        settle_art = self.app.art["settle"]
        now = pygame.time.get_ticks()
        # Holdings are painted first so a raider remains visible and
        # clickable; owned ones breathe with a slow idle pulse.
        for h in c.settlements.values():
            sxx, syy = hex_center(*h.hex, self.ox, self.oy)
            sector = realm_index(c, h.owner)
            sp = settle_art[(sector, h.size)]
            surf.blit(sp, (sxx - sp.get_width() // 2,
                           syy - sp.get_height() // 2))
            if h.owner is not None and h.owner in c.realms:
                radius = int(17 + 2.5 * math.sin(now / 620.0 +
                                                 (h.id % 5)))
                pygame.draw.circle(surf, c.realms[h.owner].color,
                                   (sxx, syy), radius, 2)
        for name, cells in c.world.regions.items():
            if not cells:
                continue
            q, r = min(cells, key=lambda pos: (pos[1], pos[0]))
            rx, ry = hex_center(q, r, self.ox, self.oy)
            draw_text(surf, sf, name, rx + 4, ry + 4, (68, 70, 60))
        self._advance_anims()
        for p in c.parties:
            cx, cy = self._party_pixel(p)
            if p.kind == "bandit":
                if not any(c.units[u].alive for u in p.unit_ids):
                    continue
                sp = self.app.art["bandit"]
                surf.blit(sp, (cx - sp.get_width() // 2,
                               cy - sp.get_height() // 2))
                draw_text(surf, sf, "%d robbers" % len(p.unit_ids),
                          cx + 12, cy + 8, (90, 24, 18))
                continue
            if p.unit_ids:
                u = c.units[p.unit_ids[0]]
                si = realm_index(c, u.realm)
                sp = self.app.art["unit"].get((si, u.kit, u.is_hero))
                if sp:
                    surf.blit(sp, (cx - 8, cy - 10))
        # hero banner + company counts
        for p in c.parties:
            if p.kind != "hero":
                continue
            cx, cy = self._party_pixel(p)
            banner = self.app.art["banner"].get(realm_index(c, p.realm))
            if banner:
                surf.blit(banner, (cx - banner.get_width() // 2, cy - 26))
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
        if self.campaign.pending_battles:
            draw_text(surf, self.app.fonts["med"],
                      "A BATTLE WAITS - press B", 24, 48, (200, 40, 22))

    def _panel(self, surf):
        c = self.campaign
        pl = c.player
        f = self.app.fonts
        x = SCREEN_W - PANEL_W + 12
        if pl is None:
            return
        draw_text(surf, f["big"], pl.name.split(" of ")[0], x, 6, (40, 26, 14))
        draw_text(surf, f["small"], c.calendar.label(), x, 42, (80, 60, 30))
        # The resource strip is reserved below the complete button row.  The
        # settlement card starts after it, so the chrome remains readable at
        # every selection state.
        draw_text(surf, f["small"],
                  "Gold %s   Wheat %s" % (_f(pl.gold), _f(pl.wheat)),
                  x, 252, (60, 45, 20))
        draw_text(surf, f["small"],
                  "Population %d   Morale %d" % (pl.population,
                                                 int(pl.morale)),
                  x, 270, (60, 45, 20))
        # selected settlement card
        y = 310
        if self.selected_sid is not None:
            h = c.settlements.get(self.selected_sid)
            if h:
                owner = ("Yours" if h.owner == pl.key else
                         (c.realms[h.owner].name if h.owner is not None
                          else "free lands"))
                gp = c.garrison_party(self.selected_sid)
                draw_text(surf, f["small"],
                          "%s - %s (%s)" % (h.name, h.size, owner),
                          x, y, (40, 26, 14))
                draw_text(surf, f["small"],
                          "Garrison %d/%d" % (len(gp.unit_ids) if gp else 0,
                                              h.garrison_cap()),
                          x, y + 17, (70, 50, 30))
                buildings = list(h.buildings)
                for index, kind in enumerate(buildings[:3]):
                    draw_text(surf, f["small"], kind.replace("_", " "),
                              x, y + 34 + index * 16, (90, 72, 48))
                if len(buildings) > 3:
                    draw_text(surf, f["small"], "+ %d more" %
                              (len(buildings) - 3), x, y + 34 + 48,
                              (90, 72, 48))
                y += 34 + 48 + (16 if len(buildings) > 3 else 0)
        # company roster
        y += 14
        draw_text(surf, f["small"], "Company roster:", x, y, (70, 45, 28))
        y += 19
        party = c.hero_party(pl.key)
        for unit in (c.living_in_party(party) if party else [])[:12]:
            draw_text(surf, f["small"],
                      "%s  %s" % (unit.name[:20], unit.kit[:12]),
                      x, y, (70, 50, 35))
            y += 17
        # robber bands
        y += 6
        draw_text(surf, f["small"], "Robber bands:", x, y, (90, 35, 24))
        y += 19
        for pb in self.bandit_parties()[:3]:
            leader = c.units.get(pb.unit_ids[0]) if pb.unit_ids else None
            label = "%d: %s (%d)" % (pb.pid,
                                     leader.name if leader else "raiders",
                                     pb.size())
            draw_text(surf, f["small"], label[:42], x, y, (100, 35, 25))
            y += 17
        # hint and month notes
        if self.hint:
            draw_text(surf, f["small"], self.hint[:44], x, 682, (90, 40, 30))
        y = 704
        for note in c.notes[-4:][::-1]:
            draw_text(surf, f["small"], note[:44], x, y, (90, 74, 52))
            y += 18
        if c.ended:
            word = ("DEFEAT - the realm is gone" if c.end_reason ==
                    "defeat" else "VICTORY - the last realm endures")
            draw_text(surf, f["big"], word, 24, 120, (150, 20, 14))

    @staticmethod
    def _f(v):
        return _f(v)
