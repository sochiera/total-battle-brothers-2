"""Readable settlement actions with dry-run reasons.

The rules package remains the authority for legality.  This screen mirrors
those checks before a click so a disabled button explains the missing supply,
worker, building, or location in one short line.
"""
import pygame

from tbb.rules import constants as C
from tbb.rules import terrain as GEO
from tbb.app.ui import draw_panel, draw_text, Button, SCREEN_W, SCREEN_H


def _f(value):
    return str(int(round(value))) if isinstance(value, float) else str(value)


class SettlementScreen:
    HUMAN_BUILDINGS = {
        "farm": "Farm", "granary": "Granary", "market": "Market",
        "militia_hall": "Militia Hall", "drill_yard": "Drill Yard",
        "smithy": "Smithy", "fletcher": "Fletcher", "stables": "Stables",
        "palisade_walls": "Palisade / Walls", "keep": "Keep",
    }

    def __init__(self, app):
        self.app = app
        self.campaign = None
        self.sid = None
        self.hint = ""
        self.unit_page = 0
        self.garrison_page = 0

    def load(self, campaign, sid):
        self.campaign, self.sid = campaign, sid
        self.hint = ""
        self.unit_page = 0
        self.garrison_page = 0

    def _holding(self):
        return self.campaign.settlements[self.sid]

    def _realm(self):
        return self.campaign._realm_of_settlement(self.sid)

    def _nextsize(self):
        index = C.SIZE_ORDER.index(self._holding().size)
        return C.SIZE_ORDER[index + 1] if index + 1 < len(C.SIZE_ORDER) else None

    def _bname(self, kind):
        return self.HUMAN_BUILDINGS.get(kind, kind.replace("_", " ").title())

    @staticmethod
    def _with_reason(label, reason):
        return label if reason is None else "%s — %s" % (label, reason)

    # Dry-run validators are deliberately side-effect free; they are also
    # useful to tests and keep the UI's disabled state honest.
    def _build_reason(self, kind):
        realm, holding = self._realm(), self._holding()
        if realm is None or realm.key != self.campaign.player.key:
            return "not your holding"
        if kind in holding.buildings:
            return "already built"
        if holding.building_slots_free() <= 0:
            return "no building slots"
        if any(o.kind == "build" and o.settlement_id == self.sid
               for o in realm.orders):
            return "a building is already in progress"
        spec = C.BUILDINGS[kind]
        if spec["req"] and holding.size_index() < C.SIZE_ORDER.index(spec["req"]):
            return "requires a %s" % spec["req"]
        if realm.gold < spec["gold"]:
            return "need %dg gold" % spec["gold"]
        if realm.wheat < spec["wheat"]:
            return "need %dw wheat" % spec["wheat"]
        return None

    def _recruit_reason(self, field=False):
        realm, holding = self._realm(), self._holding()
        cost = C.RECRUIT_COST
        if realm.gold < cost["gold"]:
            return "need %dg gold" % cost["gold"]
        if realm.wheat < cost["wheat"]:
            return "need %dw wheat" % cost["wheat"]
        if not self.campaign._can_spend_population(realm, cost["population"]):
            return "one idle resident must remain"
        if field:
            party = self.campaign.hero_party(realm.key)
            if not party or party.hex != holding.hex:
                return "hero company is not here"
            queued = sum(1 for o in realm.orders
                         if o.kind == "recruit" and o.kind_data == "field")
            if len(party.unit_ids) + queued >= C.COMPANY_CAP:
                return "company cap is 12"
        else:
            party = self.campaign.garrison_party(self.sid)
            queued = sum(1 for o in realm.orders
                         if o.kind == "recruit" and o.kind_data == "garrison"
                         and o.settlement_id == self.sid)
            if not party or len(party.unit_ids) + queued >= holding.garrison_cap():
                return "garrison is full"
        return None

    def _train_reason(self, uid):
        realm = self._realm()
        unit = self.campaign.units.get(uid)
        if unit is None or not unit.alive:
            return "warrior is dead"
        party = self.campaign.hero_party(realm.key)
        if not party or uid not in party.unit_ids:
            return "only the field company trains here"
        if sum(1 for o in realm.orders if o.kind == "train") >= \
                realm.training_slots(self.campaign.settlements):
            return "all training slots are occupied"
        focus = self._training_focus()
        if focus is None:
            return "build and staff a Drill Yard, Smithy, Fletcher, or Stables"
        if any(o.kind == "train" and o.unit_id == uid for o in realm.orders):
            return "already training"
        return None

    def _training_focus(self):
        realm = self._realm()
        for kind in (C.BUILDING_DRILL_YARD, C.BUILDING_SMITHY,
                     C.BUILDING_FLETCHER, C.BUILDING_STABLES):
            if realm.staffed(self.campaign.settlements, kind):
                return kind
        return None

    def _preferred_kit(self, unit):
        realm = self._realm()
        if unit.stat("ranged") >= unit.stat("melee"):
            return "bow"
        if realm.staffed(self.campaign.settlements, C.BUILDING_SMITHY):
            return "two_hander" if unit.stat("melee") >= 42 else "heavy"
        return "light"

    def _gear_reason(self, uid, kit):
        realm = self._realm()
        unit = self.campaign.units.get(uid)
        if unit is None or not unit.alive:
            return "warrior is dead"
        party = self.campaign.hero_party(realm.key)
        if not party or uid not in party.unit_ids:
            return "only the field company can be equipped"
        if any(o.kind == "gear" and o.unit_id == uid for o in realm.orders):
            return "equipment order already in progress"
        spec = C.KITS[kit]
        if spec["need"] and not realm.staffed(self.campaign.settlements, spec["need"]):
            return "requires a staffed %s" % spec["need"]
        if realm.gold < spec["gold"]:
            return "need %dg gold" % spec["gold"]
        if realm.wheat < spec["wheat"]:
            return "need %dw wheat" % spec["wheat"]
        return None

    def _equip_reason(self, uid, kit):
        return self._gear_reason(uid, kit)

    def _develop_reason(self):
        realm, holding = self._realm(), self._holding()
        target = self._nextsize()
        if target is None:
            return "a City cannot develop further"
        if any(o.kind == "develop" and o.settlement_id == self.sid
               for o in realm.orders):
            return "development is already in progress"
        pop_gate = C.DEVELOP_POP_GATE[(holding.size, target)]
        building_gate = C.DEVELOP_BUILDING_GATE[(holding.size, target)]
        if holding.population < pop_gate:
            return "needs %d local residents (has %d)" % (pop_gate, holding.population)
        if len(holding.buildings) < building_gate:
            return "needs %d completed buildings (has %d)" % (building_gate, len(holding.buildings))
        cost = C.DEVELOP_COST[(holding.size, target)]
        if realm.gold < cost["gold"]:
            return "need %dg gold" % cost["gold"]
        if realm.wheat < cost["wheat"]:
            return "need %dw wheat" % cost["wheat"]
        return None

    def _found_reason(self):
        realm = self._realm()
        if realm.gold < C.FOUND_COST["gold"]:
            return "need %dg gold" % C.FOUND_COST["gold"]
        if realm.wheat < C.FOUND_COST["wheat"]:
            return "need %dw wheat" % C.FOUND_COST["wheat"]
        if not self.campaign._can_spend_population(realm, C.FOUND_COST["settlers"]):
            return "need settlers while keeping workers"
        valid = any(self.campaign.world.in_bounds(pos) and
                    self.campaign.settlement_at(pos) is None and
                    self.campaign.world.terrain(pos) in
                    C.FOUNDABLE_TERRAINS and
                    any(pos in self.campaign.world.neighbours(
                        self.campaign.settlements[s].hex)
                        for s in realm.settlement_ids)
                    for row in range(self.campaign.height)
                    for pos in [(column, row)
                                for column in range(self.campaign.width)])
        return None if valid else "no adjacent empty plains, ruins, or farmland"

    def _hero_here(self):
        realm, holding = self._realm(), self._holding()
        party = self.campaign.hero_party(realm.key)
        return party if (party and party.hex == holding.hex) else None

    def _attach_reason(self, uid):
        """Dry-run of the rules-level attach check, shown on the button."""
        realm, holding = self._realm(), self._holding()
        party = self._hero_here()
        if party is None:
            return "hero company is not here"
        garrison = self.campaign.garrison_party(self.sid)
        if not garrison or uid not in garrison.unit_ids:
            return "soldier is not in this garrison"
        if len(party.unit_ids) >= C.COMPANY_CAP:
            return "company cap is 12 including the hero"
        return None

    def _detach_reason(self, uid):
        realm, holding = self._realm(), self._holding()
        party = self._hero_here()
        if party is None:
            return "hero company is not here"
        if uid == realm.hero:
            return "the hero never garrisons"
        if uid not in party.unit_ids:
            return "soldier is not in the company"
        garrison = self.campaign.garrison_party(self.sid)
        if garrison and len(garrison.unit_ids) >= holding.garrison_cap():
            return "garrison is full (%d)" % holding.garrison_cap()
        return None

    def _market_reason(self, direction):
        realm, holding = self._realm(), self._holding()
        if not holding.has(C.BUILDING_MARKET):
            return "build and staff a Market"
        if direction == "sell" and realm.wheat < C.MARKET_SELL_WHEAT:
            return "need %dw wheat" % C.MARKET_SELL_WHEAT
        if direction == "buy" and realm.gold < C.MARKET_BUY_GOLD:
            return "need %dg gold" % C.MARKET_BUY_GOLD
        return None

    def _transfer_target(self):
        """Choose the nearest other player holding for the local convoy."""
        if self.campaign is None or self.sid is None:
            return None
        holding = self._holding()
        candidates = [self.campaign.settlements[sid]
                      for sid in self.campaign.player.settlement_ids
                      if sid != self.sid and sid in self.campaign.settlements]
        if not candidates:
            return None
        return min(candidates, key=lambda other: (
            GEO.hex_distance(holding.hex, other.hex),
            other.id)).id

    def _transfer_reason(self, target_sid=None, resource="wheat"):
        """Dry-run label for the local-market convoy shown in this panel."""
        target_sid = target_sid or self._transfer_target()
        if target_sid is None:
            return "no other holding for this convoy"
        result = self.campaign.can_transfer_goods(self.sid, target_sid, resource)
        return None if result.ok else result.reason

    def _staff_reason(self, kind):
        realm = self._realm()
        if self._holding().buildings[kind].staffed:
            return None
        return None if self.campaign._can_spend_population(realm) else \
            "one idle resident must remain"

    def _build_buttons(self):
        holding, realm = self._holding(), self._realm()
        out = []
        for index, kind in enumerate(C.BUILDING_ROSTER):
            spec, building = C.BUILDINGS[kind], holding.buildings.get(kind)
            x, y = (16 if index < 5 else 356), 150 + (index % 5) * 34
            if building is not None:
                staff_reason = self._staff_reason(kind)
                was_staffed = building.staffed
                staff_label = ("Unstaff " if building.staffed else "Staff ") + self._bname(kind)
                out.append(Button(x, y, 145, 28, staff_label,
                                  lambda k=kind, staffed=was_staffed:
                                  self.do_unstaff(k) if staffed else self.do_staff(k),
                                  enabled=building.staffed or staff_reason is None))
                out.append(Button(x + 155, y, 145, 28,
                                  "Close " + self._bname(kind),
                                  lambda k=kind: self.do_close(k)))
            else:
                reason = self._build_reason(kind)
                label = "Build %s (%dg/%dw, %dm)" % (self._bname(kind),
                                                     spec["gold"], spec["wheat"], spec["months"])
                out.append(Button(x, y, 300, 28,
                                  self._with_reason(label, reason),
                                  lambda k=kind: self.do_build(k), enabled=reason is None))

        recruit_y = 320
        for x, field, label in ((16, False, "Recruit garrison"),
                                (356, True, "Recruit company")):
            reason = self._recruit_reason(field)
            out.append(Button(x, recruit_y, 320, 28,
                              self._with_reason(label + " (%dg, %dw, %d month)" %
                                                (C.RECRUIT_GOLD, C.RECRUIT_WHEAT,
                                                 C.RECRUIT_COST["months"]), reason),
                              self.do_recruit_c if field else self.do_recruit_g,
                              enabled=reason is None))
        target = self._nextsize()
        develop_reason = self._develop_reason() if target else "a City cannot develop further"
        out.append(Button(16, 356, 320, 28,
                          self._with_reason("Develop to %s" % (target or "City"), develop_reason),
                          self.do_develop, enabled=develop_reason is None))
        found_reason = self._found_reason()
        out.append(Button(356, 356, 320, 28,
                          self._with_reason("Found a village (map)", found_reason),
                          self.do_found, enabled=found_reason is None))
        sell_reason, buy_reason = self._market_reason("sell"), self._market_reason("buy")
        out.append(Button(16, 392, 320, 28,
                          self._with_reason("Sell %d wheat -> %d gold" %
                                             (C.MARKET_SELL_WHEAT, C.MARKET_SELL_GOLD), sell_reason),
                          self.do_sell, enabled=sell_reason is None))
        out.append(Button(356, 392, 320, 28,
                          self._with_reason("Buy %d wheat <- %d gold" %
                                             (C.MARKET_BUY_WHEAT, C.MARKET_BUY_GOLD), buy_reason),
                          self.do_buy, enabled=buy_reason is None))
        target_sid = self._transfer_target()
        target_name = (self.campaign.settlements[target_sid].name
                       if target_sid is not None else "other holding")
        for x, resource, label in ((16, "wheat", "Ship wheat"),
                                    (356, "gold", "Ship gold")):
            reason = self._transfer_reason(target_sid, resource)
            out.append(Button(x, 428, 320, 28,
                              self._with_reason("%s to %s" %
                                                (label, target_name), reason),
                              lambda r=resource, target=target_sid:
                              self.do_transfer(r, target),
                              enabled=reason is None))

        party = self.campaign.hero_party(realm.key)
        ids = list(party.unit_ids) if party else []
        start = self.unit_page * 6
        for index, uid in enumerate(ids[start:start + 6]):
            unit = self.campaign.units.get(uid)
            if unit is None or not unit.alive:
                continue
            y = 450 + index * 30
            train_reason = self._train_reason(uid)
            out.append(Button(16, y, 300, 26,
                              self._with_reason("Train " + unit.name, train_reason),
                              lambda i=uid: self.do_train(i), enabled=train_reason is None))
            kit = self._preferred_kit(unit)
            gear_reason = self._equip_reason(uid, kit)
            out.append(Button(326, y, 340, 26,
                              self._with_reason("Equip %s: %s" % (unit.name, C.KITS[kit]["name"]), gear_reason),
                              lambda i=uid, k=kit: self.do_gear(i, k), enabled=gear_reason is None))
        if self.unit_page > 0:
            out.append(Button(16, 650, 180, 28, "Previous warriors", self.previous_page))
        if start + 6 < len(ids):
            out.append(Button(210, 650, 180, 28, "More warriors", self.next_page))
        out.append(Button(16, 690, 320, 28, "Back to map", self.do_back))

        # --- garrison transfer (right column) ---------------------------
        gx = 676
        garrison = self.campaign.garrison_party(self.sid)
        garrison_ids = list(garrison.unit_ids) if garrison else []
        garrison_alive = [uid for uid in garrison_ids
                          if self.campaign.units.get(uid) and
                          self.campaign.units[uid].alive]
        gstart = self.garrison_page * 4
        for index, uid in enumerate(garrison_alive[gstart:gstart + 4]):
            unit = self.campaign.units[uid]
            reason = self._attach_reason(uid)
            out.append(Button(gx, 286 + index * 34, 288, 28,
                              self._with_reason("To company: %s" % unit.name[:18],
                                                reason),
                              lambda i=uid: self.do_attach(i),
                              enabled=reason is None))
        if self.garrison_page > 0:
            out.append(Button(gx, 286 + 4 * 34, 130, 26, "Previous",
                              self.previous_garrison_page))
        if gstart + 4 < len(garrison_alive):
            out.append(Button(gx + 140, 286 + 4 * 34, 130, 26, "More",
                              self.next_garrison_page))
        detach_ids = [uid for uid in ids
                      if self.campaign.units.get(uid) and
                      self.campaign.units[uid].alive]
        for index, uid in enumerate(detach_ids[:11]):
            unit = self.campaign.units[uid]
            reason = self._detach_reason(uid)
            out.append(Button(gx, 476 + index * 26, 588, 24,
                              self._with_reason(
                                  "%s (%s) - to garrison" %
                                  (unit.name[:18], unit.kit[:12]), reason),
                              lambda i=uid: self.do_detach(i),
                              enabled=reason is None))
        return out

    # garrison transfer actions
    def do_attach(self, uid):
        self._do(self.campaign.attach_to_hero(self.sid, uid))

    def do_detach(self, uid):
        self._do(self.campaign.detach_to_garrison(self.sid, uid))

    def next_garrison_page(self):
        self.garrison_page += 1

    def previous_garrison_page(self):
        self.garrison_page = max(0, self.garrison_page - 1)

    def next_page(self):
        self.unit_page += 1

    def previous_page(self):
        self.unit_page = max(0, self.unit_page - 1)

    def do_train(self, uid):
        self._do(self.campaign.order_train(uid, 1, focus=self._training_focus()))

    def do_gear(self, uid, kit):
        self._do(self.campaign.order_gear(uid, kit))

    def do_close(self, kind):
        self._do(self.campaign.close_building(self.sid, kind))

    def _can_build(self, kind):
        return self._build_reason(kind) is None

    def _do(self, result):
        if result is not None and getattr(result, "ok", False):
            self.app.audio.sfx("click")
            self.hint = getattr(result, "reason", "") or "done"
        else:
            self.app.audio.sfx("cant")
            self.hint = getattr(result, "reason", "") or "not allowed"

    def do_build(self, kind):
        self._do(self.campaign.order_build(self.sid, kind))

    def do_staff(self, kind):
        self._do(self.campaign.staff_building(self.sid, kind))

    def do_unstaff(self, kind):
        self._do(self.campaign.unstaff_building(self.sid, kind))

    def do_recruit_g(self):
        self._do(self.campaign.recruit_to_garrison(self.sid))

    def do_recruit_c(self):
        self._do(self.campaign.recruit_to_company(self.sid))

    def do_develop(self):
        self._do(self.campaign.order_develop(self.sid))

    def do_sell(self):
        self._do(self.campaign.convert_market(self.sid, "sell"))

    def do_buy(self):
        self._do(self.campaign.convert_market(self.sid, "buy"))

    def do_transfer(self, resource, target_sid=None):
        target_sid = target_sid or self._transfer_target()
        self._do(self.campaign.transfer_goods(self.sid, target_sid, resource))

    def do_found(self):
        self.app.found_mode = True
        self.app.mode = "campaign"
        self.app.campaign_screen.hint = "Found mode: click an empty adjacent plains or ruins hex"
        self.app.audio.sfx("click")

    def do_back(self):
        self.app.mode = "campaign"
        self.app.audio.sfx("close")

    def handle(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self._build_buttons():
                if button.hit(*event.pos):
                    button.on_click()
                    return
        elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_o):
            self.do_back()

    def draw(self, surface):
        draw_panel(surface, 0, 0, SCREEN_W, SCREEN_H)
        fonts, realm, holding = self.app.fonts, self._realm(), self._holding()
        draw_text(surface, fonts["big"], "%s (%s)" % (holding.name, holding.size),
                  24, 16, (40, 26, 14))
        draw_text(surface, fonts["small"],
                  "Gold %s    Wheat %s    Population %d" %
                  (_f(realm.gold), _f(realm.wheat), realm.population),
                  24, 64, (30, 30, 30))
        draw_text(surface, fonts["small"],
                  "Garrison cap %d    Slots %d free    morale mod %+d" %
                  (holding.garrison_cap(), holding.building_slots_free(),
                   holding.morale_effect()), 24, 84, (70, 60, 40))
        draw_text(surface, fonts["small"],
                  "Local stores: %d gold / %d wheat / %d residents" %
                  (holding.gold, holding.wheat, holding.population),
                  24, 104, (70, 60, 40))
        draw_text(surface, fonts["small"],
                  "Staffed Market ships %dg gold or %dw wheat to your other holdings" %
                  (C.MARKET_TRANSFER_GOLD, C.MARKET_TRANSFER_WHEAT),
                  24, 124, (70, 60, 40))
        for button in self._build_buttons():
            button.draw(surface, fonts["small"])
        draw_text(surface, fonts["small"], self.hint, 16, SCREEN_H - 40,
                  (150, 40, 30))
        # right column: orders, then garrison transfer, then the company
        draw_text(surface, fonts["small"], "Realm orders (heir: Court)",
                  676, 120, (40, 30, 20))
        y = 142
        for order in realm.orders[:6]:
            draw_text(surface, fonts["small"], "%s - %d months" %
                      (order.label(), order.months), 676, y, (60, 50, 34))
            y += 20
        if not realm.orders:
            draw_text(surface, fonts["small"], "none", 676, y, (90, 80, 60))
        garrison = self.campaign.garrison_party(self.sid)
        draw_text(surface, fonts["small"],
                  "Garrison %d/%d - attach to company" %
                  (len(garrison.unit_ids) if garrison else 0,
                   holding.garrison_cap()), 676, 262, (40, 30, 20))
        draw_text(surface, fonts["small"],
                  "Field company %d/%d - detach to garrison" %
                  (len(self.campaign.hero_party(realm.key).unit_ids)
                   if self.campaign.hero_party(realm.key) else 0,
                   C.COMPANY_CAP), 676, 452, (40, 30, 20))
        if self._hero_here() is None:
            draw_text(surface, fonts["small"],
                      "the hero company is not here", 676, 766, (120, 40, 30))
