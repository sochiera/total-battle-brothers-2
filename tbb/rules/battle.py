"""Individual-unit side-turn tactical battles on 30x20 fields.

The field is painted from the overworld hex of the contact plus its campaign
neighbours, so a forest contact reads as woods with clearings and a hill
contact shows ridges.  Turns are side-based: one side spends the action
points of any of its warriors, ends its turn, and the other side replies.
"""
from . import constants as C
from . import terrain as G

BLOCKING_TERRAIN = C.BATTLE_BLOCKING_TERRAIN
IMPASSABLE = C.BATTLE_IMPASSABLE_TERRAIN

_THEME_NEIGHBOURS = {
    C.TERRAIN_FOREST: (C.TERRAIN_FOREST,) * 5 + (C.TERRAIN_PLAINS,),
    C.TERRAIN_HILLS: (C.TERRAIN_HILLS,) * 5 + (C.TERRAIN_PLAINS,),
    C.TERRAIN_MARSH: (C.TERRAIN_MARSH,) * 4 + (C.TERRAIN_PLAINS,) * 2,
    C.TERRAIN_FARMLAND: (C.TERRAIN_FARMLAND,) * 4 + (C.TERRAIN_PLAINS,) * 2,
    C.TERRAIN_COAST: (C.TERRAIN_COAST,) * 3 + (C.TERRAIN_PLAINS,) * 3,
    C.TERRAIN_MOUNTAIN: (C.TERRAIN_MOUNTAIN,) * 3 + (C.TERRAIN_HILLS,) * 3,
}


def _walkable(terrain):
    return terrain not in IMPASSABLE


def _weighted(rng, counts):
    total = sum(counts.values())
    pick = rng.random() * total
    for terrain, weight in counts.items():
        pick -= weight
        if pick <= 0:
            return terrain
    return next(reversed(counts))


