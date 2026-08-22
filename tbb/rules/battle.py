"""Turn-based hex battle, wired to campaign contact.

The battle hex map is a local patch of the campaign world (radius
BATTLE_RADIUS around the contact hex), so woods, hills, rivers and the
assaulted village actually appear. Morale changes hit chance only. Melee and
ranged actions; stuns, temporary and permanent wounds and death are all
possible. Experience comes only from combat.
"""
from . import constants as C
from . import terrain as G
from .rng import RNG


class Result:
    __slots__ = ("ok", "reason")

    def __init__(self, ok, reason=""):
        self.ok = ok
        self.reason = reason

    def __bool__(self):
        return self.ok


class Battle:
    def __init__(self, campaign, atk_party, def_party, assault=False,
                 target_sid=None, seed=None):
        self.campaign = campaign
        self.atk_party = atk_party
        self.def_party = def_party
        self.assault = assault
        self.target_sid = target_sid
        self.rng = RNG(seed if seed is not None
                       else campaign.rng.randint(1, 2 ** 31 - 1))
        self._seed_used = self.rng.seed
        self.center = self._contact_center()
        self.canvas = self._build_canvas()
        self.sides = {"attacker": [], "defender": []}
        self.side_of = {}
        self.positions = {}
        self.alive = {}          # uid -> bool
        self.ap = {}
        self.stun_until = {}
        self.battle_xp = {}
        self.log = []
        self.round = 1
        self.turn_side = "attacker"   # whose phase the UI shows
        self.winner = None
        self._rewards_applied = False
        self._place_units()
        self.turn_side = self.human_side()
        self._start_phase()

    # ----------------------------------------------------------- helpers
    def _contact_center(self):
        if self.assault:
            return tuple(self.campaign.settlements[self.target_sid].hex)
        return tuple(self.def_party.hex)

    def _build_canvas(self):
        q0, r0 = self.center
        w, h = self.campaign.world.width, self.campaign.world.height
        radius = C.BATTLE_RADIUS
        canvas = {}
        for dq in range(-radius, radius + 1):
            for dr in range(-radius, radius + 1):
                nq, nr = q0 + dq, r0 + dr
                if max(abs(dq), abs(dr), abs(-dq - dr)) > radius:
                    continue
                if not (0 <= nq < w and 0 <= nr < h):
                    continue
                canvas[(nq, nr)] = self.campaign.world.terrain((nq, nr))
        if self.assault:
            canvas[tuple(self.campaign.settlements[self.target_sid].hex)] = \
                C.TERRAIN_VILLAGE
        return canvas

    def _units_of(self, party):
        return [self.campaign.units[u] for u in party.unit_ids
                if u in self.campaign.units and self.campaign.units[u].alive]

    def _seat(self, side, party, prefer):
        units = self._units_of(party)[: C.BATTLE_SIDE_CAP]
        cells = [c for c in self.canvas
                 if c not in self.positions.values()]

        def ring(p):
            return G.hex_distance(p, self.center)

        cells.sort(key=ring, reverse=(prefer == "outer"))
        # jitter within bands so layouts do not look mechanical
        banded = {}
        for c in cells:
            banded.setdefault(ring(c), []).append(c)
        flat = []
        for k in sorted(banded):
            self.rng.shuffle(banded[k])
            flat.extend(banded[k])
        for u in units:
            if not flat:
                break
            spot = flat.pop(0)
            self.sides[side].append(u.id)
            self.side_of[u.id] = side
            self.positions[u.id] = spot
            self.alive[u.id] = True
            self.battle_xp[u.id] = 0

    def _place_units(self):
        self._seat("attacker", self.atk_party, "outer")
        self._seat("defender", self.def_party, "inner")

    def _start_phase(self):
        for uid in self.sides[self.turn_side]:
            if self.alive.get(uid):
                self.ap[uid] = self.max_ap()

    def max_ap(self):
        return 2

    # ----------------------------------------------------------- queries
    def living(self, side):
        return [self.campaign.units[u] for u in self.sides[side]
                if self.alive.get(u) and self.campaign.units[u].alive]

    def all_living(self):
        return self.living("attacker") + self.living("defender")

    def terrain(self, pos):
        return self.canvas.get(tuple(pos), C.TERRAIN_PLAIN)

    def unit_at(self, pos):
        pos = tuple(pos)
        for uid, p in self.positions.items():
            if p == pos:
                return self.campaign.units[uid]
        return None

    def position_of(self, u):
        return self.positions.get(u.id)

    def ap_left(self, u):
        return self.ap.get(u.id, 0)

    def is_stunned(self, u):
        return u.id in self.stun_until and self.round <= self.stun_until[u.id]

    def can_act(self, u):
        return (u.alive and not self.is_stunned(u)
                and self.ap.get(u.id, 0) > 0
                and self.side_of.get(u.id) == self.turn_side)

    def has_bow(self, u):
        return bool(C.KIT_IS_BOW.get(u.kit, 0))

    def human_side(self):
        pk = self.campaign.player.key
        for s in ("attacker", "defender"):
            if any(self.campaign.units[u].realm == pk for u in self.sides[s]):
                return s
        return "attacker"

    def human_realm_uids(self):
        pk = self.campaign.player.key
        return [u for u in self.sides[self.human_side()]
                if self.campaign.units[u].realm == pk]

    # ------------------------------------------------------------- range
    def available_moves(self, u):
        if not self.can_act(u):
            return []
        pos = self.positions.get(u.id)
        if pos is None:
            return []
        out = []
        for n in self.campaign.world.neighbours(pos):
            n = tuple(n)
            if n not in self.canvas or n in self.positions.values():
                continue
            if not G.is_passable(self.canvas[n]):
                continue
            out.append(n)
        return out

    def melee_targets(self, u):
        if not self.can_act(u):
            return []
        pos = self.positions[u.id]
        out = []
        for n in G.neighbours(*pos, self.campaign.world.width,
                              self.campaign.world.height):
            if n not in self.canvas:
                continue
            t = self.unit_at(n)
            if t is not None and t.alive and \
                    self.side_of.get(t.id) != self.side_of.get(u.id):
                out.append(t)
        return out

    def ranged_targets(self, u, max_dist=3):
        if not self.can_act(u) or not self.has_bow(u):
            return []
        pos = self.positions[u.id]
        out = []
        for t in self.all_living():
            tp = self.positions.get(t.id)
            if tp is None or t.id == u.id:
                continue
            if self.side_of.get(t.id) == self.side_of.get(u.id):
                continue
            d = G.hex_distance(pos, tp)
            if 1 <= d <= max_dist:
                out.append(t)
        return out

    def melee_in_range(self, u, tgt):
        return G.hex_distance(self.positions[u.id], self.positions[tgt.id]) <= 1

    def ranged_in_range(self, u, tgt):
        d = G.hex_distance(self.positions[u.id], self.positions[tgt.id])
        return 1 <= d <= 3

    # ------------------------------------------------------------ actions
    def do_move(self, u, pos):
        if not self.can_act(u):
            return Result(False, "cannot act now")
        pos = tuple(pos)
        if pos not in self.canvas:
            return Result(False, "outside the field")
        if pos in self.positions.values():
            return Result(False, "that hex is held")
        if G.hex_distance(self.positions[u.id], pos) > 1:
            return Result(False, "too far to step")
        if not G.is_passable(self.canvas[pos]):
            return Result(False, "cannot step onto %s" % self.canvas[pos])
        self.positions[u.id] = pos
        self.ap[u.id] -= 1
        self.log.append("%s steps onto %s" % (u.name, self.canvas[pos]))
        return Result(True)

    def do_wait(self, u):
        if not self.can_act(u):
            return Result(False, "cannot act now")
        self.ap[u.id] = 0
        self.log.append("%s holds" % u.name)
        self._check_end()
        return Result(True)

    def do_melee(self, u, tgt):
        if not self.can_act(u):
            return Result(False, "cannot act now")
        if not tgt.alive or self.side_of.get(tgt.id) == self.side_of.get(u.id):
            return Result(False, "no target in reach")
        if not self.melee_in_range(u, tgt):
            return Result(False, "not adjacent")
        self.ap[u.id] -= 1
        msg = self._resolve_melee(u, tgt)
        self._check_end()
        return Result(True, msg)

    def do_ranged(self, u, tgt):
        if not self.can_act(u):
            return Result(False, "cannot act now")
        if not self.has_bow(u):
            return Result(False, "no bow in hand")
        if not tgt.alive or self.side_of.get(tgt.id) == self.side_of.get(u.id):
            return Result(False, "no target")
        d = G.hex_distance(self.positions[u.id], self.positions[tgt.id])
        if not (1 <= d <= 3):
            return Result(False, "out of bow range")
        self.ap[u.id] -= 1
        msg = self._resolve_ranged(u, tgt, d)
        self._check_end()
        return Result(True, msg)

    # ------------------------------------------------------------- combat
    def _morale_bonus(self, u):
        realm = self.campaign.realms.get(u.realm)
        if realm is None or u.realm is None:
            m = 50.0
        else:
            m = realm.morale
        return (m - 50.0) / 100.0 * C.MORALE_HIT_FACTOR

    def _resolve_melee(self, u, tgt):
        defence = -C.BATTLE_DEF_PER_SHIELD if C.KIT_SHIELD.get(tgt.kit) else 0
        hit = (C.BATTLE_BASE_HIT +
               (u.stat("melee") - 25) * C.BATTLE_HIT_PER_STAT +
               self._morale_bonus(u) + defence +
               C.BATTLE_TERRAIN_MOD.get(self.canvas[self.positions[tgt.id]], 0))
        hit = max(C.BATTLE_MIN_HIT, min(C.BATTLE_MAX_HIT, hit))
        self.log.append("%s lashes at %s (hit %.0f%%)"
                        % (u.name, tgt.name, hit * 100))
        if self.rng.random() >= hit:
            self._gain_xp(u, C.XP_PARTICIPATION)
            self.log.append("  it misses")
            return "miss"
        self._gain_xp(u, C.XP_HIT)
        return self._deal_damage(u, tgt, "melee")

    def _resolve_ranged(self, u, tgt, dist):
        defence = C.BATTLE_DEF_PER_SHIELD if C.KIT_SHIELD.get(tgt.kit) else 0
        hit = (C.BATTLE_BASE_HIT +
               (u.stat("ranged") - 25) * C.BATTLE_HIT_PER_STAT +
               self._morale_bonus(u) - defence +
               C.BATTLE_TERRAIN_MOD.get(self.canvas[self.positions[tgt.id]], 0) -
               (dist - 1) * C.BATTLE_RANGED_PENALTY)
        hit = max(C.BATTLE_RANGED_MIN, min(C.BATTLE_MAX_HIT, hit))
        self.log.append("%s looses at %s (%.0f%%)"
                        % (u.name, tgt.name, hit * 100))
        if self.rng.random() >= hit:
            self._gain_xp(u, C.XP_PARTICIPATION)
            self.log.append("the shaft goes wide")
            return "miss"
        self._gain_xp(u, C.XP_HIT)
        return self._deal_damage(u, tgt, "ranged")

    def _deal_damage(self, u, tgt, kind):
        if kind == "melee":
            raw = C.BATTLE_MELEE_DMG + C.BATTLE_MELEE_STR_SCALE * \
                u.stat("toughness")
        else:
            raw = C.BATTLE_RANGED_DMG + C.BATTLE_RANGED_STA_SCALE * \
                u.stat("initiative")
        armour = C.KIT_ARMOUR.get(tgt.kit, 0)
        dmg = max(0, int((raw - armour) * (0.5 + self.rng.random() * 0.9)))
        return self._resolve_damage(u, tgt, dmg)

    def _resolve_damage(self, u, tgt, dmg):
        if dmg <= 0:
            self.log.append("%s's steel turns the blow" % tgt.name)
            return "blocked"
        tgh = max(1, tgt.stat("toughness"))
        if dmg > tgh * C.BATTLE_DEATH_MULT:
            if self.rng.random() < 0.75:
                self._kill(u, tgt)
                return "slain"
            self._wound(tgt, permanent=True)
            return "permanent wound"
        elif dmg > tgh:
            if self.rng.random() < C.BATTLE_PERM_CHANCE:
                self._wound(tgt, permanent=True)
                return "permanent wound"
            self._wound(tgt, permanent=False)
            return "wound"
        elif dmg > tgh * 0.5:
            self._wound(tgt, permanent=False)
            return "wound"
        else:
            if dmg > tgh * C.BATTLE_STUN_THRESH and \
                    self.rng.random() < C.BATTLE_STUN_CHANCE:
                self.stun_until[tgt.id] = self.round + 1
                self.log.append("%s staggers" % tgt.name)
                return "stun"
            self.log.append("%s grazes %s" % (u.name, tgt.name))
            return "graze"

    def _wound(self, tgt, permanent):
        if permanent:
            name = self.rng.choice(["shattered arm", "maimed leg", "lost eye"])
            if name not in tgt.wounds:
                tgt.wounds.append(name)
            self.log.append("%s is %s for life" % (tgt.name, name))
        else:
            name = self.rng.choice(["gash", "bruise", "broken ribs"])
            if name not in tgt.battle_wounds:
                tgt.battle_wounds.append(name)
            self.log.append("%s takes a %s" % (tgt.name, name))

    def _kill(self, u, tgt):
        tgt.alive = False
        self.alive[tgt.id] = False
        self._gain_xp(u, C.XP_KILL)
        self.log.append("%s slays %s" % (u.name, tgt.name))

    def _gain_xp(self, u, amount):
        u.xp += amount
        self.battle_xp[u.id] = self.battle_xp.get(u.id, 0) + amount

    # ----------------------------------------------------------- turn flow
    def over(self):
        return bool(self.winner)

    def winner_side(self):
        return self.winner

    def end_player_turn(self):
        if self.winner:
            return Result(False, "battle over")
        for u in self.sides[self.turn_side]:
            if self.alive.get(u):
                self.ap[u] = 0
        other = "defender" if self.turn_side == "attacker" else "attacker"
        self.turn_side = other
        self._start_phase()
        self._ai_turn(other)
        if self.winner:
            return Result(True, "battle ended")
        self.turn_side = self.human_side() if self.has_party(self.human_side()) \
            else "attacker"
        self._new_round()
        return Result(True)

    def has_party(self, side):
        return bool(self.living(side))

    def _new_round(self):
        self.round += 1
        side = self.human_side()
        if not self.living(side):
            side = "attacker" if self.living("attacker") else "defender"
        self.turn_side = side
        self._start_phase()
        self._check_end()

    def _ai_turn(self, side):
        for u in self._ai_units(side):
            if self.winner:
                break
            guards = 0
            while self.can_act(u):
                self._ai_act(u)
                guards += 1
                if guards > 10:
                    break

    def _ai_units(self, side):
        units = self.living(side)
        units.sort(key=lambda u: (-u.stat("initiative"), u.id))
        return units

    def _ai_act(self, u):
        foe = self._nearest_enemy(u)
        if foe is None:
            self.do_wait(u)
            return
        if self.has_bow(u) and self.ranged_in_range(u, foe):
            self.do_ranged(u, foe)
            return
        if self.melee_in_range(u, foe):
            self.do_melee(u, foe)
            return
        nxt = self._step_toward(u, foe)
        if nxt is not None:
            self.do_move(u, nxt)
        else:
            self.do_wait(u)

    def _nearest_enemy(self, u):
        foes = self.living("defender" if self.side_of[u.id] == "attacker"
                           else "attacker")
        if not foes:
            return None
        return min(foes, key=lambda f: G.hex_distance(
            self.positions[u.id], self.positions[f.id]))

    def _step_toward(self, u, foe):
        moves = self.available_moves(u)
        if not moves:
            return None

        def key(p):
            return (G.hex_distance(p, self.positions[foe.id]) * 10
                    - self.rng.randint(0, 2))
        return min(moves, key=key)

    # -------------------------------------------------------- game end
    def _check_end(self):
        if self.winner:
            return
        att = self.living("attacker")
        deff = self.living("defender")
        if not att:
            self.winner = "defender"
        elif not deff:
            self.winner = "attacker"
        elif self.round > 80:
            a = sum(u.stat("melee") for u in att)
            d = sum(u.stat("melee") for u in deff)
            self.winner = "attacker" if a >= d else "defender"
        if self.winner and not self._rewards_applied:
            self._apply_rewards()

    def _apply_rewards(self):
        if self._rewards_applied:
            return
        self._rewards_applied = True
        for u in self.all_living():
            bands = u.xp // C.XP_PER_GAIN - getattr(u, "_applied_gains", 0)
            for _ in range(bands):
                u.gain_from_combat(self.rng)
            u._applied_gains = getattr(u, "_applied_gains", 0) + bands
        for u in self.all_living():
            u.battle_wounds = []

    def auto_resolve(self, parent_rng=None):
        while not self.winner:
            self._ai_turn("attacker")
            if self.winner:
                break
            self._ai_turn("defender")
            if self.winner:
                break
            self._new_round()
        return self.winner


