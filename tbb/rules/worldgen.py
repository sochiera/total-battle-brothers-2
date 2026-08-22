"""Procedural campaign world generation from a seed.

Produces a large mixed hex world (plains, woods, hills, rivers, wastes, water),
five duchies (player + four AI), independent holdings, bandit parties, named
heroes/heirs/companies with mixed starting holdings that vary by seed.

Everything flows through the seeded RNG so the same seed always generates the
same world.
"""
from . import constants as C
from . import talents as T
from . import names as N
from . import world as W
from . import terrain as GEO
from .settlements import Holding
from .realm import Realm
from .parties import Party
from .units import Unit


class Generator:
    def __init__(self, rng):
        self.rng = rng
        self.world = W.World(C.MAP_WIDTH, C.MAP_HEIGHT)
        self.settlements = {}
        self.realms = {}
        self.units = {}
        self.parties = []
        self._uid = 0
        self._sid = 0
        self._pid = 0
        self._names = {}

    # ------------------------------------------------------------------ ids
    def next_uid(self):
        self._uid += 1
        return self._uid

    def next_sid(self):
        self._sid += 1
        return self._sid

    def next_pid(self):
        self._pid += 1
        return self._pid

    # ------------------------------------------------------------ map gen
    def _noise(self):
        w, h = C.MAP_WIDTH, C.MAP_HEIGHT
        vals = [[self.rng.random() for _ in range(w)] for _ in range(h)]
        for _ in range(2):
            nv = [[0.0] * w for _ in range(h)]
            for r in range(h):
                for q in range(w):
                    acc = vals[r][q]
                    cnt = 1
                    for nq, nr in [(q + 1, r), (q - 1, r), (q, r + 1),
                                   (q, r - 1), (q + 1, r - 1), (q - 1, r + 1)]:
                        if 0 <= nq < w and 0 <= nr < h:
                            acc += vals[nr][nq]
                            cnt += 1
                    nv[r][q] = acc / cnt + (self.rng.random() - 0.5) * 0.05
            vals = nv
        return vals

    def _overlay_blobs(self, target, count_range):
        w, h = C.MAP_WIDTH, C.MAP_HEIGHT
        n = self.rng.randint(*count_range)
        for _ in range(n):
            q = self.rng.randint(1, w - 2)
            r = self.rng.randint(1, h - 2)
            radius = self.rng.randint(1, 3)
            for dq in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    nq, nr = q + dq, r + dr
                    if not (0 <= nq < w and 0 <= nr < h):
                        continue
                    if (dq * dq + dr * dr) > radius * radius:
                        continue
                    cur = self.world.terrain((nq, nr))
                    if cur in (C.TERRAIN_HILLS, C.TERRAIN_WATER):
                        continue
                    self.world.set_terrain((nq, nr), target)

    def _carve_rivers(self):
        w, h = C.MAP_WIDTH, C.MAP_HEIGHT
        for _ in range(self.rng.randint(2, 4)):
            edge = self.rng.randint(0, 3)
            if edge == 0:
                q, r = self.rng.randint(2, w - 3), 0
            elif edge == 1:
                q, r = self.rng.randint(2, w - 3), h - 1
            elif edge == 2:
                q, r = 0, self.rng.randint(2, h - 3)
            else:
                q, r = w - 1, self.rng.randint(2, h - 3)
            steps = self.rng.randint(6, 14)
            for _ in range(steps):
                if not (0 <= q < w and 0 <= r < h):
                    break
                if self.world.terrain((q, r)) != C.TERRAIN_WATER:
                    self.world.set_terrain((q, r), C.TERRAIN_RIVER)
                nb = self.world.neighbours((q, r))
                self.rng.shuffle(nb)
                nxt = None
                for cand in nb:
                    t = self.world.terrain(cand)
                    if t in (C.TERRAIN_RIVER, C.TERRAIN_WATER):
                        continue
                    nxt = cand
                    break
                if nxt is None:
                    nxt = nb[self.rng.randint(0, len(nb) - 1)]
                q, r = nxt

    def generate_map(self):
        w, h = C.MAP_WIDTH, C.MAP_HEIGHT
        vals = self._noise()
        for r in range(h):
            for q in range(w):
                v = vals[r][q]
                if v < 0.42:
                    terr = C.TERRAIN_WATER
                elif v > 0.62:
                    terr = C.TERRAIN_HILLS
                else:
                    terr = C.TERRAIN_PLAIN
                self.world.set_terrain((q, r), terr)
        self._overlay_blobs(C.TERRAIN_WOODS, (30, 55))
        self._overlay_blobs(C.TERRAIN_WASTE, (8, 14))
        self._carve_rivers()
        return self.world

    # -------------------------------------------------------------- cells
    def suitable_cells(self):
        out = []
        for pos, terr in self.world.grid.items():
            if terr != C.TERRAIN_PLAIN:
                continue
            nb = self.world.neighbours(pos)
            if any(self.world.terrain(n) in (C.TERRAIN_WATER,
                                             C.TERRAIN_RIVER) for n in nb):
                continue
            out.append(pos)
        return out

    def dist_to_any(self, pos, others):
        if not others:
            return 10 ** 9
        return min(GEO.hex_distance(pos, o) for o in others)

    def pick_far_cell(self, cells, centers, min_dist):
        picks = cells[:]
        self.rng.shuffle(picks)
        for c in picks:
            if self.dist_to_any(c, centers) >= min_dist:
                return c
        return picks[0] if picks else None

    def near_suitable(self, capital, used):
        w, h = C.MAP_WIDTH, C.MAP_HEIGHT
        q0, r0 = capital
        best = []
        for r in range(max(0, r0 - 4), min(h, r0 + 5)):
            for q in range(max(0, q0 - 4), min(w, q0 + 5)):
                pos = (q, r)
                if pos in used:
                    continue
                if self.world.terrain(pos) == C.TERRAIN_PLAIN:
                    best.append(pos)
        self.rng.shuffle(best)
        return best[0] if best else None

    # --------------------------------------------------------- holdings
    def roll_capital_size(self):
        r = self.rng.random()
        if r < 0.22:
            return C.SIZE_V
        if r < 0.80:
            return C.SIZE_T
        return C.SIZE_C

    def roll_extra_size(self):
        return C.SIZE_V if self.rng.random() < 0.7 else C.SIZE_T

    def starting_holdings(self):
        """Explicit seed-varied start mix: lone village, city + village,
        town + village, or town + two villages. AI rulers use the same table,
        so what the player can roll is what every duchy rolls."""
        table = [
            # (probability, sizes)
            (0.14, [C.SIZE_V]),                       # grim lone village
            (0.12, [C.SIZE_C, C.SIZE_V]),             # a worn city + village
            (0.30, [C.SIZE_T, C.SIZE_V]),             # town + village
            (0.44, [C.SIZE_T, C.SIZE_V, C.SIZE_V]),   # town + two villages
        ]
        r = self.rng.random()
        acc = 0.0
        for prob, sizes in table:
            acc += prob
            if r < acc:
                return list(sizes)
        return list(table[-1][1])

    def place_holding(self, realm, pos, size, prefix=None):
        sid = self.next_sid()
        if prefix is None:
            prefix = "Free" if realm is None else realm.name.split(" of ")[-1]
        name = "%s %s" % (prefix, N.settlement_name(self.rng))
        owner = realm.key if realm is not None else None
        h = Holding(sid, name, pos, size, owner=owner)
        self.settlements[sid] = h
        if realm is None:
            self.parties.append(Party(self.next_pid(), "garrison", None,
                                      pos, [], settlement_id=sid))
        else:
            # a garrison post always rises with the holding; the ruler may
            # not fill it yet
            self.parties.append(Party(self.next_pid(), "garrison", realm.key,
                                      pos, [], settlement_id=sid))
            realm.settlement_ids.append(sid)
        return h

    # ------------------------------------------------------------- units
    def _taken_names(self, realm_key):
        return self._names.setdefault(realm_key, set())

    def make_unit(self, realm_key, rng, hero=False, stats=None, kit=None):
        uid = self.next_uid()
        name = N.unique_warrior_name(rng, self._taken_names(realm_key))
        if stats is None:
            base = rng.randint(34, 58) if hero else rng.randint(24, 46)
            stats = {
                "melee": base + rng.randint(-6, 12),
                "ranged": base + rng.randint(-10, 8),
                "toughness": base + rng.randint(-4, 8),
                "fatigue": base + rng.randint(-2, 10),
                "resolve": rng.randint(22, 50),
                "initiative": base + rng.randint(-8, 6),
            }
            stats = {k: min(C.STAT_MAX, max(C.STAT_MIN, v))
                     for k, v in stats.items()}
        tal = T.roll_talents(rng)
        u = Unit(uid, name, stats["melee"], stats["ranged"],
                 stats["toughness"], stats["fatigue"], stats["resolve"],
                 stats["initiative"], tal, kit=kit or C.KIT_POOR,
                 realm=realm_key)
        if hero:
            u.is_hero = True
        self.units[uid] = u
        return u

    def _create_company(self, realm, center, extras):
        hero = self.make_unit(realm.key, self.rng, hero=True)
        realm.hero = hero.id
        field = [hero.id]
        for _ in range(extras):
            field.append(self.make_unit(realm.key, self.rng).id)
        heir = self.make_unit(realm.key, self.rng)
        heir.is_heir = False
        realm.unit_ids.add(heir.id)
        realm.unit_ids.update(field)
        if self.rng.random() < 0.7:
            heir.is_heir = True
            realm.heir = heir.id
        party = Party(self.next_pid(), "hero", realm.key, self._capital_hex,
                      field)
        self.parties.append(party)
        cap_sid = self._capital_sid
        # fill the garrison post that place_holding already created
        gp = next((p for p in self.parties if p.kind == "garrison" and
                   p.settlement_id == cap_sid), None)
        n = self.rng.randint(*C.GARRISON_EXTRA)
        g = [self.make_unit(realm.key, self.rng).id for _ in range(n)]
        realm.unit_ids.update(g)
        g = g[: self.settlements[cap_sid].garrison_cap()]
        if gp is not None:
            gp.unit_ids = g
            gp.hex = tuple(center)
        else:
            self.parties.append(Party(self.next_pid(), "garrison",
                                      realm.key, center, g,
                                      settlement_id=cap_sid))
        realm.gold = self.rng.randint(C.START_GOLD_BASE,
                                      C.START_GOLD_BASE + C.START_GOLD_SPREAD)
        realm.wheat = self.rng.randint(C.START_WHEAT_BASE,
                                       C.START_WHEAT_BASE + C.START_WHEAT_SPREAD)
        realm.population = self.rng.randint(C.START_POP_MIN,
                                            C.START_POP_MIN + C.START_POP_ADD)

    # --------------------------------------------------------------- run
    def run(self):
        self.generate_map()
        cells = self.suitable_cells()

        centers = []
        for _ in range(C.NUM_DUCHIES):
            c = self.pick_far_cell(cells, centers, 9)
            if c is None:
                break
            centers.append(c)

        colors = [(150, 40, 40), (35, 80, 160), (45, 120, 65),
                  (155, 65, 15), (130, 120, 35)]
        realm_keys = ([C.PLAYER_REALM_KEY] +
                      [k for k in range(1, C.NUM_DUCHIES)])
        for i, center in enumerate(centers[: len(realm_keys)]):
            key = realm_keys[i]
            realm = Realm(key, N.realm_name(self.rng), is_player=(key == 0),
                          color=colors[i])
            self.realms[key] = realm
            sizes = self.starting_holdings()
            cap_cell = center
            used = [cap_cell]
            self.place_holding(realm, cap_cell, sizes[0])
            for extra in sizes[1:]:
                cand = self.near_suitable(cap_cell, used)
                if cand is None:
                    break
                self.place_holding(realm, cand, extra)
                used.append(cand)

        for i, center in enumerate(centers):
            realm = self.realms[realm_keys[i]]
            self._capital_hex = center
            self._capital_sid = self._hex_settlement_id(center)
            extras = self.rng.randint(*C.HERO_COMPANY_SIZE)
            self._create_company(realm, center, extras)

        self._create_neutrals(cells, centers)
        self._create_bandits(cells)
        return {
            "world": self.world, "settlements": self.settlements,
            "realms": self.realms, "units": self.units,
            "parties": self.parties,
        }

    def _hex_settlement_id(self, pos):
        for sid, h in self.settlements.items():
            if tuple(h.hex) == tuple(pos):
                return sid
        return None

    # ------------------------------------------------------------- flavour
    def _create_neutrals(self, cells, centers):
        n = self.rng.randint(C.MIN_NEUTRALS, C.MAX_NEUTRALS)
        pool = [c for c in cells]
        for _ in range(n):
            c = self.pick_far_cell(pool, list(centers), 6)
            if c is None:
                break
            pool.remove(c)
            size = C.SIZE_T if self.rng.random() < 0.3 else C.SIZE_V
            h = self.place_holding(None, c, size)
            guard = [self.make_unit(None, self.rng).id
                     for _ in range(self.rng.randint(2, 5))]
            for uid in guard:
                u = self.units[uid]
                if self.rng.random() < 0.15:
                    u.kit = "light"
            self.parties.append(Party(self.next_pid(), "garrison", None, c,
                                      guard, settlement_id=h.id))

    def _create_bandits(self, cells):
        player_pos = (0, 0)
        if C.PLAYER_REALM_KEY in self.realms:
            sids = self.realms[C.PLAYER_REALM_KEY].settlement_ids
            if sids:
                player_pos = self.settlements[sids[0]].hex
        pool = [c for c in cells if GEO.hex_distance(c, player_pos) >= 6]
        n = self.rng.randint(C.MIN_BANDITS, C.MAX_BANDITS)
        for _ in range(n):
            self.rng.shuffle(pool)
            if not pool:
                break
            c = pool.pop()
            size = self.rng.randint(*C.BANDIT_PARTY_SIZE)
            band = [self.make_unit(None, self.rng).id for _ in range(size)]
            for uid in band:
                u = self.units[uid]
                roll = self.rng.random()
                if roll < 0.2:
                    u.kit = "light"
                elif roll < 0.3:
                    u.kit = "militia"
            self.parties.append(Party(self.next_pid(), "bandit", None, c,
                                      band))


def generate(rng):
    return Generator(rng).run()