def generate_field(contact_terrain, rng=None, neighbours=None):
    """Build the shared large tactical field for every new contact.

    ``neighbours`` carries the campaign terrains of the contact hex's
    overworld neighbours, so clustered biomes paint clearly themed fields.
    """
    if rng is None:
        from .rng import RNG, stable_int
        rng = RNG(stable_int(contact_terrain))
    counts = {C.TERRAIN_PLAINS: 1, contact_terrain: 4}
    if neighbours is None:
        neighbours = _THEME_NEIGHBOURS.get(contact_terrain,
                                           (contact_terrain,) * 3 +
                                           (C.TERRAIN_PLAINS,) * 3)
    for terrain in neighbours:
        if terrain in C.CAMPAIGN_TERRAINS:
            counts[terrain] = counts.get(terrain, 0) + 1
    width, height = C.BATTLE_WIDTH, C.BATTLE_HEIGHT
    clump_w, clump_h = width // 2, (height + 1) // 2
    clumps = [[_weighted(rng, counts) for _ in range(clump_w + 1)]
              for _ in range(clump_h + 1)]
    field = {}
    for r in range(height):
        for q in range(width):
            terrain = clumps[r // 2][q // 2]
            if rng.random() < 0.18:
                terrain = _weighted(rng, counts)
            field[(q, r)] = terrain
    if contact_terrain == C.TERRAIN_RIVER:
        # A water band with fording spots down the middle.
        for r in range(height):
            band = 8 + (1 if r % 4 in (1, 2) else 0)
            for q in (band, band + 1):
                field[(q, r)] = C.TERRAIN_RIVER
            if r % 5 == 2:
                field[(band, r)] = C.TERRAIN_PLAINS
    if contact_terrain == C.TERRAIN_MOUNTAIN:
        # Rocky spines with a walkable corridor through the pass.
        for r in range(height):
            if abs(r - height // 2) <= 1:
                continue
            if r % 3 == 0:
                field[(5, r)] = C.TERRAIN_MOUNTAIN
                field[(12, r)] = C.TERRAIN_MOUNTAIN
    if contact_terrain == C.TERRAIN_ROAD:
        for q in range(width):
            field[(q, height // 2)] = C.TERRAIN_ROAD
    # Both deployment columns must stand on walkable ground.
    for r in range(height):
        for q in list(range(0, 5)) + list(range(width - 5, width)):
            if not _walkable(field[(q, r)]):
                field[(q, r)] = C.TERRAIN_PLAINS
    _ensure_corridor(field)
    return field


def _ensure_corridor(field):
    """Guarantee the two deployment zones are mutually reachable."""
    width, height = C.BATTLE_WIDTH, C.BATTLE_HEIGHT
    start, goal = (2, height // 2), (width - 3, height // 2)
    seen, frontier = {start}, [start]
    while frontier:
        cur = frontier.pop()
        for nxt in G.neighbours(cur[0], cur[1], width, height):
            if nxt in seen or not _walkable(field.get(nxt, C.TERRAIN_PLAINS)):
                continue
            seen.add(nxt)
            frontier.append(nxt)
    if goal in seen:
        return
    for q in range(2, width - 2):
        field[(q, height // 2)] = C.TERRAIN_PLAINS


class Result:
    __slots__ = ("ok", "reason", "hit", "damage", "records")
    def __init__(self, ok, reason="", hit=False, damage=0, records=None):
        self.ok,self.reason,self.hit,self.damage,self.records=ok,reason,hit,damage,records or []
    def __bool__(self): return self.ok

class Battle:
    def __init__(self, campaign, attacker, defender, assault=False, canvas=None):
        self.campaign, self.attacker, self.defender, self.assault = campaign, attacker, defender, assault
        self.sides = {"attacker": [u.id for u in attacker.alive_units(campaign.units)[:C.COMPANY_CAP]],
                      "defender": [u.id for u in defender.alive_units(campaign.units)[:C.COMPANY_CAP]]}
        self.side_of = {uid: side for side, ids in self.sides.items() for uid in ids}
        self.positions, self.canvas, self.stun_until, self.log = {}, {}, {}, []
        self.alive = {uid: True for uid in self.side_of}
        self.ap = {uid: 2 for uid in self.side_of}
        self.atk_party, self.def_party = attacker, defender
        self.target_sid = defender.settlement_id if assault else None
        self.round, self.turn_side, self.winner = 1, "attacker", None
        terrain = campaign.world.terrain(attacker.hex)
        self.contact_terrain = terrain if terrain in C.CAMPAIGN_TERRAINS else C.TERRAIN_PLAINS
        if canvas is not None:
            # Restoring a saved fight: reuse the stored field so the load
            # never consumes fresh campaign randomness.
            self.canvas = dict(canvas)
        else:
            self._build_field()
        self.field = self.canvas
        self._place_units()

    @property
    def prepared_assault(self):
        """Whether this contact is a walled-holding assault, not a raid."""
        return self.assault

    @property
    def center(self):
        return (C.BATTLE_WIDTH // 2, C.BATTLE_HEIGHT // 2)

    @property
    def field_center(self):
        return self.center

    def _build_field(self):
        neighbours = [self.campaign.world.terrain(n)
                      for n in self.campaign.world.neighbours(self.attacker.hex)]
        self.canvas = generate_field(self.contact_terrain, self.campaign.rng,
                                     neighbours)
        self.field = self.canvas

    def _place_units(self):
        for side, ids in self.sides.items():
            columns = range(1, 4) if side == "attacker" else range(C.BATTLE_WIDTH-4, C.BATTLE_WIDTH-1)
            columns = list(columns)
            for n, uid in enumerate(ids):
                self.positions[uid] = (columns[n % 3], n // 3 + 1)

    def terrain(self, pos): return self.canvas.get(tuple(pos), C.TERRAIN_PLAINS)
    def human_side(self):
        return "attacker" if self.attacker.realm == self.campaign.player.key else "defender"
    def unit_at(self, pos):
        for uid, value in self.positions.items():
            if value == tuple(pos) and self.campaign.units[uid].alive: return self.campaign.units[uid]
        return None
    def living(self, side): return self.living_ids(side)
    def winner_side(self): return self.winner
    def available_moves(self, unit):
        origin=self.position_of(unit)
        return [p for p in G.neighbours(*origin,C.BATTLE_WIDTH,C.BATTLE_HEIGHT) if p not in self.positions.values() and _walkable(self.terrain(p))]
    def position_of(self, unit): return self.positions.get(unit.id)
    def all_living(self): return [self.campaign.units[i] for i in self.side_of if self.campaign.units[i].alive]
    def living_ids(self, side): return [i for i in self.sides[side] if self.campaign.units[i].alive]
    def over(self):
        if self.winner: return True
        alive = {s: self.living_ids(s) for s in self.sides}
        if not alive["attacker"] or not alive["defender"]:
            self.winner = "attacker" if alive["attacker"] else "defender"
        return self.winner is not None
    def is_stunned(self, unit): return self.stun_until.get(unit.id, 0) >= self.round
    def can_act(self, unit): return unit.alive and unit.id in self.side_of and self.side_of[unit.id] == self.turn_side and not self.is_stunned(unit)
    def has_bow(self, unit): return C.KITS[unit.kit]["bow"]
    def melee_in_range(self, attacker, target): return G.hex_distance(self.position_of(attacker), self.position_of(target)) == 1
    def ranged_in_range(self, attacker, target):
        d=G.hex_distance(self.position_of(attacker), self.position_of(target)); return 2 <= d <= 3
    def ranged_targets(self, attacker):
        return [self.campaign.units[i] for i in self.living_ids("defender" if self.side_of[attacker.id] == "attacker" else "attacker") if self.ranged_in_range(attacker, self.campaign.units[i]) and self._line_clear(self.position_of(attacker), self.position_of(self.campaign.units[i]))]
    def _line_clear(self, a, b):
        if not a or not b: return False
        distance = G.hex_distance(a, b)
        if distance <= 1:
            return True
        # Axial hexes are interpolated in cube space, so diagonal shots get
        # the same line-of-sight treatment as horizontal and vertical shots.
        def cube(pos):
            return (pos[0], pos[1], -pos[0] - pos[1])
        start, end = cube(a), cube(b)
        cells = []
        for step in range(1, distance):
            fraction = step / distance
            values = tuple(start[i] + (end[i] - start[i]) * fraction
                           for i in range(3))
            rounded = [round(value) for value in values]
            differences = [abs(rounded[i] - values[i]) for i in range(3)]
            largest = differences.index(max(differences))
            rounded[largest] = -rounded[(largest + 1) % 3] - rounded[(largest + 2) % 3]
            cells.append((rounded[0], rounded[1]))
        return not any(self.terrain(p) in BLOCKING_TERRAIN
                        for p in cells)
    def morale_hit_term(self, side):
        realm = self.campaign.realms.get(self.campaign.units[self.sides[side][0]].realm)
        return morale_hit_term(realm.morale if realm else 50)
    def _defender_mod(self, target):
        cover = C.BATTLE_TERRAIN_MOD.get(self.terrain(self.position_of(target)), 0)
        shield = -C.BATTLE_DEF_PER_SHIELD if C.KITS[target.kit]["shield"] else 0
        assault_cover = (-C.ASSAULT_DEFENDER_BONUS
                         if self.assault and self.side_of.get(target.id) ==
                         "defender" else 0)
        return cover + shield + assault_cover - target.stat("resolve") * C.BATTLE_DEF_PER_STAT
    def hit_chance(self, attacker, target, kind="melee"):
        stat = attacker.stat("ranged" if kind == "ranged" else "melee")
        distance = G.hex_distance(self.position_of(attacker), self.position_of(target))
        penalty = (distance-1)*C.BATTLE_RANGED_PENALTY if kind == "ranged" else 0
        return max(C.BATTLE_MIN_HIT, min(C.BATTLE_MAX_HIT, C.BATTLE_BASE_HIT + (stat-25)*C.BATTLE_HIT_PER_STAT + self._defender_mod(target) - penalty + self.morale_hit_term(self.side_of[attacker.id])))
    def _attack(self, attacker, target, kind):
        if not self.can_act(attacker): return Result(False, "that unit cannot act")
        if self.ap.get(attacker.id, 0) < 1: return Result(False, "no action points")
        if target.id not in self.side_of or self.side_of[target.id] == self.side_of[attacker.id] or not target.alive: return Result(False, "invalid target")
        if kind == "melee" and not self.melee_in_range(attacker,target): return Result(False,"melee requires an adjacent hex")
        if kind == "ranged":
            if not self.has_bow(attacker): return Result(False,"no bow in hand")
            if not self.ranged_in_range(attacker,target): return Result(False,"bow range is two to three hexes")
            if not self._line_clear(self.position_of(attacker), self.position_of(target)): return Result(False,"the shot is blocked")
        chance=self.hit_chance(attacker,target,kind); hit=self.campaign.rng.random() < chance; self.ap[attacker.id] -= 1
        attacker.add_combat_xp(C.XP_PARTICIPATION, self.campaign.rng)
        record = {"kind": kind, "unit": attacker.id, "target": target.id,
                  "hit": False, "reason": "miss"}
        if not hit:
            self.log.append(f"{attacker.name} misses {target.name}")
            return Result(True, "miss", False, 0, [record])
        damage=(C.BATTLE_MELEE_DAMAGE if kind == "melee" else C.BATTLE_RANGED_DAMAGE) + attacker.stat("melee" if kind == "melee" else "ranged")//15
        damage=max(1, damage-C.KITS[target.kit]["armour"]); target.current_hit_points=max(0,target.current_hit_points-damage); attacker.add_combat_xp(C.XP_HIT,self.campaign.rng)
        wounds_before = len(target.wounds)
        self._wound(target, damage)
        if not target.alive or target.current_hit_points <= 0: target.alive=False; self.alive[target.id] = False; attacker.add_combat_xp(C.XP_KILL,self.campaign.rng); self.log.append(f"{target.name} dies")
        else: self.log.append(f"{attacker.name} hits {target.name} for {damage}")
        self.over()
        reason = "slain" if not target.alive else ("wound" if len(target.wounds) > wounds_before else "hit")
        record.update(hit=True, reason=reason)
        return Result(True, reason, True, damage, [record])
    def _wound(self, target, damage):
        if damage >= max(3, target.max_hit_points//4):
            choices=["gash","bruise","shattered arm","maimed leg","lost eye","broken ribs"]
            wound=choices[self.campaign.rng.randint(0,len(choices)-1)]
            if C.WOUNDS[wound] == "permanent" and self.campaign.rng.random() > C.BATTLE_PERMANENT_WOUND_CHANCE: wound="gash"
            months = C.TEMP_WOUND_MONTHS if C.WOUNDS[wound] == "temporary" else None
            target.apply_wound(wound, months)
            target.max_hit_points = max(1, target.stat("hit_points"))
            target.current_hit_points = min(target.current_hit_points, target.max_hit_points)
            if damage >= target.stat("hit_points")*C.BATTLE_STUN_THRESHOLD and self.campaign.rng.random() < C.BATTLE_STUN_CHANCE: self.stun_until[target.id]=self.round+1
    def do_melee(self, attacker, target): return self._attack(attacker,target,"melee")
    def do_ranged(self, attacker, target): return self._attack(attacker,target,"ranged")
    def move(self, unit, target):
        if not self.can_act(unit): return Result(False,"that unit cannot act")
        if self.ap.get(unit.id, 0) < 1: return Result(False,"no action points")
        if target not in self.canvas or target in self.positions.values(): return Result(False,"occupied or outside field")
        if not _walkable(self.terrain(target)): return Result(False,"rivers and bare rock cannot be entered")
        if G.hex_distance(self.position_of(unit),target) != 1: return Result(False,"move one adjacent hex")
        self.positions[unit.id]=tuple(target); self.ap[unit.id] -= 1; return Result(True)
    def do_move(self, unit, target): return self.move(unit, target)

    # ------------------------------------------------------- side turns
    def end_turn(self):
        """Hand the whole fight to the other side and refresh their AP."""
        if self.over(): return Result(False, "battle is already over")
        self.turn_side = "defender" if self.turn_side == "attacker" else "attacker"
        if self.turn_side == "attacker":
            self.round += 1
        for uid in self.sides[self.turn_side]:
            self.ap[uid] = 2
        return Result(True, "the other side takes the field")

    def end_player_turn(self):
        """End the human side; the scripted foe answers with a full turn."""
        if self.over(): return Result(False, "battle is already over")
        res = self.end_turn()
        if not res.ok:
            return res
        if not self.over() and self.turn_side != self.human_side():
            records = self.scripted_turn()
            res = Result(True, "the foe takes %d action%s" %
                         (len(records), "" if len(records) == 1 else "s"))
            res.records = records
            return res
        res.records = []
        return res

    def _scripted_act(self, unit):
        """One deterministic decision for an AI warrior using player rules."""
        foes_side = "defender" if self.side_of[unit.id] == "attacker" else "attacker"
        foes = [self.campaign.units[i] for i in self.living_ids(foes_side)]
        if not foes:
            return None
        foes.sort(key=lambda f: (self.position_of(f), f.id))
        for foe in foes:
            if self.melee_in_range(unit, foe):
                res = self.do_melee(unit, foe)
                return {"kind": "melee", "unit": unit.id, "target": foe.id,
                        "hit": res.hit, "damage": res.damage,
                        "reason": res.reason}
        if self.has_bow(unit):
            shots = [f for f in foes
                     if self.ranged_in_range(unit, f) and
                     self._line_clear(self.position_of(unit),
                                      self.position_of(f))]
            if shots:
                res = self.do_ranged(unit, shots[0])
                return {"kind": "ranged", "unit": unit.id,
                        "target": shots[0].id, "hit": res.hit,
                        "damage": res.damage, "reason": res.reason}
        nearest = min(foes, key=lambda f: (G.hex_distance(self.position_of(unit), self.position_of(f)), f.id))
        origin = self.position_of(unit)
        goal = self.position_of(nearest)
        steps = sorted(G.neighbours(*origin, C.BATTLE_WIDTH, C.BATTLE_HEIGHT),
                       key=lambda p: (G.hex_distance(p, goal), p))
        for step in steps:
            if step in self.positions.values() or not _walkable(self.terrain(step)):
                continue
            before = self.position_of(unit)
            if self.move(unit, step).ok:
                return {"kind": "move", "unit": unit.id, "target": None,
                        "from": before, "to": step, "hit": False,
                        "damage": 0, "reason": "march"}
        return None

    def scripted_turn(self):
        """Play the acting side's full turn with the shared rules, then end
        it.  Stunned warriors are skipped; nothing invents free damage."""
        records = []
        if self.over():
            return records
        for uid in list(self.sides[self.turn_side]):
            unit = self.campaign.units.get(uid)
            if not unit or not unit.alive or self.is_stunned(unit):
                continue
            for _ in range(2):
                if self.over() or self.ap.get(uid, 0) < 1:
                    break
                record = self._scripted_act(unit)
                if record is None:
                    break
                records.append(record)
        self.end_turn()
        return records

    def auto_resolve(self, rng=None):
        """Finish the fight with alternating scripted side turns."""
        guard = 0
        while not self.over() and guard < 120:
            self.scripted_turn()
            guard += 1
        if not self.over():
            self.winner = ("attacker"
                           if len(self.living_ids("attacker")) >=
                           len(self.living_ids("defender")) else "defender")
        return self.winner

def morale_hit_term(morale): return (float(morale)-50.0)/100.0*C.MORALE_HIT_FACTOR
def hit_chance_for(battle, attacker, kind="melee"):
    foe = next((battle.campaign.units[i] for i in battle.living_ids("defender" if battle.side_of[attacker.id] == "attacker" else "attacker")), None)
    return battle.hit_chance(attacker, foe, kind) if foe else 0
def battle_from_contact(campaign, attacker, defender, assault=False):
    if not attacker or not defender or not attacker.unit_ids or not defender.unit_ids: return None
    return Battle(campaign, attacker, defender, assault)
def writeback(campaign, battle):
    player_key = campaign.player.key
    for party in (battle.attacker, battle.defender):
        for uid in list(party.unit_ids):
            unit = campaign.units.get(uid)
            if unit is not None and not unit.alive and uid in party.unit_ids:
                if unit.realm == player_key:
                    campaign.notes.append("%s fell in battle" % unit.name)
        party.unit_ids = [i for i in party.unit_ids if campaign.units[i].alive]
    if battle.assault and battle.winner == "attacker" and battle.defender.settlement_id is not None: campaign._conquer(battle.defender.settlement_id,battle.attacker.realm)
    campaign._ensure_succession(campaign.realms.get(battle.attacker.realm)) if battle.attacker.realm in campaign.realms else None
    campaign._ensure_succession(campaign.realms.get(battle.defender.realm)) if battle.defender.realm in campaign.realms else None
    campaign.discard_pending(battle); campaign.check_end_conditions()
