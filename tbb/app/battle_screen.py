"""Battle screen: readable hex fight - distinct terrain, each living warrior
visible with kit/side, whose turn it is, hit / wound / death feedback, and
morale implied through hit numbers without routs."""
import pygame

from tbb.rules import constants as C
from tbb.app.ui import hex_center, pick_hex, draw_panel, draw_text, Button, \
    hex_corners, SCREEN_W, SCREEN_H, realm_index


class BattleScreen:
    def __init__(self, app):
        self.app = app
        self.battle = None
        self.selected_uid = None
        self.hint = ""
        self.log = []
        self._ox = 0
        self._oy = 0

    def load(self, battle):
        self.battle = battle
        self.selected_uid = None
        if self.selected_uid is None:
            human = [uid for uid in battle.sides[battle.human_side()]
                     if battle.alive.get(uid)]
            self.selected_uid = human[0] if human else None
        self.battle_result = None
        self._compute_focus()

    def _compute_focus(self):
        cq, cr = self.battle.center
        self._ox = int(SCREEN_W / 2 - 1.72 * 22 * (cq + cr * 0.5))
        self._oy = int(SCREEN_H / 2 - 40 - 1.5 * 22 * cr)

    # ------------------------------------------------------------ actions
    def _do(self, res):
        if res and res.ok:
            if "slain" in (res.reason or ""):
                self.app.audio.sfx("death")
            elif "wound" in (res.reason or ""):
                self.app.audio.sfx("pain")
            else:
                self.app.audio.sfx("hit")
            self.hint = res.reason
        else:
            self.app.audio.sfx("cant")
            self.hint = res.reason if res else ""

    def _advance_if_over(self):
        b = self.battle
        if b is None or not b.over():
            return
        self.app.campaign.resolve_battle(b)
        c = self.app.campaign
        pending = [x for x in c.pending_battles if not x.over()]
        c.pending_battles = pending
        if c.pending_battles:
            self.app.start_battle(c.pending_battles[0])
        else:
            self.app.finish_battle()

    def do_end_turn(self):
        if self.battle is None:
            return
        if self.battle.over():
            self._advance_if_over()
            return
        res = self.battle.end_player_turn()
        self.hint = res.reason if not res.ok else "the foe stirs"
        self.app.audio.sfx("click")
        self.selected_uid = None
        # select a fresh unit
        if self.battle and not self.battle.over():
            alive = [u for u in self.battle.sides[self.battle.turn_side]
                     if self.battle.alive.get(u)]
            self.selected_uid = alive[0] if alive else None
        self._advance_if_over()

    # ------------------------------------------------------------ events
    def handle(self, ev):
        if self.battle is None:
            return
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for b in self._buttons():
                if b.hit(ev.pos[0], ev.pos[1]):
                    b.on_click()
                    return
            self._click(ev.pos)
        elif ev.type == pygame.KEYDOWN:
            k = ev.key
            if k == pygame.K_SPACE or k == pygame.K_RETURN:
                self.do_end_turn()
            elif k == pygame.K_a:
                self.auto_battle()
            elif k in (pygame.K_ESCAPE, pygame.K_q):
                pass

    def _buttons(self):
        bx, by, bw, bh = SCREEN_W // 2 - 200, SCREEN_H - 66, 180, 38
        if self.battle and self.battle.over():
            label = "Return to Map"
            items = [Button(bx, by, bw, bh, label, self._btn_end,
                            enabled=True)]
        else:
            items = [Button(bx, by, bw, bh, "End Turn (SPACE)",
                            self._btn_end, enabled=True),
                     Button(bx + bw + 12, by, bw, bh, "Auto (A)",
                            self.auto_battle, enabled=True)]
        return items

    def _btn_end(self):
        if self.battle and self.battle.over():
            self._advance_if_over()
        else:
            self.do_end_turn()

    def auto_battle(self):
        """Deterministic auto-resolve: finishes the fight and writes it back
        so a player never leaves a pending battle stuck."""
        if self.battle is None:
            return
        if not self.battle.over():
            self.battle.auto_resolve()
            self.app.audio.sfx("close")
        self._advance_if_over()

    def _click(self, pos):
        b = self.battle
        q, r = pick_hex(pos[0], pos[1], self._ox, self._oy)
        hexpos = (q, r)
        if hexpos not in b.canvas:
            return
        u = None
        if self.selected_uid is not None:
            u = b.campaign.units.get(self.selected_uid)
        tgt = b.unit_at(hexpos)
        if tgt is not None and u is not None and u.alive and \
                b.side_of.get(tgt.id, None) != b.side_of.get(u.id, None):
            # attack
            if b.melee_in_range(u, tgt) and u.id in (b.sides[b.turn_side]):
                self._do(b.do_melee(u, tgt))
                self._advance_if_over()
                return
            if b.ranged_in_range(u, tgt) and b.has_bow(u):
                self._do(b.do_ranged(u, tgt))
                self._advance_if_over()
                return
            self.hint = "out of reach"
            self.app.audio.sfx("cant")
            return
        if u is not None and u.id in b.sides[b.turn_side] and u.alive and \
                b.can_act(u):
            moves = b.available_moves(u)
            if hexpos in moves:
                self._do(b.do_move(u, hexpos))
                return
        # select the unit standing here (own side)
        if tgt is not None and tgt.alive and \
                b.side_of.get(tgt.id) == b.turn_side:  # our side acts
            self.selected_uid = tgt.id
            self.hint = "%s acts" % tgt.name

    # --------------------------------------------------------------- draw
    def draw(self, surf):
        b = self.battle
        if b is None:
            return
        surf.fill((54, 54, 46))
        f = self.app.fonts
        t = self.app.art["terrain"]
        unit_art = self.app.art["unit"]
        # terrain
        for (pos, terr) in b.canvas.items():
            cx, cy = self._hex(pos)
            img = t[terr]
            surf.blit(img, (cx - img.get_width() // 2,
                            cy - img.get_height() // 2))
        # moves highlight
        if self.selected_uid is not None:
            u = b.campaign.units.get(self.selected_uid)
            if u is not None and u.alive:
                for m in b.available_moves(u):
                    mx, my = self._hex(m)
                    pygame.draw.polygon(surf, (120, 220, 120),
                                        [(mx - 10, my), (mx + 10, my),
                                         (mx, my - 12)], 2)
        # units
        for uid, pos in b.positions.items():
            unit = b.campaign.units[uid]
            if not b.alive.get(uid):
                continue
            cx, cy = self._hex(pos)
            si = realm_index(b.campaign, unit.realm)
            sp = unit_art.get((si, unit.kit, unit.is_hero))
            if sp:
                surf.blit(sp, (cx - 8, cy - 10))
            if b.side_of[uid] == b.turn_side and b.alive.get(uid) and \
                    b.campaign.units[uid].realm == b.campaign.player.key:
                pass
            draw_text(surf, f["small"], "%s  AP%d HP%d/%d" % (unit.name[:14], b.ap.get(uid, 0), unit.current_hit_points, unit.max_hit_points), cx + 8, cy - 4,
                      (30, 20, 12))
        draw_panel(surf, 0, SCREEN_H - 90, SCREEN_W, 90)
        draw_text(surf, f["small"], "Your turn - click a warrior, then a new "
                  "hex to march, a foe to strike" if not b.over() else
                  "Battle over - press Return/SPACE", 12, SCREEN_H - 82,
                  (40, 40, 40))
        if self.hint:
            draw_text(surf, f["small"], self.hint, 12, SCREEN_H - 60,
                      (120, 40, 30))
        draw_text(surf, f["small"], "Round %d - %d attacker, %d defender" % (
            b.round, len(b.living("attacker")), len(b.living("defender"))),
            12, SCREEN_H - 40, (60, 60, 55))
        for bt in self._buttons():
            bt.draw(surf, f["small"])
        if b.over():
            winner = b.winner_side()
            draw_text(surf, f["med"], ("The %s carries the field"
                                       % winner), SCREEN_W // 2 - 120, 30,
                      (220, 40, 30) if winner != b.human_side else
                      (40, 120, 50))

    def _hex(self, pos):
        return hex_center(*pos, self._ox, self._oy)

    def _selected(self):
        return None