def morale_hit_term(morale):
    """How much a realm's morale shifts a fighter's hit window (nothing else).
    Morale changes hit chance only - no crits, no damage, no routs."""
    return (float(morale) - 50.0) / 100.0 * C.MORALE_HIT_FACTOR


def hit_chance_for(battle, u, kind):
    """The stat + morale portion of the hit-window formula. Terrain/shield
    terms for the target are fixed between two identical battles, so this
    auxiliary keeps the morale comparison stable and testable."""
    if kind == "melee":
        base = (C.BATTLE_BASE_HIT +
                (u.stat("melee") - 25) * C.BATTLE_HIT_PER_STAT)
    else:
        base = (C.BATTLE_BASE_HIT +
                (u.stat("ranged") - 25) * C.BATTLE_HIT_PER_STAT)
    return base + battle._morale_bonus(u)


def battle_from_contact(campaign, atk_party, def_party, assault):
    target_sid = None
    if assault:
        target_sid = def_party.settlement_id
    return Battle(campaign, atk_party, def_party, assault=assault,
                  target_sid=target_sid)


def writeback(campaign, battle):
    """Apply battle outcome back into campaign state."""
    for side in ("attacker", "defender"):
        for uid in battle.sides[side]:
            u = campaign.units[uid]
            if not u.alive:
                if uid in battle.atk_party.unit_ids:
                    battle.atk_party.remove(uid)
                if uid in battle.def_party.unit_ids:
                    battle.def_party.remove(uid)
    if battle.assault and battle.winner == "attacker":
        atk_realm = battle.atk_party.realm
        if atk_realm is not None:
            campaign._conquer(battle.target_sid, atk_realm)
    for u in campaign.units.values():
        u.stun_until = None
    for b in list(campaign.pending_battles):
        if b.over():
            campaign.discard_pending(b)
    for realm in list(campaign.realms.values()):
        if realm.hero is not None and not campaign.units[realm.hero].alive:
            campaign._ensure_succession(realm)
    campaign.check_end_conditions()
    pk = campaign.player.key
    player_in = any(campaign.units[uid].realm == pk
                    for uid in (battle.sides["attacker"] + battle.sides["defender"])
                    if uid in battle.side_of)
    player_side = battle.human_side()
    if player_in and battle.winner == player_side:
        campaign.notes.append("Your banner takes the field")
    elif player_in:
        campaign.notes.append("The field is lost to you")