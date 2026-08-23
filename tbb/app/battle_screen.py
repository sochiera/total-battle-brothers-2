"""Battle screen: readable 30x20 hex fight - themed terrain, each living
warrior visible with kit/side, side-based turns (act with several warriors,
then SPACE ends your side and the scripted foe answers), hit / wound / death
feedback with lunge, projectile and flash juice."""
import pygame

from tbb.rules import constants as C
from tbb.app.ui import hex_center, pick_hex, draw_panel, draw_text, Button, \
    hex_corners, SCREEN_W, SCREEN_H, realm_index

FX_FRAMES = 8


class BattleScreen:
    def __init__(self, app):
        self.app = app
        self.battle = None
        self.selected_uid = None
        self.hint = ""
        self.log = []
        self._ox = 0
        self._oy = 0
        self.fx = []            # strike / projectile / hit / wound / death effects

    def load(self, battle):
        self.battle = battle
        self.selected_uid = None
        self.fx = []
        if self.selected_uid is None:
            human = [uid for uid in battle.sides[battle.human_side()]
                     if battle.alive.get(uid)]
            self.selected_uid = human[0] if human else None
        self.battle_result = None
        self._compute_focus()
        # If the foe opens the fight, they take their scripted turn now.
        if not battle.over() and battle.turn_side != battle.human_side():
            self._run_foe_side()

    def _compute_focus(self):
        cq, cr = self.battle.center
        self._ox = int(SCREEN_W / 2 - 1.72 * 22 * (cq + cr * 0.5))
        self._oy = int(SCREEN_H / 2 - 60 - 1.5 * 22 * cr)

    # ------------------------------------------------------------ actions
    def _do(self, res, kind=None):
        if res and res.ok:
            if "slain" in (res.reason or ""):
                self.app.audio.sfx("death")
            elif "wound" in (res.reason or ""):
                self.app.audio.sfx("pain")
            elif kind == "ranged":
                self.app.audio.sfx("bow")
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
        self.hint = res.reason if not res.ok else res.reason
        self.app.audio.sfx("click")
        self.selected_uid = None
        for record in getattr(res, "records", []):
            self._fx_from_record(record)
        if self.battle and not self.battle.over():
            alive = [u for u in self.battle.sides[self.battle.turn_side]
                     if self.battle.alive.get(u)]
            self.selected_uid = alive[0] if alive else None
        self._advance_if_over()

    def _run_foe_side(self):
        """Play the acting non-human side and render its juice."""
        records = self.battle.scripted_turn()
        for record in records:
            self._fx_from_record(record)

    def _fx_from_record(self, record):
        b = self.battle
        unit = b.campaign.units.get(record.get("unit"))
        target = b.campaign.units.get(record.get("target"))
        if record["kind"] == "move":
            return
        if unit is None or target is None:
            return
        kind = record["kind"]
        if kind == "melee":
            self.fx.append({"kind": "melee_strike", "unit": unit.id,
                            "toward": b.position_of(target), "t": 0})
        elif kind == "ranged":
            self.fx.append({"kind": "projectile", "from": b.position_of(unit),
                            "to": b.position_of(target), "t": 0})
        if record.get("hit"):
            effect_kind = "death" if not target.alive else (
                "wound_flash" if record.get("reason") == "wound" else "hit_flash")
            self.fx.append({"kind": effect_kind,
                            "pos": b.position_of(target), "t": 0,
                            "dead": not target.alive})
            if not target.alive:
                self.app.audio.sfx("death")
            else:
                self.app.audio.sfx("pain" if record.get("reason") == "wound"
                                   else "hit")
        elif kind == "ranged":
            self.app.audio.sfx("bow")

    # -------------------------------------------------------------- events
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
                self._strike(u, tgt, "melee")
                return
            if b.ranged_in_range(u, tgt) and b.has_bow(u) and \
                    u.id in b.sides[b.turn_side]:
                self._strike(u, tgt, "ranged")
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

    def _strike(self, u, tgt, kind):
        b = self.battle
        res = b.do_melee(u, tgt) if kind == "melee" else b.do_ranged(u, tgt)
        if res.ok:
            for record in res.records or [{"kind": kind, "unit": u.id,
                                           "target": tgt.id, "hit": res.hit,
                                           "reason": res.reason}]:
                self._fx_from_record(record)
        self._do(res, kind)
        self._advance_if_over()

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
            img = t.get(terr)
            if img is None:
                continue
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
        lunge_offsets = {}
        for effect in self.fx:
            if effect["kind"] in ("lunge", "melee_strike"):
                unit = b.campaign.units.get(effect["unit"])
                if unit is None:
                    continue
                home = b.position_of(unit)
                hx, hy = self._hex(home)
                tx, ty = self._hex(effect["toward"])
                k = effect["t"] / float(FX_FRAMES)
                reach = max(0.0, 1.0 - abs(2.0 * k - 1.0))  # out and back
                lunge_offsets[effect["unit"]] = (
                    int((tx - hx) * 0.3 * reach),
                    int((ty - hy) * 0.3 * reach))
        for uid, pos in b.positions.items():
            unit = b.campaign.units[uid]
            if not b.alive.get(uid):
                continue
            cx, cy = self._hex(pos)
            dx, dy = lunge_offsets.get(uid, (0, 0))
            si = realm_index(b.campaign, unit.realm)
            bandit_side = (b.attacker if b.side_of[uid] == "attacker"
                           else b.defender)
            sp = (self.app.art["bandit"] if bandit_side.kind == "bandit"
                  else unit_art.get((si, unit.kit, unit.is_hero)))
            if sp:
                surf.blit(sp, (cx - 8 + dx, cy - 10 + dy))
            if b.side_of[uid] == b.turn_side and uid == self.selected_uid:
                pygame.draw.circle(surf, (240, 210, 90), (cx, cy + 12), 3)
            draw_text(surf, f["small"], "%s  AP%d HP%d/%d" % (unit.name[:12], b.ap.get(uid, 0), unit.current_hit_points, unit.max_hit_points), cx + 8, cy - 4,
                      (30, 20, 12))
        self._draw_fx(surf)
        draw_panel(surf, 0, SCREEN_H - 90, SCREEN_W, 90)
        your_side = b.human_side()
        acting = ("Yours" if b.turn_side == your_side else "The foe's")
        draw_text(surf, f["small"], "%s turn - click a warrior, then a new "
                  "hex to march, a foe to strike; SPACE ends the side"
                  % acting if not b.over() else
                  "Battle over - press Return/SPACE", 12, SCREEN_H - 82,
                  (40, 40, 40))
        if self.hint:
            draw_text(surf, f["small"], self.hint, 12, SCREEN_H - 60,
                      (120, 40, 30))
        battle_kind = b.contact_kind.replace("_", " ")
        draw_text(surf, f["small"], "Round %d - %d vs %d, %s ground — %s" % (
            b.round, len(b.living("attacker")), len(b.living("defender")),
            b.contact_terrain, battle_kind), 12, SCREEN_H - 40, (60, 60, 55))
        if b.contact_kind == "prepared_assault":
            draw_text(surf, f["med"], "PREPARED ASSAULT — defender walls",
                      24, 20, (210, 175, 85))
        elif b.contact_kind == "raid":
            draw_text(surf, f["med"], "RAID — sack and withdraw, no annexation",
                      24, 20, (210, 115, 70))
        for bt in self._buttons():
            bt.draw(surf, f["small"])
        if b.over():
            winner = b.winner_side()
            draw_text(surf, f["med"], ("The %s carries the field"
                                        % winner), SCREEN_W // 2 - 120, 30,
                      (220, 40, 30) if winner != your_side else
                      (40, 120, 50))

    def _draw_fx(self, surf):
        b = self.battle
        for effect in self.fx:
            k = effect["t"] / float(FX_FRAMES)
            if effect["kind"] == "projectile":
                fx_, fy_ = self._hex(effect["from"])
                tx, ty = self._hex(effect["to"])
                x = int(fx_ + (tx - fx_) * k)
                y = int(fy_ + (ty - fy_) * k)
                pygame.draw.line(surf, (60, 40, 20), (x - 4, y), (x + 4, y), 2)
                pygame.draw.line(surf, (210, 180, 120), (x - 3, y), (x + 2, y), 1)
            elif effect["kind"] in ("hit_flash", "wound_flash", "death", "flash"):
                x, y = self._hex(effect["pos"])
                if effect["kind"] == "death" or effect.get("dead"):
                    radius = int(6 + 14 * k)
                    pygame.draw.circle(surf, (200, 30, 20), (x, y),
                                       radius, 3)
                elif effect["kind"] == "wound_flash":
                    radius = int(5 + 10 * k)
                    pygame.draw.circle(surf, (250, 170, 45), (x, y),
                                       radius, 3)
                else:
                    radius = int(4 + 8 * k)
                    colour = (255, 240, 220) if k < 0.5 else (220, 60, 40)
                    pygame.draw.circle(surf, colour, (x, y), radius, 2)
        for effect in self.fx:
            effect["t"] += 1
        self.fx = [e for e in self.fx if e["t"] <= FX_FRAMES]

    def _hex(self, pos):
        return hex_center(*pos, self._ox, self._oy)

    def playback_kinds(self):
        """Kinds currently queued for the dump/playback contract."""
        return {effect["kind"] for effect in self.fx}
