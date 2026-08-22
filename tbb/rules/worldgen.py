"""Seeded, broad world generation for six duchies and frontier trouble."""
from . import constants as C
from . import names as N
from . import terrain as GEO
from . import world as W
from .settlements import Holding, Building
from .realm import Realm
from .parties import Party
from .units import Unit
from . import talents as T

COLORS = ((177, 56, 51), (53, 91, 161), (57, 126, 75), (164, 95, 39),
          (133, 74, 126), (175, 133, 43))

class Generator:
    def __init__(self, rng):
        self.rng = rng; self.world = W.World(C.MAP_WIDTH, C.MAP_HEIGHT)
        self.settlements, self.realms, self.units = {}, {}, {}
        self.parties = []; self.uid = self.sid = self.pid = 0; self.taken = {}
        self.realm_names, self.settlement_names = set(), set()

    def _id(self, attr):
        value = getattr(self, attr) + 1; setattr(self, attr, value); return value

    def generate_map(self):
        w, h = self.world.width, self.world.height
        for r in range(h):
            for q in range(w):
                roll = self.rng.random()
                terrain = C.TERRAIN_PLAINS
                if roll < .18: terrain = C.TERRAIN_FOREST
                elif roll > .83: terrain = C.TERRAIN_HILLS
                self.world.set_terrain((q, r), terrain)
        # two sinuous rivers ensure crossing decisions exist on every seed
        for river_no in range(2):
            q = 8 + river_no * 18 + self.rng.randint(-2, 2)
            for r in range(1, h - 1):
                qq = max(1, min(w - 2, q + ((r + river_no * 3) % 5) - 2))
                self.world.set_terrain((qq, r), C.TERRAIN_RIVER)
                if r % 6 == 2 or r == h // 2:
                    self.world.set_crossing((qq, r), "bridge" if (r // 6) % 2 else "ford")
        # ruins are former sites: empty, but valid founding targets
        candidates = [(q, r) for r in range(2, h-2) for q in range(2, w-2)
                      if self.world.terrain((q, r)) == C.TERRAIN_PLAINS]
        self.rng.shuffle(candidates)
        for pos in candidates[:max(20, len(candidates)//32)]: self.world.set_terrain(pos, C.TERRAIN_RUINS)
        return self.world

    def suitable_cells(self):
        return [p for p,t in self.world.grid.items() if t in (C.TERRAIN_PLAINS, C.TERRAIN_RUINS)]

    def _far_cell(self, pool, used, distance):
        options = [p for p in pool if all(GEO.hex_distance(p, u) >= distance for u in used)]
        if not options: options = [p for p in pool if p not in used]
        if not options: return None
        return self.rng.choice(options)

    def _archetype(self):
        names = tuple(C.START_ARCHETYPES)
        return self.rng.choice(names)

    def _sizes(self, archetype):
        return self.rng.choice(C.START_ARCHETYPES[archetype])

    def _make_unit(self, realm_key, hero=False, origin="the road"):
        taken = self.taken.setdefault(realm_key, set())
        name = N.unique_warrior_name(self.rng, taken)
        base = self.rng.randint(34, 54) if hero else self.rng.randint(24, 45)
        stats = {"melee": max(C.STAT_MIN, min(C.STAT_MAX, base+self.rng.randint(-5, 10))),
                 "ranged": max(C.STAT_MIN, min(C.STAT_MAX, base+self.rng.randint(-8, 8))),
                 "hit_points": max(C.STAT_MIN, min(C.STAT_MAX, base+self.rng.randint(-3, 8))),
                 "fatigue": max(C.STAT_MIN, min(C.STAT_MAX, base+self.rng.randint(-2, 9))),
                 "resolve": max(C.STAT_MIN, min(C.STAT_MAX, self.rng.randint(25, 55)))}
        uid = self._id("uid")
        unit = Unit(uid, name, stats=stats, talents=T.roll_talents(self.rng),
                    origin=origin, age=self.rng.randint(16, 40), realm=realm_key,
                    kit="light", is_hero=hero)
        self.units[uid] = unit; return unit

    def _holding(self, realm, pos, size):
        sid = self._id("sid")
        name = N.unique_settlement_name(self.rng, self.settlement_names)
        owner = realm.key if realm else None
        h = Holding(sid, name, pos, size, owner)
        if size in (C.SIZE_T, C.SIZE_C):
            h.buildings[C.BUILDING_FARM] = Building(C.BUILDING_FARM, staffed=True)
            h.buildings[C.BUILDING_MARKET] = Building(C.BUILDING_MARKET, staffed=True)
            if size == C.SIZE_C:
                h.buildings[C.BUILDING_MILITIA_HALL] = Building(
                    C.BUILDING_MILITIA_HALL, staffed=True)
        self.settlements[sid] = h
        if owner is not None: realm.settlement_ids.append(sid)
        self.world.set_terrain(pos, C.TERRAIN_VILLAGE)
        self.parties.append(Party(self._id("pid"), "garrison", owner, pos, (), sid))
        return h

    def _road_between(self, a, b):
        q, r = a
        for _ in range(GEO.hex_distance(a, b) + 1):
            if self.world.terrain((q, r)) in (C.TERRAIN_PLAINS, C.TERRAIN_RUINS): self.world.set_terrain((q, r), C.TERRAIN_ROAD)
            if q == b[0] and r == b[1]: break
            if q < b[0]: q += 1
            elif q > b[0]: q -= 1
            if r < b[1]: r += 1
            elif r > b[1]: r -= 1

    def _party_for_holding(self, sid): return next(p for p in self.parties if p.settlement_id == sid)

    def _create_realm(self, key, center):
        realm = Realm(key, N.unique_realm_name(self.rng, self.realm_names),
                      key == C.PLAYER_REALM_KEY, COLORS[key])
        self.realms[key] = realm
        archetype = self._archetype()
        realm.start_archetype = archetype
        sizes = self._sizes(archetype)
        used = [center]
        for index, size in enumerate(sizes):
            pos = center if index == 0 else self._far_cell(
                self.suitable_cells(), used, 2)
            if pos is None:
                raise RuntimeError("worldgen could not place the selected start layout")
            used.append(pos); h = self._holding(realm, pos, size)
            if index == 0: capital = h
        hero = self._make_unit(key, True, capital.name); realm.hero = hero.id; realm.unit_ids.add(hero.id)
        field = [hero.id]
        for _ in range(self.rng.randint(2, 5)):
            unit = self._make_unit(key, False, capital.name); field.append(unit.id); realm.unit_ids.add(unit.id)
        heir = self._make_unit(key, False, capital.name); realm.unit_ids.add(heir.id)
        if self.rng.random() < .75: realm.heir = heir.id; heir.is_heir = True
        self.parties.append(Party(self._id("pid"), "hero", key, center, field))
        garrison = self._party_for_holding(capital.id)
        for _ in range(min(2, capital.garrison_cap())):
            unit = self._make_unit(key, False, capital.name); realm.unit_ids.add(unit.id); garrison.add(unit.id)
        realm.gold = self.rng.randint(160, 260)
        realm.wheat = self.rng.randint(80, 140)
        minimum_workers = realm.staff_total(self.settlements) + 1
        realm.population = min(realm.holdings_cap(self.settlements),
                               max(self.rng.randint(18, 30), minimum_workers))
        return realm

    def _neutrals(self, pool, centers):
        for _ in range(self.rng.randint(C.MIN_NEUTRALS, C.MAX_NEUTRALS)):
            pos = self._far_cell(pool, centers, 5)
            if not pos: continue
            centers.append(pos); h = self._holding(None, pos, C.SIZE_V if self.rng.random() < .7 else C.SIZE_T)
            g = self._party_for_holding(h.id)
            for _ in range(self.rng.randint(2, 4)): g.add(self._make_unit(None, origin=h.name).id)

    def _bandits(self, pool, player_pos):
        wild = [p for p in pool if GEO.hex_distance(p, player_pos) >= 7 and self.world.terrain(p) in (C.TERRAIN_FOREST, C.TERRAIN_RUINS, C.TERRAIN_ROAD)]
        if len(wild) < C.NUM_ROBBER_BANDS: wild = [p for p in pool if GEO.hex_distance(p, player_pos) >= 7]
        for _ in range(C.NUM_ROBBER_BANDS):
            pos = self.rng.choice(wild); wild.remove(pos)
            ids = [self._make_unit(None, origin="the road").id for _ in range(self.rng.randint(*C.BANDIT_PARTY_SIZE))]
            self.parties.append(Party(self._id("pid"), "bandit", None, pos, ids))

    def run(self):
        self.generate_map(); pool = self.suitable_cells(); centers = []
        for _ in range(C.NUM_DUCHIES):
            pos = self._far_cell(pool, centers, 9); centers.append(pos)
        for key, center in enumerate(centers): self._create_realm(key, center)
        for a, b in zip(centers, centers[1:]): self._road_between(a, b)
        self._neutrals(pool, centers[:]); self._bandits(pool, centers[0])
        return {"world": self.world, "settlements": self.settlements, "realms": self.realms,
                "units": self.units, "parties": self.parties}

def generate(rng): return Generator(rng).run()
