"""Pure campaign rules: actions, monthly economy, contact and succession."""
from . import constants as C
from . import terrain as GEO
from . import talents as T
from . import names as N
from .calendar import Calendar
from .rng import RNG
from .settlements import Holding, Building, Order
from .units import Unit
from .realm import Realm
from .parties import Party
from . import worldgen

class Check:
    __slots__ = ("ok", "reason")
    def __init__(self, ok, reason=""):
        self.ok = bool(ok)
        self.reason = reason

    def __bool__(self):
        return self.ok

class Campaign:
    def __init__(self, seed=C.DEFAULT_SEED):
        self.seed = int(seed)
        self.rng = RNG(seed)
        self.calendar = Calendar()
        data = worldgen.generate(self.rng)
        self.world = data["world"]
        self.settlements = data["settlements"]
        self.realms = data["realms"]
        self.units = data["units"]
        self.parties = data["parties"]
        self.player = self.realms[C.PLAYER_REALM_KEY]
        self.turn = 0
        self.pending_battles = []
        self.notes = []
        self.ended = False
        self.end_reason = ""
        for party in self.parties:
            if party.kind in ("hero", "bandit"):
                party.mp = self._fresh_mp(party)

    def _new_id(self, values):
        return max(values, default=0) + 1
    def _fresh_mp(self, party):
        points = C.CAMPAIGN_MOVEMENT_POINTS
        on_road = self.world.terrain(party.hex) == C.TERRAIN_ROAD
        party.road_bonus = on_road
        if on_road:
            points += C.ROAD_MOVEMENT_BONUS
        if party.realm in self.realms and self.realms[party.realm].staffed(
                self.settlements, C.BUILDING_STABLES):
            points += C.STABLES_MOVE_BONUS
        return points
    def _new_uid(self):
        return self._new_id(self.units)

    def _new_sid(self):
        return self._new_id(self.settlements)

    def _new_pid(self):
        return max((p.pid for p in self.parties), default=0) + 1

    def settlement_at(self, pos):
        return next((h for h in self.settlements.values()
                     if h.hex == tuple(pos)), None)

    def settlement_id_at(self, pos):
        holding = self.settlement_at(pos)
        return holding.id if holding else None

    def hero_party(self, realm_key):
        return next((p for p in self.parties
                     if p.kind == "hero" and p.realm == realm_key), None)

    def garrison_party(self, settlement_id):
        return next((p for p in self.parties
                     if p.kind == "garrison" and
                     p.settlement_id == settlement_id), None)

    def living_in_party(self, party):
        return [self.units[i] for i in party.unit_ids
                if i in self.units and self.units[i].alive]

    def _realm_of_settlement(self, sid):
        holding = self.settlements.get(sid)
        if holding is None or holding.owner is None:
            return None
        return self.realms.get(holding.owner)

    def _realm_of_unit(self, uid):
        unit = self.units.get(uid)
        if unit is None or unit.realm is None:
            return None
        return self.realms.get(unit.realm)

    def _next_size(self, size):
        index = C.SIZE_ORDER.index(size)
        return (C.SIZE_ORDER[index + 1]
                if index + 1 < len(C.SIZE_ORDER) else None)

    def _unique_name(self, realm_key):
        names = {u.name for u in self.units.values() if u.realm == realm_key}
        return N.unique_warrior_name(self.rng, names)

    def _make_unit(self, realm_key, origin="the road", hero=False):
        uid = self._new_uid()
        base = self.rng.randint(34, 54) if hero else self.rng.randint(24, 45)
        stats = {
            "melee": base,
            "ranged": max(C.STAT_MIN, base - 3),
            "hit_points": base + 2,
            "fatigue": base + 3,
            "resolve": self.rng.randint(25, 55),
        }
        unit = Unit(uid, self._unique_name(realm_key), stats=stats, talents=T.roll_talents(self.rng),
                    origin=origin, age=self.rng.randint(16, 40), kit="light", realm=realm_key, is_hero=hero)
        self.units[uid] = unit
        return unit

    def move_party(self, party_id, target):
        party = next((p for p in self.parties if p.pid == party_id), None)
        if not party:
            return Check(False, "no such party")
        if party.realm != self.player.key:
            return Check(False, "that is not your party")
        if party.kind == "garrison":
            return Check(False, "a garrison stays put")
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self.player
        hero = realm.hero
        if (party.kind == "hero" and
                (hero is None or hero not in party.unit_ids or
                 not self.units[hero].alive)):
            return Check(False, "the field company needs a living hero")
        target = tuple(target)
        if target not in self.world.neighbours(party.hex):
            return Check(False, "that is not an adjacent hex")
        crossing = self.world.crossing(target)
        terrain = self.world.terrain(target)
        cost = GEO.move_cost(terrain, crossing)
        if cost is None:
            return Check(False, "no way through: rivers need a ford or bridge, mountains a pass")
        if terrain == C.TERRAIN_ROAD and not party.road_bonus:
            party.mp += C.ROAD_MOVEMENT_BONUS
            party.road_bonus = True
        if party.mp < cost:
            return Check(False, "no march left this month")
        party.mp -= cost
        party.move_to(target)
        self._scan_contacts_for(party)
        return Check(True)

    def _can_spend_population(self, realm, amount=1):
        staffed = realm_staffed(realm, self.settlements)
        idle_after = realm.population - staffed - amount
        return idle_after >= 1

    def _recruit(self, sid, field):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "that is not your settlement")
        holding = self.settlements[sid]
        cost = C.RECRUIT_COST
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold to recruit")
        if realm.wheat < cost["wheat"]:
            return Check(False, "not enough wheat to recruit")
        if not self._can_spend_population(realm, cost["population"]):
            return Check(False, "one idle resident must remain after staffing")
        if field:
            party = self.hero_party(realm.key)
            if not party or party.hex != holding.hex:
                return Check(False, "the hero is not at this settlement")
            queued = sum(1 for order in realm.orders
                         if order.kind == "recruit" and
                         order.kind_data == "field")
            if len(party.unit_ids) + queued >= C.COMPANY_CAP:
                return Check(False, "the field company is full (12 including the hero)")
        else:
            party = self.garrison_party(sid)
            queued = sum(1 for order in realm.orders
                         if order.kind == "recruit" and
                         order.kind_data == "garrison" and
                         order.settlement_id == sid)
            if not party or len(party.unit_ids) + queued >= holding.garrison_cap():
                return Check(False, "the garrison is full")
        realm.gold -= cost["gold"]
        realm.wheat -= cost["wheat"]
        realm.population -= cost["population"]
        realm.orders.append(Order("recruit", "field" if field else "garrison",
                                  cost["months"], settlement_id=sid))
        return Check(True, "recruit arrives after one whole month")

    def recruit_to_garrison(self, settlement_id):
        return self._recruit(settlement_id, False)

    def recruit_to_company(self, settlement_id):
        return self._recruit(settlement_id, True)

    def staff_building(self, sid, kind):
        realm = self._realm_of_settlement(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        building = self.settlements[sid].buildings.get(kind)
        if building is None:
            return Check(False, "building is not built")
        if building.staffed:
            return Check(False, "building is already staffed")
        if not self._can_spend_population(realm):
            return Check(False, "not enough residents; one idle worker must remain")
        building.staffed = True
        realm.population -= 1
        return Check(True)

    def unstaff_building(self, sid, kind):
        realm = self._realm_of_settlement(sid)
        building = self.settlements[sid].buildings.get(kind)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        if building is None:
            return Check(False, "building is not built")
        if building.staffed:
            building.staffed = False
            realm.population += 1
            return Check(True)
        return Check(True, "building was idle; no resident was occupied")

    def close_building(self, sid, kind):
        realm = self._realm_of_settlement(sid)
        holding = self.settlements.get(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        if kind not in holding.buildings:
            return Check(False, "building is not built")
        was_staffed = holding.buildings[kind].staffed
        holding.buildings.pop(kind)
        if was_staffed:
            realm.population += 1
        return Check(True)

    def order_build(self, sid, kind):
        realm = self._realm_of_settlement(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        holding = self.settlements[sid]
        if kind not in C.BUILDINGS:
            return Check(False, "unknown building")
        if kind in holding.buildings:
            return Check(False, "building already stands")
        if holding.building_slots_free() <= 0:
            return Check(False, "no building slots remain")
        req = C.BUILDINGS[kind]["req"]
        if req and holding.size_index() < C.SIZE_ORDER.index(req):
            return Check(False, f"{holding.size} cannot host this building; develop first")
        if any(order.kind == "build" and order.settlement_id == sid
               for order in realm.orders):
            return Check(False, "a building order is already in flight")
        cost = C.BUILDINGS[kind]
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < cost["wheat"]:
            return Check(False, "not enough wheat")
        realm.gold -= cost["gold"]
        realm.wheat -= cost["wheat"]
        realm.orders.append(Order("build", kind, cost["months"], sid))
        return Check(True)

    def order_develop(self, sid):
        realm = self._realm_of_settlement(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        holding = self.settlements[sid]
        target = self._next_size(holding.size)
        if not target:
            return Check(False, "a city cannot develop further")
        if any(order.kind == "develop" and order.settlement_id == sid
               for order in realm.orders):
            return Check(False, "development is already in progress")
        cost = C.DEVELOP_COST[(holding.size, target)]
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < cost["wheat"]:
            return Check(False, "not enough wheat")
        realm.gold -= cost["gold"]
        realm.wheat -= cost["wheat"]
        realm.orders.append(Order("develop", target, cost["months"], sid))
        return Check(True)

    def order_found(self, pos):
        pos = tuple(pos)
        realm = self.player
        if not self.world.in_bounds(pos):
            return Check(False, "that hex is outside the world")
        if self.settlement_at(pos):
            return Check(False, "this hex is already occupied")
        if not GEO.can_found(self.world.terrain(pos)):
            return Check(False, "founding requires empty plains, ruins, or farmland")
        if any(p.kind == "bandit" and p.hex == pos and
               p.alive_units(self.units) for p in self.parties):
            return Check(False, "robbers camp on that ground")
        adjacent = any(
            self.settlements[s].owner == realm.key and
            pos in self.world.neighbours(self.settlements[s].hex)
            for s in realm.settlement_ids
        )
        if not adjacent:
            return Check(False, "the village must touch your own land")
        if realm.gold < C.FOUND_COST["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < C.FOUND_COST["wheat"]:
            return Check(False, "not enough wheat")
        if not self._can_spend_population(realm, C.FOUND_COST["settlers"]):
            return Check(False, "not enough settlers while keeping workers")
        realm.gold -= C.FOUND_COST["gold"]
        realm.wheat -= C.FOUND_COST["wheat"]
        realm.population -= C.FOUND_COST["settlers"]
        realm.orders.append(Order("found", pos, C.FOUND_COST["months"]))
        return Check(True)

    def order_train(self, uid, months=1, focus=None, building=None):
        unit = self.units.get(uid)
        realm = self._realm_of_unit(uid)
        if not unit or not realm or not unit.alive:
            return Check(False, "the dead cannot train")
        if realm.key != self.player.key:
            return Check(False, "not your soldier")
        focus = focus or building or C.BUILDING_DRILL_YARD
        disciplines = (C.BUILDING_DRILL_YARD, C.BUILDING_SMITHY,
                       C.BUILDING_FLETCHER, C.BUILDING_STABLES)
        if focus not in disciplines:
            return Check(False, "no matching training discipline")
        if not realm.staffed(self.settlements, focus):
            return Check(False, "the matching building is not staffed")
        occupied = sum(1 for order in realm.orders if order.kind == "train")
        if occupied >= realm.training_slots(self.settlements):
            return Check(False, "all training slots are occupied")
        if any(order.kind == "train" and order.unit_id == uid
               for order in realm.orders):
            return Check(False, "this warrior already has a training order")
        realm.orders.append(Order("train", focus, months, unit_id=uid,
                                  focus=focus))
        return Check(True)

    def order_gear(self, uid, kit):
        unit = self.units.get(uid)
        realm = self._realm_of_unit(uid)
        if not unit or not realm or realm.key != self.player.key:
            return Check(False, "not your soldier")
        if kit not in C.KITS:
            return Check(False, "unknown kit")
        spec = C.KITS[kit]
        if spec["need"] and not realm.staffed(self.settlements, spec["need"]):
            return Check(False, f"a staffed {spec['need']} is required")
        if realm.gold < spec["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < spec["wheat"]:
            return Check(False, "not enough wheat")
        party = self.hero_party(realm.key)
        if not party or uid not in party.unit_ids:
            return Check(False, "only the field company can be equipped")
        if any(order.kind == "gear" and order.unit_id == uid
               for order in realm.orders):
            return Check(False, "this warrior already has an equipment order")
        realm.gold -= spec["gold"]
        realm.wheat -= spec["wheat"]
        realm.orders.append(Order("gear", kit, spec["months"], unit_id=uid))
        return Check(True)

    def attach_to_hero(self, sid, uid):
        realm = self._realm_of_settlement(sid)
        holding = self.settlements[sid]
        hero_party = self.hero_party(self.player.key)
        garrison = self.garrison_party(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        if not hero_party or hero_party.hex != holding.hex:
            return Check(False, "the hero is not here")
        if not garrison or uid not in garrison.unit_ids:
            return Check(False, "soldier is not in this garrison")
        if len(hero_party.unit_ids) >= C.COMPANY_CAP:
            return Check(False, "the company is full (12 including hero)")
        garrison.remove(uid)
        hero_party.add(uid)
        return Check(True)

    def detach_to_garrison(self, sid, uid):
        realm = self._realm_of_settlement(sid)
        holding = self.settlements[sid]
        hero_party = self.hero_party(self.player.key)
        garrison = self.garrison_party(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        if not hero_party or hero_party.hex != holding.hex:
            return Check(False, "the hero is not here")
        if uid == realm.hero:
            return Check(False, "the hero never garrisons")
        if uid not in hero_party.unit_ids:
            return Check(False, "soldier is not in the company")
        if len(garrison.unit_ids) >= holding.garrison_cap():
            return Check(False, "the garrison is full")
        hero_party.remove(uid)
        garrison.add(uid)
        return Check(True)

    def convert_market(self, sid, direction):
        realm = self._realm_of_settlement(sid)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        if not self.settlements[sid].has(C.BUILDING_MARKET):
            return Check(False, "a staffed market is required")
        if direction == "sell":
            if realm.wheat < C.MARKET_SELL_WHEAT:
                return Check(False, "not enough wheat to sell")
            realm.wheat -= C.MARKET_SELL_WHEAT
            realm.gold += C.MARKET_SELL_GOLD
        elif direction == "buy":
            if realm.gold < C.MARKET_BUY_GOLD:
                return Check(False, "not enough gold to buy wheat")
            realm.gold -= C.MARKET_BUY_GOLD
            realm.wheat += C.MARKET_BUY_WHEAT
        else:
            return Check(False, "trade direction must be sell or buy")
        return Check(True)

    def designate_heir(self, uid=None):
        realm = self.player
        if uid is not None:
            if uid not in realm.unit_ids or not self.units[uid].alive:
                return Check(False, "only a living soldier may inherit")
            if uid == realm.hero:
                return Check(False, "the hero already rules")
        for unit_id in realm.unit_ids:
            self.units[unit_id].is_heir = False
        realm.heir = uid
        if uid is not None:
            self.units[uid].is_heir = True
        return Check(True)

    def end_turn(self):
        if self.ended:
            return Check(False, self.end_reason)
        if any(not battle.over() for battle in self.pending_battles):
            return Check(False, "resolve the pending battle first")
        self.pending_battles = []
        self.turn += 1
        self.calendar.advance()
        self.notes = []
        if self.calendar.month == 0:
            for unit in self.units.values():
                if unit.alive:
                    unit.age_one_year()
        for unit in self.units.values():
            if unit.shaken:
                unit.shaken = False
        for unit in self.units.values():
            unit.heal_month()
        for party in self.parties:
            if party.kind in ("hero", "bandit"):
                party.mp = self._fresh_mp(party)
        for realm in self.realms.values():
            self._resolve_realm_month(realm)
        self._ai_and_bandit_turn()
        self.check_end_conditions()
        return Check(True, self.calendar.label())

    def _local_population(self, realm, holding):
        share = realm.population // max(1, len(realm.settlement_ids))
        return min(holding.pop_cap(), max(0, share))

    def _account(self, realm):
        holdings = realm.holdings(self.settlements)
        capacity = realm.holdings_cap(self.settlements)
        produced = sum(holding.food_produced(self._local_population(realm, holding))
                       for holding in holdings)
        living = len(realm.living_units(self.units))
        food_need = (realm.population * C.POP_FOOD_PER_MONTH +
                     living * C.WARRIOR_FOOD_UPKEEP)
        realm.wheat += produced
        remainder = realm.wheat - food_need
        if remainder < 0:
            realm.wheat = 0
            realm.morale += C.STARVATION_MORALE
            realm.population = max(0, realm.population - max(1, int(-remainder)))
        else:
            granaries = sum(1 for holding in holdings
                            if holding.has(C.BUILDING_GRANARY))
            spoilage = max(0.0, C.SPOILAGE_RATE -
                           granaries * C.GRANARY_SPOILAGE_REDUCTION)
            realm.wheat = max(0.0, remainder * (1 - spoilage))
        due = (living * C.WARRIOR_GOLD_UPKEEP +
               realm.building_upkeep(self.settlements))
        realm.gold -= due
        if realm.gold < 0:
            realm.gold = 0
            realm.morale += C.UNPAID_UPKEEP_MORALE
        if realm.population >= capacity:
            realm.population_fraction = 0.0
        elif realm.wheat > 0:
            growth = ((realm.population * C.BIRTH_RATE +
                       realm.population * C.IMMIGRATION_RATE) *
                      (realm.morale / 100.0)) + realm.population_fraction
            whole = int(growth)
            realm.population = min(capacity,
                                   realm.population + whole)
            if realm.population >= capacity:
                realm.population_fraction = 0.0
            else:
                realm.population_fraction = growth - whole
        realm.morale = max(0, min(
            100, realm.morale + realm.morale_from_holdings(self.settlements)))

    def _resolve_realm_month(self, realm):
        if realm.destroyed:
            return
        self._account(realm)
        self._advance_orders(realm)
        self._ensure_succession(realm)

    def _advance_orders(self, realm):
        done = []
        for order in realm.orders:
            order.months -= 1
            if order.months <= 0:
                done.append(order)
        realm.orders = [o for o in realm.orders if o.months > 0]
        for order in done:
            self._complete_order(realm, order)

    def _complete_order(self, realm, order):
        if order.kind == "build":
            holding = self.settlements[order.settlement_id]
            holding.buildings[order.kind_data] = Building(order.kind_data)
        elif order.kind == "recruit":
            holding = self.settlements[order.settlement_id]
            unit = self._make_unit(realm.key, holding.name)
            unit.kit = ("shield_onehander" if self.rng.random() < 0.5
                        else "light")
            realm.unit_ids.add(unit.id)
            party = (self.hero_party(realm.key)
                     if order.kind_data == "field" else
                     self.garrison_party(order.settlement_id))
            allowed = bool(party)
            if allowed and order.kind_data == "field":
                allowed = len(party.unit_ids) < C.COMPANY_CAP
            if allowed and order.kind_data == "garrison":
                allowed = len(party.unit_ids) < holding.garrison_cap()
            if allowed:
                party.add(unit.id)
        elif order.kind == "develop":
            self.settlements[order.settlement_id].size = order.kind_data
        elif order.kind == "found":
            names = {holding.name for holding in self.settlements.values()}
            holding = Holding(self._new_sid(), N.unique_settlement_name(self.rng, names),
                              order.kind_data, C.SIZE_V, realm.key)
            self.settlements[holding.id] = holding
            realm.settlement_ids.append(holding.id)
            self.world.set_terrain(holding.hex, C.TERRAIN_VILLAGE)
            self.parties.append(Party(self._new_pid(), "garrison", realm.key,
                                      holding.hex, (), holding.id))
        elif order.kind == "train":
            unit = self.units.get(order.unit_id)
            if unit and unit.alive:
                unit.gain_from_training(self.rng, order.focus)
        elif order.kind == "gear":
            unit = self.units.get(order.unit_id)
            if unit and unit.alive:
                unit.kit = order.kind_data

    def _ensure_succession(self, realm):
        if realm is None:
            return
        hero = self.units.get(realm.hero) if realm.hero is not None else None
        if hero and hero.alive:
            return
        heir = self.units.get(realm.heir) if realm.heir is not None else None
        if heir and heir.alive:
            new = heir
            if hero:
                hero.is_hero = False
            new.is_hero = True
            new.is_heir = False
            realm.hero = new.id
            realm.heir = None
            realm.morale = max(0, realm.morale + C.MORALE_HEIR_SUCCESSION)
            party = self.hero_party(realm.key)
            if party and new.id not in party.unit_ids:
                if hero and hero.id in party.unit_ids:
                    party.remove(hero.id)
                for other in self.parties:
                    if other is not party:
                        other.remove(new.id)
                if len(party.unit_ids) < C.COMPANY_CAP:
                    party.add(new.id)
            for uid in realm.unit_ids:
                unit = self.units.get(uid)
                if unit is not None and unit.alive and unit.id != new.id:
                    unit.shaken = True
            if realm.key == self.player.key:
                self.notes.append(
                    "%s falls; %s succeeds as heir (morale %d)"
                    % (hero.name if hero else "the old hero", new.name,
                       C.MORALE_HEIR_SUCCESSION))
            return
        if realm.can_raise_hero(self.settlements):
            new = self._make_unit(realm.key, "the council", True)
            if hero:
                hero.is_hero = False
            realm.hero = new.id
            realm.unit_ids.add(new.id)
            realm.morale = max(0, realm.morale + C.MORALE_NEW_COMMANDER)
            party = self.hero_party(realm.key)
            if party:
                if hero and hero.id in party.unit_ids:
                    party.remove(hero.id)
                for other in self.parties:
                    if other is not party:
                        other.remove(new.id)
                if len(party.unit_ids) < C.COMPANY_CAP:
                    party.add(new.id)
            for uid in realm.unit_ids:
                unit = self.units.get(uid)
                if unit is not None and unit.alive and unit.id != new.id:
                    unit.shaken = True
            if realm.key == self.player.key:
                self.notes.append(
                    "no heir lived; the council raises %s (morale %d)"
                    % (new.name, C.MORALE_NEW_COMMANDER))
        else:
            realm.hero = None

    def _parties_hostile(self, a, b):
        if a.realm is None and b.realm is None:
            return False
        if a.realm is None or b.realm is None:
            return True
        return a.realm != b.realm

    def _scan_contacts_for(self, party):
        h = self.settlement_at(party.hex)
        if h and party.kind == "hero" and h.owner != party.realm:
            self._start_assault(party, self.garrison_party(h.id), h.id)
        elif h and party.kind == "bandit":
            if h.owner is not None:
                self._bandit_raid(party, h.id)
            else:
                guard = self.garrison_party(h.id)
                raiders = sum(self.units[i].stat("melee")
                              for i in party.unit_ids
                              if self.units[i].alive)
                defenders = sum(self.units[i].stat("melee")
                                for i in guard.unit_ids
                                if self.units[i].alive) if guard else 0
                if guard and guard.unit_ids and raiders > defenders:
                    self._make_battle(party, guard, True)
        for other in self.parties:
            if (other.pid != party.pid and other.kind != "garrison" and
                    other.hex == party.hex and
                    self._parties_hostile(party, other)):
                self._make_battle(party, other, False)

    def _bandit_raid(self, party, sid):
        realm = self._realm_of_settlement(sid)
        if realm is None:
            return
        stolen_w = min(6, int(realm.wheat))
        stolen_g = min(4, int(realm.gold))
        realm.wheat -= stolen_w
        realm.gold -= stolen_g
        self.notes.append(f"robbers sack {self.settlements[sid].name}: -{stolen_w} wheat, -{stolen_g} gold")
        guard = self.garrison_party(sid)
        if guard and guard.unit_ids:
            raiders = sum(self.units[i].stat("melee") for i in party.unit_ids
                          if self.units[i].alive)
            defenders = sum(self.units[i].stat("melee") for i in guard.unit_ids
                            if self.units[i].alive)
            if raiders > defenders:
                self._make_battle(party, guard, True)

    def _start_assault(self, attacker, guard, sid):
        if guard and guard.unit_ids:
            self._make_battle(attacker, guard, True)
        else:
            self._conquer(sid, attacker.realm)

    def _conquer(self, sid, realm_key):
        holding = self.settlements[sid]
        old = holding.owner
        if (old is not None and old in self.realms and
                sid in self.realms[old].settlement_ids):
            self.realms[old].settlement_ids.remove(sid)
        holding.owner = realm_key
        if (realm_key is not None and
                sid not in self.realms[realm_key].settlement_ids):
            self.realms[realm_key].settlement_ids.append(sid)
        player_key = self.player.key
        if realm_key == player_key:
            self.notes.append("%s is taken by your banner" % holding.name)
        elif old == player_key:
            self.notes.append("%s is lost to %s"
                              % (holding.name,
                                 self.realms[realm_key].name
                                 if realm_key is not None else "robbers"))

    def _make_battle(self, a, d, assault=False):
        from . import battle as B
        b = B.battle_from_contact(self, a, d, assault)
        if not b:
            return None
        if self.player.key in (a.realm, d.realm):
            self.pending_battles.append(b)
        else:
            b.auto_resolve(self.rng)
            self.resolve_battle(b)
        return b

    def resolve_battle(self, battle):
        from . import battle as B
        B.writeback(self, battle)

    def auto_resolve_pending(self):
        for battle in list(self.pending_battles):
            if not battle.over():
                battle.auto_resolve(self.rng)
            self.resolve_battle(battle)
        self.pending_battles = []

    def discard_pending(self, battle):
        if battle in self.pending_battles:
            self.pending_battles.remove(battle)

    def check_end_conditions(self):
        for realm in self.realms.values():
            hero = self.units.get(realm.hero) if realm.hero is not None else None
            heir = self.units.get(realm.heir) if realm.heir is not None else None
            no_holdings = not realm.settlement_ids
            no_line = not (hero and hero.alive) and not (heir and heir.alive)
            if no_holdings and no_line:
                realm.destroyed = True
        if self.player.destroyed:
            self.ended = True
            self.end_reason = "defeat"
        elif all(realm.destroyed for key, realm in self.realms.items()
                 if key != self.player.key):
            self.ended = True
            self.end_reason = "victory"

    def check_player_hero(self):
        self._ensure_succession(self.player)

    def _ai_and_bandit_turn(self):
        """Run one autonomous month through the shared pure-rule AI loop."""
        from . import ai
        ai.run_ai_turn(self)

    def path_to(self, start, goal, mp=None):
        from . import pathfind
        return pathfind.a_star(self.world, start, goal)

    @property
    def width(self):
        return self.world.width

    @property
    def height(self):
        return self.world.height

    def morale_bonus(self, realm):
        return self.realms[realm].morale

    def realm_info(self, key):
        realm = self.realms[key]
        party = self.hero_party(key)
        return {
            "gold": realm.gold,
            "wheat": realm.wheat,
            "pop": realm.population,
            "morale": realm.morale,
            "name": realm.name,
            "holdings": [self.settlements[sid].name
                         for sid in realm.settlement_ids],
            "company": len(self.living_in_party(party)) if party else 0,
        }


def realm_staffed(realm, settlements):
    return sum(holding.staff_needed() for holding in realm.holdings(settlements))
