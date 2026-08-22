"""Settlement screen: inspect buildings, staff, population, queues for
training/gear, recruit, develop, found (site chosen on the map), close
buildings - with disabled/illegal actions explained."""
import pygame

from tbb.rules import constants as C
from tbb.app.ui import draw_panel, draw_text, Button, SCREEN_W, SCREEN_H


def _f(v):
    return str(int(round(v))) if isinstance(v, float) else str(v)


class SettlementScreen:
    def __init__(self, app):
        self.app = app
        self.campaign = None
        self.sid = None
        self.hint = ""
        self._buttons = []

    def load(self, campaign, sid):
        self.campaign = campaign
        self.sid = sid
        self.hint = ""

    # ------------------------------------------------------------------
    def _holding(self):
        return self.campaign.settlements[self.sid]

    def _realm(self):
        return self.campaign._realm_of_settlement(self.sid)

    def _nextsize(self):
        h = self._holding()
        try:
            i = C.SIZE_ORDER.index(h.size)
        except ValueError:
            return None
        return C.SIZE_ORDER[i + 1] if i + 1 < len(C.SIZE_ORDER) else None

# ------------------------------------------------------------ buttons
    HUMAN_BUILDINGS = {
        "farm": "Farm", "granary": "Granary", "market": "Market",
        "militia_hall": "Militia Hall", "training_yard": "Training Yard",
        "smithy": "Smithy", "bowyer": "Bowyer", "walls": "Walls",
        "keep": "Keep", "chapel": "Chapel",
    }

    def _bname(self, kind):
        return self.HUMAN_BUILDINGS.get(kind, kind.replace("_", " ").title())

    def _build_buttons(self):
        h = self._holding()
        realm = self._realm()
        out = []
        # two columns of the locked building roster
        for i, kind in enumerate(C.BUILDING_ROSTER):
            spec = C.BUILDINGS[kind]
            b = h.buildings.get(kind)
            xx = 16 if i < 5 else 356
            yy = 150 + (i % 5) * 34
            if b is not None:
                if b.staffed:
                    label = "Close %s - 1 pop" % self._bname(kind)
                    cb = (lambda k=kind: self.do_close(k))
                else:
                    label = "Staff %s" % self._bname(kind)
                    cb = (lambda k=kind: self.do_staff(k))
                out.append(Button(xx, yy, 300, 28, label, cb))
            else:
                label = "Build %s (%dg %dm)" % (self._bname(kind),
                                                 spec["gold"],
                                                 spec["months"])
                out.append(Button(xx, yy, 300, 28, label,
                                  (lambda k=kind: self.do_build(k)),
                                  enabled=self._can_build(kind)))
        y = 290
        out.append(Button(16, y, 300, 28, "Recruit to garrison (10g,1w,folk)",
                          self.do_recruit_g))
        y += 32
        out.append(Button(16, y, 300, 28, "Recruit to company (hero here)",
                          self.do_recruit_c))
        y += 32
        if self._nextsize():
            nxt = self._nextsize()
            out.append(Button(16, y, 300, 28, "Develop to %s" % nxt.title(),
                              self.do_develop))
            y += 32
        out.append(Button(16, y, 300, 28, "Found a village (map)",
                          self.do_found))
        y += 36
        hp = self.campaign.hero_party(realm.key)
        field_ids = hp.unit_ids if hp else []
        train_max = self.campaign.player.training_slots(self.campaign.settlements)
        train_used = sum(1 for o in realm.orders if o.kind == "train")
        for uid in field_ids[:6]:
            u = self.campaign.units.get(uid)
            if u is None or not u.alive:
                continue
            if train_used < train_max:
                out.append(Button(16, y, 190, 26, "Drill %s" % u.name,
                                  lambda i=uid: self.do_train(i),
                                  enabled=self._can_train(uid)))
            kit = self._best_gear(u)
            if kit:
                out.append(Button(210, y, 210, 26,
                                  "Equip %s" % C.KITS[kit]["name"],
                                  lambda i=uid, k=kit: self.do_gear(i, k)))
            y += 30
        out.append(Button(16, y, 300, 28, "Back to map", self.do_back))
        return out

    def _train_full(self):
        realm = self._realm()
        used = sum(1 for o in realm.orders if o.kind == "train")
        total = self.campaign.player.training_slots(self.campaign.settlements)
        return used >= total

    def _can_train(self, uid):
        if self._train_full():
            return False
        hp = self.campaign.hero_party(self.campaign.player.key)
        if hp is None or uid not in hp.unit_ids:
            return False
        return True

    def _best_gear(self, u):
        realm = self._realm()
        if realm is None:
            return None
        can = realm.supplies(self.campaign.settlements)
        spec = C.KITS
        if u.stat("ranged") > u.stat("melee"):
            for kit in ("heavy_bow", "bow"):
                if spec[kit]["need"] and spec[kit]["need"] not in can:
                    continue
                if realm.gold >= spec[kit]["gold"] * 2:
                    return kit
        if "smithy" in can:
            for kit in ("two_hand", "heavy"):
                if realm.gold >= spec[kit]["gold"] * 2:
                    return kit
        if realm.gold >= spec["light"]["gold"] * 3:
            return "light"
        return None

    def do_train(self, uid):
        self._do(self.campaign.order_train(uid, 1))

    def do_gear(self, uid, kit):
        self._do(self.campaign.order_gear(uid, kit))

    def do_close(self, kind):
        self._do(self.campaign.close_building(self.sid, kind))

    def _can_build(self, kind):
        realm = self._realm()
        h = self._holding()
        if realm is None:
            return False
        if kind in h.buildings:
            return False
        if h.building_slots_free() <= 0:
            return False
        spec = C.BUILDINGS[kind]
        req = spec["req"]
        if req and h.size_index() < C.SIZE_ORDER.index(req):
            return False
        return realm.gold >= spec["gold"]

    # ------------------------------------------------------------ actions
    def _do(self, res):
        if res is not None and getattr(res, "ok", False):
            self.app.audio.sfx("click")
            self.hint = getattr(res, "reason", "") or "done"
        else:
            self.app.audio.sfx("cant")
            self.hint = getattr(res, "reason", "") or "not allowed"

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

    def do_found(self):
        self.app.found_mode = True
        self.app.mode = "campaign"
        self.app.campaign_screen.hint = ("Found mode: click empty plains "
                                         "beside your own land")
        self.app.audio.sfx("click")

    def do_back(self):
        self.app.mode = "campaign"
        self.app.audio.sfx("close")

    # ------------------------------------------------------------- events
    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            mx, my = ev.pos
            for b in self._build_buttons():
                if b.hit(mx, my):
                    b.on_click()
                    return
            # click a unit row in the right column -> designate heir
            realm = self._realm()
            units = realm.living_units(self.campaign.units)
            y0 = self._units_start_y()
            for i, u in enumerate(units):
                if 380 <= mx <= 780 and y0 + i * 18 <= my < y0 + (i + 1) * 18:
                    self._do(self.campaign.designate_heir(
                        None if realm.heir == u.id else u.id))
                    return
        elif ev.type == pygame.KEYDOWN:
            k = ev.key
            if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_o):
                self.app.mode = "campaign"
                self.app.audio.sfx("close")

    def _heir_start_y(self):
        realm = self._realm()
        y = 166 + len(realm.orders) * 20 + 32
        return y

    # --------------------------------------------------------------- draw
    def _units_start_y(self):
        realm = self._realm()
        return 166 + len(realm.orders) * 20 + 26

    def draw(self, surf):
        draw_panel(surf, 0, 0, SCREEN_W, SCREEN_H)
        f = self.app.fonts
        realm = self._realm()
        h = self._holding()
        draw_text(surf, f["big"], "%s (%s)" % (h.name, h.size), 24, 16,
                  (40, 26, 14))
        draw_text(surf, f["small"],
                  "Gold %s    Wheat %s    Population %d" % (
                      _f(realm.gold), _f(realm.wheat), realm.population),
                  24, 64, (30, 30, 30))
        draw_text(surf, f["small"],
                  "Garrison cap %d    Slots %d free    morale mod %+d" % (
                      h.garrison_cap(), h.building_slots_free(),
                      h.morale_effect()), 24, 84, (70, 60, 40))
        for b in self._build_buttons():
            b.draw(surf, f["small"])
        draw_text(surf, f["small"], self.hint, 16, SCREEN_H - 40,
                  (150, 40, 30))
        # orders panel on the right
        x = 380
        draw_text(surf, f["small"], "Realm orders:", x, 140, (40, 30, 20))
        y = 166
        for o in realm.orders:
            draw_text(surf, f["small"], "%s  -  %d months" %
                      (o.label(), o.months), x, y, (60, 50, 34))
            y += 20
        draw_text(surf, f["small"], "Heir:", x, y + 6, (40, 30, 20))
        y += 26
        for u in realm.living_units(self.campaign.units):
            tag = ("[hero]" if u.id == realm.hero else
                   "[heir]" if u.id == realm.heir else "")
            draw_text(surf, f["small"], "%s %s" % (tag, u.name), x, y,
                      (60, 50, 34))
            y += 18