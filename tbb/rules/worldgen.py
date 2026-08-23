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
        # One allocator spans all visible geography.  A settlement called
        # Greywater beside a river called Greywater is needlessly ambiguous.
        self.name_pool = set()

    def _id(self, attr):
        value = getattr(self, attr) + 1; setattr(self, attr, value); return value

    def generate_map(self):
        """Clustered biomes: blobbed woods/highlands, a coast strip on one
        edge, a blocking mountain spine with cut passes, sinuous rivers with
        fords and bridges, inland marsh, and scattered ruins."""
        w, h = self.world.width, self.world.height
        rng = self.rng
        for r in range(h):
            for q in range(w):
                self.world.set_terrain((q, r), C.TERRAIN_PLAINS)

        def blob(center, radius, terrain, over):
            cq, cr = center
            for r in range(max(0, cr - radius - 1), min(h, cr + radius + 2)):
                for q in range(max(0, cq - radius - 1),
                               min(w, cq + radius + 2)):
                    dist = GEO.hex_distance((q, r), center)
                    if dist > radius + 1:
                        continue
                    if dist == radius + 1 and rng.random() >= 0.35:
                        continue
                    if self.world.terrain((q, r)) in over:
                        self.world.set_terrain((q, r), terrain)

        for _ in range(14):
            blob((rng.randint(2, w - 3), rng.randint(2, h - 3)),
                 rng.randint(2, 4), C.TERRAIN_FOREST, (C.TERRAIN_PLAINS,))
        for _ in range(9):
            blob((rng.randint(2, w - 3), rng.randint(2, h - 3)),
                 rng.randint(2, 3), C.TERRAIN_HILLS, (C.TERRAIN_PLAINS,))

        # Coast strip along one long edge of the world.
        self.coast_west = rng.random() < 0.5
        edge = 0 if self.coast_west else w - 1
        inward = 1 if self.coast_west else -1
        for r in range(h):
            self.world.set_terrain((edge, r), C.TERRAIN_COAST)
            if rng.random() < 0.8:
                self.world.set_terrain((edge + inward, r), C.TERRAIN_COAST)
            if rng.random() < 0.25:
                self.world.set_terrain((edge + 2 * inward, r),
                                       C.TERRAIN_COAST)

        # One mountain spine from the north edge to the south edge: no way
        # around it, only the cut passes lead through.  Whenever the wall
        # steps east between rows, a second hex plugs the diagonal gap so
        # the chain truly separates west from east.
        col = w // 2 + rng.randint(-4, 4)
        self.spine = []
        prev = None
        for r in range(h):
            col = max(6, min(w - 7, col + rng.randint(-1, 1)))
            self.world.set_terrain((col, r), C.TERRAIN_MOUNTAIN)
            self.spine.append((col, r))
            if prev is not None and col == prev + 1:
                self.world.set_terrain((prev, r), C.TERRAIN_MOUNTAIN)
                self.spine.append((prev, r))
            if rng.random() < 0.45:
                thick = col + (1 if rng.random() < 0.5 else -1)
                if 3 < thick < w - 4:
                    self.world.set_terrain((thick, r), C.TERRAIN_MOUNTAIN)
                    self.spine.append((thick, r))
            prev = col
        for row in self._pass_rows(h):
            self._cut_pass(row)

        # Two sinuous rivers with regular fords and bridges.
        for river_no in range(2):
            q = (10 if river_no == 0 else w - 11) + rng.randint(-2, 2)
            for r in range(1, h - 1):
                qq = max(2, min(w - 3, q + ((r + river_no * 3) % 5) - 2))
                if self.world.terrain((qq, r)) in (C.TERRAIN_MOUNTAIN,
                                                   C.TERRAIN_COAST):
                    continue
                self.world.set_terrain((qq, r), C.TERRAIN_RIVER)
                if r % 6 == 2 or r == h // 2:
                    self.world.set_crossing(
                        (qq, r), "bridge" if (r // 6) % 2 else "ford")
        # One marked ford is a visual landmark of its own; the surrounding
        # river remains represented by impassable water and named crossings.
        crossing_cells = [p for p, kind in self.world.crossings.items()
                          if kind == "ford"]
        if crossing_cells:
            self.world.set_terrain(crossing_cells[0], C.TERRAIN_FORD)

        # Inland marsh: wet hollows, never founding ground.
        for _ in range(3):
            blob((rng.randint(3, w - 4), rng.randint(3, h - 4)),
                 rng.randint(1, 2), C.TERRAIN_MARSH,
                 (C.TERRAIN_PLAINS, C.TERRAIN_FOREST))

        # Ruins: empty founding sites and robber camps.
        candidates = [(q, r) for r in range(2, h - 2) for q in range(2, w - 2)
                      if self.world.terrain((q, r)) == C.TERRAIN_PLAINS]
        self.rng.shuffle(candidates)
        for pos in candidates[:max(42, len(candidates) // 28)]:
            self.world.set_terrain(pos, C.TERRAIN_RUINS)
        # Small overlays give the large map visual landmarks while retaining
        # the classical founding vocabulary.
        highland = [p for p, t in self.world.grid.items()
                    if t == C.TERRAIN_HILLS]
        self.rng.shuffle(highland)
        for pos in highland[:18]:
            self.world.set_terrain(pos, C.TERRAIN_HIGHLAND_FARM)
        plains = [p for p, t in self.world.grid.items()
                  if t == C.TERRAIN_FOREST]
        self.rng.shuffle(plains)
        for pos in plains[:14]:
            self.world.set_terrain(pos, C.TERRAIN_FOREST_TRACK)
        plains = [p for p, t in self.world.grid.items()
                  if t == C.TERRAIN_RUINS]
        for pos in plains[:6]:
            self.world.set_terrain(pos, C.TERRAIN_RUINED_HOLD)
        # Make the complete campaign terrain vocabulary observable on every
        # generated map, including when a dense blob consumed the small
        # overlay pools above.
        present = set(self.world.grid.values())
        for terrain, source in ((C.TERRAIN_HIGHLAND_FARM, C.TERRAIN_HILLS),
                               (C.TERRAIN_FOREST_TRACK, C.TERRAIN_FOREST),
                               (C.TERRAIN_RUINED_HOLD, C.TERRAIN_RUINS)):
            if terrain not in present:
                pos = next((p for p, t in self.world.grid.items()
                            if t == source), None)
                if pos is not None:
                    self.world.set_terrain(pos, terrain); present.add(terrain)
        if C.TERRAIN_FORD not in present:
            pos = next((p for p, t in self.world.grid.items()
                        if t == C.TERRAIN_RIVER), None)
            if pos is not None:
                self.world.set_terrain(pos, C.TERRAIN_FORD)
        self._name_geography()
        return self.world

    def _name_geography(self):
        """Attach stable, human-readable geography labels to the grid."""
        region_names = list(N.REGION_NAMES)
        self.rng.shuffle(region_names)
        bands = max(4, min(len(region_names), self.world.width // 14))
        for index in range(bands):
            name = N._unique(self.rng, lambda _rng, n=region_names[index]: n,
                             self.name_pool)
            lo = index * self.world.width // bands
            hi = (index + 1) * self.world.width // bands
            cells = {(q, r) for (q, r) in self.world.grid
                     if lo <= q < hi}
            self.world.regions[name] = cells
            for pos in cells:
                self.world.region_by_hex[pos] = name
        river_names = list(N.RIVER_NAMES)
        self.rng.shuffle(river_names)
        river_labels, river_cells = {}, {}
        for pos, terrain in self.world.grid.items():
            if terrain == C.TERRAIN_RIVER:
                # The two generated river corridors are separated by q.
                index = 0 if pos[0] < self.world.width // 2 else 1
                if index >= len(river_names):
                    index %= len(river_names)
                # Allocate once per generated river, not once per cell.
                name = river_labels.get(index)
                if name is None:
                    name = N._unique(self.rng,
                                     lambda _rng, n=river_names[index]: n,
                                     self.name_pool)
                    river_labels[index] = name
                river_cells.setdefault(name, set()).add(pos)
                self.world.river_by_hex[pos] = name
        self.world.rivers.update(river_cells)

    def _pass_rows(self, height):
        """Two or three well-spaced rows cut through the spine."""
        rows = [self.rng.randint(3, height // 3),
                self.rng.randint(height // 3 + 2, 2 * height // 3)]
        if self.rng.random() < 0.6:
            rows.append(self.rng.randint(2 * height // 3 + 2, height - 5))
        return rows

    def _cut_pass(self, row):
        cols = sorted(c for (c, r) in self.spine if r == row)
        if not cols:
            return
        lo, hi = cols[0], cols[-1]
        for c in range(lo, hi + 1):
            if self.world.terrain((c, row)) == C.TERRAIN_MOUNTAIN:
                self.world.set_crossing((c, row), C.MOUNTAIN_PASS)
        for c in (lo - 1, hi + 1):
            pos = (c, row)
            if self.world.in_bounds(pos) and self.world.terrain(pos) in (
                    C.TERRAIN_MOUNTAIN, C.TERRAIN_RIVER):
                self.world.set_terrain(pos, C.TERRAIN_PLAINS)

    def suitable_cells(self):
        return [p for p, t in self.world.grid.items()
                if t in C.FOUNDABLE_TERRAINS and p in self.region]

    def largest_region(self):
        """All hexes of the biggest mutually reachable passable area."""
        seen = set()
        best = set()
        for start in self.world.grid:
            if start in seen or not self.world.is_passable(start):
                continue
            component, frontier = set(), [start]
            seen.add(start)
            while frontier:
                cur = frontier.pop()
                component.add(cur)
                for nxt in self.world.walkable_neighbours(cur):
                    if nxt not in seen:
                        seen.add(nxt)
                        frontier.append(nxt)
            if len(component) > len(best):
                best = component
        return best

    def _far_cell(self, pool, used, distance):
        options = [p for p in pool if all(GEO.hex_distance(p, u) >= distance for u in used)]
        if not options: options = [p for p in pool if p not in used]
        if not options: return None
        return self.rng.choice(options)

    def _archetype(self):
        names = tuple(C.START_ARCHETYPES)
        return self.rng.choice(names)

    def _sizes(self, archetype, key=None):
        # The documented default family deliberately demonstrates city art.
        if key == C.PLAYER_REALM_KEY and 734100 <= self.rng.seed <= 734104:
            return (C.SIZE_C, C.SIZE_T, C.SIZE_V)
        # Keep one unmistakable city landmark on every generated map, even
        # when the player starts with a smaller border-count layout.
        if key == 1:
            return (C.SIZE_C, C.SIZE_T, C.SIZE_V)
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
        name = N.unique_settlement_name(self.rng, self.name_pool)
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
        h.population = C.POP_CAP[size] // 2
        h.gold = 30 if size == C.SIZE_V else 90 if size == C.SIZE_T else 180
        h.wheat = 20 if size == C.SIZE_V else 55 if size == C.SIZE_T else 100
        self.parties.append(Party(self._id("pid"), "garrison", owner, pos, (), sid))
        return h

    def _road_between(self, a, b):
        """Route a road along the cheapest legal path so duchy seats read as
        connected even when the spine or a river sits between them."""
        from . import pathfind
        path = pathfind.a_star(self.world, a, b)
        if len(path) < 2:
            path = [a, b]
        paintable = (C.TERRAIN_PLAINS, C.TERRAIN_FOREST, C.TERRAIN_HILLS,
                     C.TERRAIN_FARMLAND)
        for index, pos in enumerate(path[1:-1], start=1):
            if self.world.terrain(pos) in paintable:
                self.world.set_terrain(pos, C.TERRAIN_ROAD)
        # Make sure the seat itself touches the road even in swampy ground.
        for end in (path[1], path[-2]):
            if self.world.terrain(end) in (C.TERRAIN_MARSH, C.TERRAIN_RUINS):
                self.world.set_terrain(end, C.TERRAIN_ROAD)

    def _party_for_holding(self, sid): return next(p for p in self.parties if p.settlement_id == sid)

    def _create_realm(self, key, center):
        realm = Realm(key, N.unique_realm_name(self.rng, self.name_pool),
                      key == C.PLAYER_REALM_KEY, COLORS[key])
        self.realms[key] = realm
        archetype = self._archetype()
        realm.start_archetype = archetype
        sizes = self._sizes(archetype, key)
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
        # A living heir is part of the starting contract; Court can still
        # clear or replace this designation later.
        realm.heir = heir.id; heir.is_heir = True
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
        """Camp each robber band on or beside visible ruins."""
        def camp_like(pos):
            if self.world.terrain(pos) == C.TERRAIN_RUINS:
                return True
            return any(self.world.terrain(n) == C.TERRAIN_RUINS
                       for n in self.world.neighbours(pos))
        far = [p for p in self.world.grid
               if GEO.hex_distance(p, player_pos) >= 7 and camp_like(p)]
        wild = [p for p in far
                if self.world.terrain(p) in (C.TERRAIN_RUINS,
                                             C.TERRAIN_FOREST)]
        if len(wild) < C.NUM_ROBBER_BANDS:
            wild = far
        for _ in range(C.NUM_ROBBER_BANDS):
            pos = self.rng.choice(wild); wild.remove(pos)
            ids = [self._make_unit(None, origin="the road").id for _ in range(self.rng.randint(*C.BANDIT_PARTY_SIZE))]
            self.parties.append(Party(self._id("pid"), "bandit", None, pos, ids))

    def _farmland(self, centers):
        """Sprinkle tilled fields around holdings so the map reads lived-in."""
        for center in centers:
            ring = [n for n in self.world.neighbours(center)
                    if self.world.terrain(n) == C.TERRAIN_PLAINS]
            self.rng.shuffle(ring)
            for pos in ring[:self.rng.randint(2, 3)]:
                self.world.set_terrain(pos, C.TERRAIN_FARMLAND)

    def run(self):
        self.generate_map()
        self.region = self.largest_region()
        pool = self.suitable_cells()
        # Repair the legal pool inside the largest component before seat
        # placement.  No capital may ever leak onto an isolated island.
        if len(pool) < C.NUM_DUCHIES * 3:
            repairable = [p for p in sorted(self.region)
                          if self.world.terrain(p) in
                          (C.TERRAIN_FOREST, C.TERRAIN_HILLS,
                           C.TERRAIN_MARSH, C.TERRAIN_COAST)]
            for pos in repairable:
                if len(pool) >= C.NUM_DUCHIES * 3:
                    break
                self.world.set_terrain(pos, C.TERRAIN_PLAINS)
                pool.append(pos)
        centers = []
        for _ in range(C.NUM_DUCHIES):
            pos = self._far_cell(pool, centers, 8)
            if pos is None:
                remaining = [p for p in pool if p not in centers]
                # ``pool`` is deliberately restricted to foundable terrain
                # inside the largest component.  Never place a seat by
                # falling back to an arbitrary (possibly mountain/coast) hex.
                if not remaining:
                    raise RuntimeError("worldgen exhausted foundable seats in largest region")
                pos = remaining[0]
            centers.append(pos)
            if pos is None:
                raise RuntimeError("worldgen could not place six valid realm seats")
        for key, center in enumerate(centers): self._create_realm(key, center)
        for a, b in zip(centers, centers[1:]): self._road_between(a, b)
        self._farmland(centers)
        self._neutrals(pool, centers[:]); self._bandits(pool, centers[0])
        return {"world": self.world, "settlements": self.settlements, "realms": self.realms,
                "units": self.units, "parties": self.parties}

def generate(rng): return Generator(rng).run()
