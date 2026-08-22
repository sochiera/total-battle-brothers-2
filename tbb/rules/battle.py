"""Individual-unit 14x11 tactical battles, independent of pygame."""
from . import constants as C
from . import terrain as G

BLOCKING_TERRAIN = C.BATTLE_BLOCKING_TERRAIN


def generate_field(contact_terrain, rng=None):
    """Build the shared 14x11 tactical field for every new contact."""
    field = {}
    for r in range(C.BATTLE_HEIGHT):
        for q in range(C.BATTLE_WIDTH):
            terrain = C.TERRAIN_PLAINS
            if contact_terrain == C.TERRAIN_FOREST:
                terrain = (C.TERRAIN_FOREST
                           if (q // 2 + r // 2) % 3 != 1 else
                           C.TERRAIN_PLAINS)
            elif contact_terrain == C.TERRAIN_HILLS:
                terrain = C.TERRAIN_HILLS if r in (3, 4, 5) else C.TERRAIN_PLAINS
            elif contact_terrain == C.TERRAIN_RIVER:
                terrain = C.TERRAIN_RIVER if q in (6, 7) else C.TERRAIN_PLAINS
            elif contact_terrain == C.TERRAIN_ROAD:
                terrain = C.TERRAIN_ROAD if r in (5, 6) else C.TERRAIN_PLAINS
            elif contact_terrain == C.TERRAIN_VILLAGE:
                terrain = C.TERRAIN_VILLAGE if (q + r) % 5 == 0 else C.TERRAIN_PLAINS
            elif contact_terrain == C.TERRAIN_RUINS:
                terrain = C.TERRAIN_RUINS if (q + 2 * r) % 6 in (0, 1) else C.TERRAIN_PLAINS
            field[(q, r)] = terrain
    return field

class Result:
    __slots__ = ("ok", "reason", "hit", "damage")
    def __init__(self, ok, reason="", hit=False, damage=0): self.ok,self.reason,self.hit,self.damage=ok,reason,hit,damage
    def __bool__(self): return self.ok

class Battle:
    def __init__(self, campaign, attacker, defender, assault=False):
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
        if terrain == C.TERRAIN_VILLAGE and assault: terrain = C.TERRAIN_VILLAGE
        self.contact_terrain = terrain if terrain in C.CAMPAIGN_TERRAINS else C.TERRAIN_PLAINS
        self._build_field()
        self._place_units()

    @property
    def center(self):
        return (C.BATTLE_WIDTH // 2, C.BATTLE_HEIGHT // 2)

    @property
    def field_center(self):
        return self.center

    def _build_field(self):
        self.canvas = generate_field(self.contact_terrain, self.campaign.rng)
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
        return [p for p in G.neighbours(*origin,C.BATTLE_WIDTH,C.BATTLE_HEIGHT) if p not in self.positions.values() and self.terrain(p) != C.TERRAIN_RIVER]
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
        return cover + shield - target.stat("resolve") * C.BATTLE_DEF_PER_STAT
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
        if not hit: self.log.append(f"{attacker.name} misses {target.name}"); self._finish_action(); return Result(True,"miss",False,0)
        damage=(C.BATTLE_MELEE_DAMAGE if kind == "melee" else C.BATTLE_RANGED_DAMAGE) + attacker.stat("melee" if kind == "melee" else "ranged")//15
        damage=max(1, damage-C.KITS[target.kit]["armour"]); target.current_hit_points=max(0,target.current_hit_points-damage); attacker.add_combat_xp(C.XP_HIT,self.campaign.rng)
        wounds_before = len(target.wounds)
        self._wound(target, damage)
        if not target.alive or target.current_hit_points <= 0: target.alive=False; self.alive[target.id] = False; attacker.add_combat_xp(C.XP_KILL,self.campaign.rng); self.log.append(f"{target.name} dies")
        else: self.log.append(f"{attacker.name} hits {target.name} for {damage}")
        self._finish_action(); self.over()
        reason = "slain" if not target.alive else ("wound" if len(target.wounds) > wounds_before else "hit")
        return Result(True, reason, True, damage)
    def _finish_action(self):
        self.turn_side = "defender" if self.turn_side == "attacker" else "attacker"
        if self.turn_side == "attacker": self.round += 1
    def _wound(self, target, damage):
        if damage >= max(3, target.max_hit_points//4):
            choices=["gash","bruise","shattered arm","maimed leg","lost eye","broken ribs"]
            wound=choices[self.campaign.rng.randint(0,len(choices)-1)]
            if C.WOUNDS[wound] == "permanent" and self.campaign.rng.random() > C.BATTLE_PERMANENT_WOUND_CHANCE: wound="gash"
            target.wounds.append(wound)
            target.max_hit_points = max(1, target.stat("hit_points"))
            target.current_hit_points = min(target.current_hit_points, target.max_hit_points)
            if damage >= target.stat("hit_points")*C.BATTLE_STUN_THRESHOLD and self.campaign.rng.random() < C.BATTLE_STUN_CHANCE: self.stun_until[target.id]=self.round+1
    def do_melee(self, attacker, target): return self._attack(attacker,target,"melee")
    def do_ranged(self, attacker, target): return self._attack(attacker,target,"ranged")
    def move(self, unit, target):
        if not self.can_act(unit): return Result(False,"that unit cannot act")
        if self.ap.get(unit.id, 0) < 1: return Result(False,"no action points")
        if target not in self.canvas or target in self.positions.values(): return Result(False,"occupied or outside field")
        if G.hex_distance(self.position_of(unit),target) != 1: return Result(False,"move one adjacent hex")
        self.positions[unit.id]=tuple(target); self.ap[unit.id] -= 1; self._finish_action(); return Result(True)
    def do_move(self, unit, target): return self.move(unit, target)
    def end_player_turn(self):
        if self.over(): return Result(False, "battle is already over")
        self.turn_side = "defender" if self.turn_side == "attacker" else "attacker"
        if self.turn_side == "attacker":
            self.round += 1
            for uid in self.side_of: self.ap[uid] = 2
        return Result(True, "the foe stirs")
    def end_turn(self): self._finish_action(); return Result(True)
    def auto_resolve(self, rng=None):
        rng = rng or self.campaign.rng
        guard=0
        while not self.over() and guard < 300:
            side=self.turn_side; enemies="defender" if side == "attacker" else "attacker"
            ours=[self.campaign.units[i] for i in self.living_ids(side)]; foes=[self.campaign.units[i] for i in self.living_ids(enemies)]
            if not ours or not foes: break
            unit=ours[guard % len(ours)]; target=foes[guard % len(foes)]; self.positions[target.id]=self.positions[target.id]
            # deterministic close combat for compact auto-resolve
            self.positions[unit.id]=(self.positions[target.id][0]-1 if side == "attacker" else self.positions[target.id][0]+1,self.positions[target.id][1])
            if self.melee_in_range(unit,target): self._attack(unit,target,"melee")
            else: self._finish_action()
            guard += 1
        if not self.over(): self.winner="attacker" if len(self.living_ids("attacker")) >= len(self.living_ids("defender")) else "defender"
        return self.winner

def morale_hit_term(morale): return (float(morale)-50.0)/100.0*C.MORALE_HIT_FACTOR
def hit_chance_for(battle, attacker, kind="melee"):
    foe = next((battle.campaign.units[i] for i in battle.living_ids("defender" if battle.side_of[attacker.id] == "attacker" else "attacker")), None)
    return battle.hit_chance(attacker, foe, kind) if foe else 0
def battle_from_contact(campaign, attacker, defender, assault=False):
    if not attacker or not defender or not attacker.unit_ids or not defender.unit_ids: return None
    return Battle(campaign, attacker, defender, assault)
def writeback(campaign, battle):
    for party in (battle.attacker,battle.defender): party.unit_ids=[i for i in party.unit_ids if campaign.units[i].alive]
    if battle.assault and battle.winner == "attacker" and battle.defender.settlement_id is not None: campaign._conquer(battle.defender.settlement_id,battle.attacker.realm)
    campaign._ensure_succession(campaign.realms.get(battle.attacker.realm)) if battle.attacker.realm in campaign.realms else None
    campaign._ensure_succession(campaign.realms.get(battle.defender.realm)) if battle.defender.realm in campaign.realms else None
    campaign.discard_pending(battle); campaign.check_end_conditions()
