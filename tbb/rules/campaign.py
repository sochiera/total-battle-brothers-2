"""The Campaign: owns world, realms, settlements, units and parties, and every
rules action. The UI calls these methods; presentation only reads state.
Everything is deterministic given the seed.
"""
from . import constants as C
from . import terrain as GEO
from . import talents as T
from . import names as N
from . import worldgen
from .calendar import Calendar
from .rng import RNG
from .settlements import Holding, Building, Order
from .units import Unit
from .realm import Realm
from .parties import Party

class Check:
    __slots__ = ("ok", "reason")

    def __init__(self, ok, reason=""):
        self.ok = ok
        self.reason = reason

    def __bool__(self):
        return self.ok


class Campaign:
    def __init__(self, seed=C.DEFAULT_SEED):
        self.seed = int(seed)
        self.rng = RNG(self.seed)
        self.calendar = Calendar()
        gen = worldgen.generate(self.rng)
        self.world = gen["world"]
        self.settlements = gen["settlements"]
        self.realms = gen["realms"]
        self.units = gen["units"]
        self.parties = gen["parties"]
        self.player = self.realms[C.PLAYER_REALM_KEY]
        for p in self.parties:
            if p.kind in ("hero", "bandit"):
                p.mp = C.CAMPAIGN_MOVEMENT_POINTS
        self.turn = 0
        self.ended = False
        self.end_reason = ""
        self.pending_battles = []
        self.notes = []

    # --------------------------------------------------------------- ids
    def _new_uid(self):
        ids = self.units.keys()
        return (max(ids) if ids else 0) + 1

    def _new_sid(self):
        ids = self.settlements.keys()
        return (max(ids) if ids else 0) + 1

    def _new_pid(self):
        ids = [p.pid for p in self.parties]
        return (max(ids) if ids else 0) + 1

    # ------------------------------------------------------------ lookups
    def settlement_at(self, pos):
        pos = tuple(pos)
        for h in self.settlements.values():
            if tuple(h.hex) == pos:
                return h
        return None

    def settlement_id_at(self, pos):
        h = self.settlement_at(pos)
        for sid, s in self.settlements.items():
            if s is h:
                return sid
        return None

    def hero_party(self, realm_key):
        for p in self.parties:
            if p.realm == realm_key and p.kind == "hero":
                return p
        return None

    def garrison_party(self, settlement_id):
        for p in self.parties:
            if p.kind == "garrison" and p.settlement_id == settlement_id:
                return p
        return None

    def living_in_party(self, party):
        return [self.units[u] for u in party.unit_ids
                if u in self.units and self.units[u].alive]

    def _realm_of_settlement(self, sid):
        h = self.settlements[sid]
        if h.owner is None:
            return None
        return self.realms[h.owner]

    def _realm_of_unit(self, unit_id):
        u = self.units[unit_id]
        if u.realm is None:
            return None
        return self.realms[u.realm]

    def _next_size(self, size):
        try:
            i = C.SIZE_ORDER.index(size)
        except ValueError:
            return None
        if i + 1 >= len(C.SIZE_ORDER):
            return None
        return C.SIZE_ORDER[i + 1]

    def _unique_name(self, realm_key):
        taken = set()
        for u in self.units.values():
            if u.realm == realm_key:
                taken.add(u.name)
        return N.unique_warrior_name(self.rng, taken)

    # ------------------------------------------------------------ act: move
    def move_party(self, party_id, target):
        """March one hex; a step must save movement points. Contact is checked
        afterwards; player-involving battles join pending_battles."""
        p = next((q for q in self.parties if q.pid == party_id), None)
        if p is None:
            return Check(False, "no such party")
        if p.realm != self.player.key:
            return Check(False, "that is not your party")
        if p.kind == "garrison":
            return Check(False, "a garrison stays put")
        if self.ended:
            return Check(False, "the campaign has ended")
        # a field company marches only with its living hero at its head
        realm = self.realms[p.realm]
        if p.kind == "hero" and (realm.hero is None or
                                 not self.units[realm.hero].alive or
                                 realm.hero not in p.unit_ids):
            return Check(False, "no living hero leads this company")
        if tuple(target) not in GEO.neighbours(*p.hex, self.world.width,
                                               self.world.height):
            return Check(False, "that is not an adjacent hex")
        terrain = self.world.terrain(tuple(target))
        cost = C.MOVE_COST[terrain]
        if cost is None:
            return Check(False, "you cannot march into open water")
        if p.mp < cost:
            return Check(False, "no march left this month")
        p.mp -= cost
        p.move_to(tuple(target))
        self._scan_contacts_for(p)
        return Check(True)

    # ------------------------------------------------------------ act: recruit
    def recruit_to_garrison(self, settlement_id):
        return self._recruit(settlement_id, field=False)

    def recruit_to_company(self, settlement_id):
        return self._recruit(settlement_id, field=True)

    def _recruit(self, settlement_id, field):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None:
            return Check(False, "you do not hold this land")
        if realm.key != self.player.key:
            return Check(False, "that is not your settlement")
        h = self.settlements[settlement_id]
        if realm.gold < C.RECRUIT_GOLD:
            return Check(False, "not enough gold")
        if realm.wheat < C.RECRUIT_WHEAT:
            return Check(False, "not enough wheat")
        if realm.population < 1:
            return Check(False, "no idle folk to call up")
        if field:
            hp = self.hero_party(realm.key)
            if hp is None or tuple(hp.hex) != tuple(h.hex):
                return Check(False, "the hero is not at this settlement")
            if hp.size() >= 1 + C.COMPANY_CAP:
                return Check(False, "the field company is at full strength")
        else:
            gp = self.garrison_party(settlement_id)
            if gp is None:
                return Check(False, "no garrison post here")
            if len(gp.unit_ids) >= h.garrison_cap():
                return Check(False, "the garrison is full")
        u = self._make_unit(realm.key)
        if field:
            self.hero_party(realm.key).add(u.id)
        else:
            self.garrison_party(settlement_id).add(u.id)
        realm.unit_ids.add(u.id)
        realm.gold -= C.RECRUIT_GOLD
        realm.wheat -= C.RECRUIT_WHEAT
        realm.population -= 1
        return Check(True, u.name)

    def _make_unit(self, realm_key, hero=False, stats=None):
        uid = self._new_uid()
        name = self._unique_name(realm_key)
        if stats is None:
            base = self.rng.randint(34, 58) if hero else self.rng.randint(24, 46)
            stats = {
                "melee": base + self.rng.randint(-6, 12),
                "ranged": base + self.rng.randint(-10, 8),
                "toughness": base + self.rng.randint(-4, 8),
                "fatigue": base + self.rng.randint(-2, 10),
                "resolve": self.rng.randint(22, 50),
                "initiative": base + self.rng.randint(-8, 6),
            }
            stats = {k: min(C.STAT_MAX, max(C.STAT_MIN, v))
                     for k, v in stats.items()}
        tal = T.roll_talents(self.rng)
        u = Unit(uid, name, stats["melee"], stats["ranged"],
                 stats["toughness"], stats["fatigue"], stats["resolve"],
                 stats["initiative"], tal, realm=realm_key)
        if hero:
            u.is_hero = True
        self.units[uid] = u
        return u

    # ------------------------------------------------------------ act: attach
    def attach_to_hero(self, settlement_id, unit_id):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        hp = self.hero_party(realm.key)
        if hp is None or tuple(hp.hex) != tuple(h.hex):
            return Check(False, "the hero is not here")
        gp = self.garrison_party(settlement_id)
        if gp is None or unit_id not in gp.unit_ids:
            return Check(False, "that soldier is not in this garrison")
        if hp.size() >= 1 + C.COMPANY_CAP:
            return Check(False, "the company is at full strength")
        gp.remove(unit_id)
        hp.add(unit_id)
        return Check(True)

    def detach_to_garrison(self, settlement_id, unit_id):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        hp = self.hero_party(realm.key)
        if hp is None or tuple(hp.hex) != tuple(h.hex):
            return Check(False, "the hero is not here")
        if unit_id not in hp.unit_ids:
            return Check(False, "that soldier is not in the field company")
        if unit_id == realm.hero:
            return Check(False, "the hero never garrisons")
        gp = self.garrison_party(settlement_id)
        if gp is None:
            return Check(False, "no garrison post")
        if len(gp.unit_ids) >= h.garrison_cap():
            return Check(False, "the garrison is full")
        hp.remove(unit_id)
        gp.add(unit_id)
        return Check(True)

    # ------------------------------------------------------------- buildings
    def order_build(self, settlement_id, kind):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        if kind not in C.BUILDINGS:
            return Check(False, "unknown building")
        if kind in h.buildings:
            return Check(False, "it already stands")
        if h.building_slots_free() <= 0:
            return Check(False, "no room for more building")
        req = C.BUILDINGS[kind]["req"]
        if req and h.size_index() < C.SIZE_ORDER.index(req):
            return Check(False, "a %s cannot hold that" % h.size)
        if any(o.kind == "build" and o.kind_data == kind
               and o.settlement_id == settlement_id for o in realm.orders):
            return Check(False, "already ordered")
        cost = C.BUILDINGS[kind]
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < cost.get("wheat", 0):
            return Check(False, "not enough wheat")
        realm.gold -= cost["gold"]
        realm.wheat -= cost.get("wheat", 0)
        realm.orders.append(Order("build", kind, cost["months"],
                                  settlement_id=settlement_id))
        return Check(True)

    def staff_building(self, settlement_id, kind):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        b = h.buildings.get(kind)
        if b is None:
            return Check(False, "not built yet")
        if b.staffed:
            return Check(False, "already staffed")
        if realm.population < 1:
            return Check(False, "no idle folk to man it")
        realm.population -= 1
        b.staffed = True
        return Check(True)

    def unstaff_building(self, settlement_id, kind):
        """Take the craftsperson off the payroll: the building stands idle
        and no longer grants its effect; 1 population returns to the pool."""
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        b = self.settlements[settlement_id].buildings.get(kind)
        if b is None or not b.staffed:
            return Check(False, "no staffed building to close")
        b.staffed = False
        realm.population += 1
        return Check(True)

    def close_building(self, settlement_id, kind):
        """Tear the building down: it leaves the holding, a building slot
        frees up, and 1 population of residents returns to the pool."""
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        b = h.buildings.get(kind)
        if b is None:
            return Check(False, "no such building stands")
        h.buildings.pop(kind, None)
        realm.population += 1
        return Check(True)

    def order_develop(self, settlement_id):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self._realm_of_settlement(settlement_id)
        if realm is None or realm.key != self.player.key:
            return Check(False, "not your holding")
        h = self.settlements[settlement_id]
        target = self._next_size(h.size)
        if target is None:
            return Check(False, "this is already a city")
        if any(o.kind == "develop" and o.settlement_id == settlement_id
               for o in realm.orders):
            return Check(False, "growth is already ordered")
        key = (h.size, target)
        cost = C.DEVELOP_COST[key]
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < cost["wheat"]:
            return Check(False, "not enough wheat")
        realm.gold -= cost["gold"]
        realm.wheat -= cost["wheat"]
        realm.orders.append(Order("develop", target, cost["months"],
                                  settlement_id=settlement_id))
        return Check(True)

    def order_found(self, pos):
        pos = tuple(pos)
        realm = self.player
        if self.ended:
            return Check(False, "the campaign has ended")
        if not GEO.can_found(self.world.terrain(pos)):
            return Check(False, "only empty plains can be settled")
        if self.settlement_at(pos) is not None:
            return Check(False, "this land is already taken")
        adj = GEO.neighbours(*pos, self.world.width, self.world.height)
        for n in adj:
            sid = self.settlement_id_at(n)
            if sid is not None and self.settlements[sid].owner == self.player.key:
                break
        else:
            return Check(False, "found a village beside your own land")
        cost = C.FOUND_COST
        if realm.gold < cost["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < cost["wheat"]:
            return Check(False, "not enough wheat")
        if realm.population < cost["pop"]:
            return Check(False, "not enough free folk to seed the site")
        realm.gold -= cost["gold"]
        realm.wheat -= cost["wheat"]
        realm.population -= cost["pop"]
        realm.orders.append(Order("found", pos, cost["months"]))
        return Check(True)

    # ------------------------------------------------------------- training
    def order_train(self, unit_id, months=1):
        realm = self._realm_of_unit(unit_id)
        if realm is None:
            return Check(False, "not one of your soldiers")
        u = self.units[unit_id]
        if not u.alive:
            return Check(False, "the dead do not drill")
        if self.ended:
            return Check(False, "the campaign has ended")
        hp = self.hero_party(self.player.key)
        if hp is None or (unit_id not in hp.unit_ids and
                          unit_id != self.player.hero):
            return Check(False, "only the field company may train")
        total = self.player.training_slots(self.settlements)
        if self._train_slots_used() >= total:
            return Check(False, "every training yard is occupied")
        self.player.orders.append(Order("train", months, months,
                                        unit_id=unit_id))
        return Check(True)

    def _train_slots_used(self):
        return sum(1 for o in self.player.orders if o.kind == "train")

    def order_gear(self, unit_id, kit):
        realm = self._realm_of_unit(unit_id)
        if realm is None:
            return Check(False, "not your soldier")
        if kit not in C.KITS or kit == C.KIT_POOR:
            return Check(False, "no such kit")
        spec = C.KITS[kit]
        if spec["need"] and spec["need"] not in self.player.supplies(
                self.settlements):
            return Check(False, "your realm does not outfit this kit")
        if realm.gold < spec["gold"]:
            return Check(False, "not enough gold")
        if realm.wheat < spec["wheat"]:
            return Check(False, "not enough wheat")
        hp = self.hero_party(self.player.key)
        if hp is None or unit_id not in hp.unit_ids:
            return Check(False, "only the field company is outfitted")
        realm.gold -= spec["gold"]
        realm.wheat -= spec["wheat"]
        realm.orders.append(Order("gear", kit, spec["months"], unit_id=unit_id))
        return Check(True)

    def designate_heir(self, unit_id=None):
        if self.ended:
            return Check(False, "the campaign has ended")
        realm = self.player
        if unit_id is not None and unit_id not in realm.unit_ids:
            return Check(False, "not your soldier")
        if unit_id is not None and not self.units[unit_id].alive:
            return Check(False, "the dead cannot inherit")
        if unit_id == realm.hero:
            return Check(False, "the hero rules already")
        realm.heir = unit_id
        for u in list(realm.unit_ids):
            self.units[u].is_heir = False
        if unit_id is not None:
            self.units[unit_id].is_heir = True
        return Check(True)

    # -------------------------------------------------------- monthly sim
    def end_turn(self):
        """End the act phase; resolve one whole new month for every realm."""
        if self.ended:
            return Check(False, self.end_reason)
        if any(not b.over() for b in self.pending_battles):
            return Check(False, "resolve the engagement first")
        self.pending_battles = [b for b in self.pending_battles if not b.over()]
        self.turn += 1
        self.calendar.advance()
        self.notes = []
        for r in self.realms.values():
            r.drop_notes = []
        for p in self.parties:
            if p.kind in ("hero", "bandit"):
                p.mp = C.CAMPAIGN_MOVEMENT_POINTS
        for key in sorted(self.realms):
            self._resolve_realm_month(self.realms[key])
        self._ai_and_bandit_turn()
        self.check_end_conditions()
        return Check(True, "%s started" % self.calendar.label())

    def _resolve_realm_month(self, realm):
        if realm is None or realm.destroyed:
            return
        self._account(realm)
        self._advance_orders(realm)
        self._ensure_succession(realm)

    # --- economy & population (see constants for every number) ---
    def _account(self, realm):
        food = realm.food_income(self.settlements)
        gold = realm.gold_income(self.settlements)
        units = realm.living_units(self.units)
        pop_food = realm.population * C.POP_FOOD_PER_UNIT
        units_food = len(units) * C.UPKEEP_WHEAT_PER_UNIT
        units_gold = len(units) * C.UPKEEP_GOLD_PER_UNIT
        upkeep = realm.building_upkeep(self.settlements)
        gold_needed = units_gold + upkeep
        food_needed = pop_food + units_food
        realm.gold += gold - gold_needed
        if realm.gold < 0:
            realm.morale += C.UNPAID_MORALE
            realm.drop_notes.append("unpaid upkeep gnaws the realm")
            realm.gold = 0
        realm.wheat += food - food_needed
        if realm.wheat < 0:
            short = -realm.wheat
            realm.morale += C.STARVATION_MORALE
            loss = max(1, int(round(short * 0.5)))
            realm.population = max(0, realm.population - loss)
            realm.drop_notes.append("starvation empties the villages")
            realm.wheat = 0
        self._population_growth(realm)
        realm.morale += realm.morale_from_holdings(self.settlements)
        realm.morale = max(0, min(100, realm.morale))

    def _population_growth(self, realm):
        cap = realm.holdings_cap(self.settlements)
        pop = realm.population
        if pop >= cap:
            return
        births = pop * C.BIRTH_RATE
        wheat = realm.wheat - pop * C.POP_FOOD_PER_UNIT
        surplus = max(0, wheat)
        immig = pop * C.IMMIG_RATE * (1 + surplus * 0.02)
        chapel = 0
        for sid in realm.settlement_ids:
            if self.settlements[sid].has(C.BUILDING_CHAPEL):
                chapel += pop * C.CHAPEL_BIRTH
        growth = (births + immig + chapel) * (realm.morale / 100.0)
        if growth > 0:
            realm.population = min(realm.population + int(growth), cap)

    # --- orders ---------------------------------------------------------
    def _advance_orders(self, realm):
        done = []
        for o in realm.orders:
            o.months -= 1
            if o.months <= 0:
                done.append(o)
        realm.orders = [o for o in realm.orders if o.months > 0]
        for o in done:
            self._complete_order(realm, o)

    def _complete_order(self, realm, o):
        if o.kind == "build":
            h = self.settlements[o.settlement_id]
            h.buildings[o.kind_data] = Building(o.kind_data)
        elif o.kind == "develop":
            h = self.settlements[o.settlement_id]
            h.size = o.kind_data
        elif o.kind == "found":
            self._found_village_land(realm, o.kind_data)
        elif o.kind == "train":
            unit = self.units[o.unit_id]
            if unit.alive:
                unit.gain_from_training(self.rng)
                realm.drop_notes.append("%s drills hard" % unit.name)
        elif o.kind == "gear":
            unit = self.units[o.unit_id]
            if unit.alive:
                unit.kit = o.kind_data
                realm.drop_notes.append("%s outfitted" % unit.name)

    def _found_village_land(self, realm, pos):
        pos = tuple(pos)
        new_sid = self._new_sid()
        name = "%s %s" % (realm.name.split(" of ")[-1],
                          N.settlement_name(self.rng))
        h = Holding(new_sid, name, pos, C.SIZE_V, owner=realm.key)
        self.settlements[new_sid] = h
        realm.settlement_ids.append(new_sid)
        self.parties.append(Party(self._new_pid(), "garrison", realm.key,
                                  pos, [], settlement_id=new_sid))

    # --- succession ------------------------------------------------------
    def _ensure_succession(self, realm):
        if realm.hero is None or self.units[realm.hero].alive:
            return
        old = self.units[realm.hero]
        if realm.heir is not None and self.units[realm.heir].alive:
            self.units[realm.hero].is_hero = False
            self.units[realm.heir].is_hero = True
            self.units[realm.heir].is_heir = False
            realm.hero = realm.heir
            realm.heir = None
            realm.morale = max(0, realm.morale + C.MORALE_HERO_LOST)
            realm.drop_notes.append("the heir takes the crown")
            return
        # no living heir: can a town raise a new commander?
        has_town = any(self.settlements[sid].size != C.SIZE_V
                       for sid in realm.settlement_ids)
        if has_town:
            self.units[realm.hero].is_hero = False
            new_hero = self._make_unit(realm.key, hero=True)
            realm.hero = new_hero.id
            realm.unit_ids.add(new_hero.id)
            realm.morale = max(0, realm.morale + C.MORALE_RAISE_COMMANDER)
            realm.drop_notes.append("the council raises a new commander")
            hp = self.hero_party(realm.key)
            if hp is not None:
                hp.add(new_hero.id)
        else:
            self.units[realm.hero].is_hero = False
            realm.hero = None

    # ------------------------------------------------------------- contacts
    def _scan_contacts_for(self, party):
        """After a party move (or the AI phase), check for battles."""
        if party.kind == "garrison":
            return
        h = self.settlement_at(party.hex)
        if h is not None and h.owner is not None:
            sid = self.settlement_id_at(party.hex)
            if party.kind == "bandit":
                self._bandit_raid(party, sid)
            elif h.owner != party.realm:
                self._start_assault(party, self.garrison_party(sid), sid)
        for other in self.parties:
            if other.pid == party.pid:
                continue
            if other.kind == "garrison":
                continue
            if tuple(other.hex) == tuple(party.hex) and \
                    self._parties_hostile(party, other):
                self._make_battle(party, other, assault=False)

    def _parties_hostile(self, a, b):
        if a.kind == "bandit" and b.kind == "bandit":
            return False
        if a.realm is None or b.realm is None:
            return True  # bandits and neutral guards oppose everyone
        return a.realm != b.realm

    def _start_assault(self, attacker, garrison, sid):
        if garrison is not None and garrison.unit_ids:
            self._make_battle(attacker, garrison, assault=True)
        else:
            self._conquer(sid, attacker.realm)

    def _conquer(self, sid, realm_key):
        h = self.settlements[sid]
        old = h.owner
        if old is not None and old in self.realms and old != realm_key:
            if sid in self.realms[old].settlement_ids:
                self.realms[old].settlement_ids.remove(sid)
        h.owner = realm_key
        if realm_key in self.realms and sid not in self.realms[realm_key].settlement_ids:
            self.realms[realm_key].settlement_ids.append(sid)
        self.notes.append("%s was taken" % h.name)

    def _bandit_raid(self, bandit, sid):
        h = self.settlements[sid]
        realm = self._realm_of_settlement(sid)
        if realm is None:
            return
        stolen_w = min(6, int(realm.wheat))
        stolen_g = min(4, int(realm.gold))
        realm.wheat -= stolen_w
        realm.gold -= stolen_g
        realm.drop_notes.append("bandits raided %s" % h.name)
        self.notes.append("bandits raided %s (%d wheat, %d gold)"
                          % (h.name, stolen_w, stolen_g))
        gp = self.garrison_party(sid)
        if gp is not None and gp.unit_ids:
            # press the weak garrison or slip away
            me = sum(u.stat("melee") for u in self.living_in_party(bandit))
            them = sum(u.stat("melee") for u in self.living_in_party(gp))
            if me > them * 1.1 or self.rng.random() > 0.5:
                self._make_battle(bandit, gp, assault=True)

    def _start_battle(self, party_a, party_b):
        self._make_battle(party_a, party_b, assault=False)

    def _make_battle(self, atk_party, def_party, assault):
        from . import battle as B
        b = B.battle_from_contact(self, atk_party, def_party, assault)
        if b is None:
            return None
        involves_player = (atk_party.realm is not None and
                           atk_party.realm == self.player.key) or \
                          (def_party.realm is not None and
                           def_party.realm == self.player.key)
        if involves_player:
            self.pending_battles.append(b)
        else:
            b.auto_resolve(self.rng)
            self.resolve_battle(b)
        return b

    def resolve_battle(self, battle):
        """Write battle result back into the campaign."""
        from . import battle as B
        B.writeback(self, battle)

    def auto_resolve_pending(self):
        """Resolve every pending battle with the built-in AI (tests/invasion)."""
        while self.pending_battles:
            b = self.pending_battles[0]
            if not b.over():
                b.auto_resolve(self.rng)
            self.resolve_battle(b)
            if self.ended:
                break

    def discard_pending(self, battle):
        if battle in self.pending_battles:
            self.pending_battles.remove(battle)

    # --------------------------------------------------------- win / lose
    def check_end_conditions(self):
        for k, r in self.realms.items():
            if r.destroyed:
                continue
            hero_alive = (r.hero is not None and self.units[r.hero].alive)
            if not r.settlement_ids and not hero_alive:
                r.destroyed = True
                self.notes.append("%s has fallen" % r.name)
        if self.realms[C.PLAYER_REALM_KEY].destroyed:
            self.ended = True
            self.end_reason = "defeat"
            return
        others = [k for k, r in self.realms.items() if k != self.player.key]
        if all(self.realms[k].destroyed for k in others):
            self.ended = True
            self.end_reason = "victory"
            return
        # mid-loss is not the end
        self.check_player_hero()

    def check_player_hero(self):
        r = self.player
        if r.hero is not None and self.units[r.hero].alive:
            return
        self._ensure_succession(r)

    # ------------------------------------------------------------------ AI
    def _ai_and_bandit_turn(self):
        from . import ai as AI
        AI.run_ai_turn(self)

    # --------------------------------------------------------------- path
    def path_to(self, start, goal, mp=None):
        """Cheapest-first path from start to goal; returns list of hexes
        (excluding start) or [] if unreachable."""
        from . import pathfind
        return pathfind.a_star(self.world, start, goal)

    @property
    def width(self):
        return self.world.width

    @property
    def height(self):
        return self.world.height

    # ------------------------------------------------------------ reviews
    def morale_bonus(self, realm):
        r = self.realms[realm]
        return r.morale

    # ------------------------------------------------------------------ stats
    def realm_info(self, key):
        r = self.realms[key]
        return {
            "gold": r.gold, "wheat": r.wheat, "pop": r.population,
            "morale": r.morale, "name": r.name,
            "holdings": [self.settlements[s].name for s in r.settlement_ids],
            "company": len(self.living_in_party(self.hero_party(key))),
        }