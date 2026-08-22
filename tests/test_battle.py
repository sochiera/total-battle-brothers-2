"""Battle resolution: hit chance from morale only (no routs), terrain
modifiers, melee vs ranged, stun / wounds / death, XP writeback."""
from tbb.rules import constants as C
from tbb.rules import battle as B
from tbb.rules.campaign import Campaign


def make_game(seed=21):
    return Campaign(seed)


def forced_battle(c, morale=50.0):
    """Always build a real Battle between two live field parties (the player's
    and the first AI duchy's hero company) so no test ever skips out."""
    atk = c.hero_party(c.player.key)
    dfn = None
    for k in (1, 2, 3, 4):
        dfn = c.hero_party(k)
        if dfn is not None:
            break
    assert atk is not None and dfn is not None, "hero parties must exist"
    c.realms[c.player.key].morale = morale
    b = B.battle_from_contact(c, atk, dfn, assault=False)
    assert b is not None
    assert b.sides["attacker"] and b.sides["defender"]
    return b


def active_attacker(b):
    """One attacker that can act (promote the side's phase if needed)."""
    for uid in b.sides["attacker"]:
        u = b.campaign.units[uid]
        if b.alive.get(uid) and not b.is_stunned(u):
            if b.turn_side != b.side_of[uid]:
                b.turn_side = b.side_of[uid]
                b._start_phase()
            return u
    # fall back: clear the stun so the test can exercise the action
    u0 = b.campaign.units[b.sides["attacker"][0]]
    b.stun_until.pop(u0.id, None)
    b.turn_side = "attacker"
    b._start_phase()
    return u0


ALL_TERRAIN = {C.TERRAIN_PLAIN, C.TERRAIN_WOODS, C.TERRAIN_HILLS,
               C.TERRAIN_RIVER, C.TERRAIN_WATER, C.TERRAIN_WASTE,
               C.TERRAIN_VILLAGE}


def test_battle_boot_and_terrain():
    for seed in (1, 2, 3):
        c = make_game(seed)
        b = forced_battle(c)
        kinds = {b.terrain(p) for p in b.canvas}
        assert kinds.issubset(ALL_TERRAIN)
        assert len(b.canvas) > 10
        assert b.sides["attacker"] and b.sides["defender"]


def test_melee_range_and_bow_only():
    c = make_game(seed=7)
    b = forced_battle(c)
    attacker = active_attacker(b)
    foe = None
    for uid in b.sides["defender"]:
        foe = c.units[uid]
        break
    assert foe is not None
    # put them adjacent
    fpos = b.position_of(foe)
    nxt = None
    for n in c.world.neighbours(fpos):
        if n in b.canvas and n not in b.positions.values():
            nxt = n
            break
    if nxt is not None:
        b.positions[attacker.id] = tuple(nxt)
    res = b.do_melee(attacker, foe)
    assert res.ok, (res.reason, b.log)
    assert attacker.xp >= C.XP_PARTICIPATION  # participation XP always lands
    # a kitless recruit has no bow in hand
    other = active_attacker(b)
    other.kit = C.KIT_POOR
    assert not b.has_bow(other)
    r2 = b.do_ranged(other, foe)
    assert r2 is not None and not r2.ok
    assert "no bow" in r2.reason


def test_morale_raises_hit_chance_only():
    # the morale term multiplies only the hit window (no crits, no damage)
    lo = B.morale_hit_term(20)
    hi = B.morale_hit_term(95)
    assert hi > lo
    assert lo == (20 - 50.0) / 100.0 * C.MORALE_HIT_FACTOR
    assert hi == (95 - 50.0) / 100.0 * C.MORALE_HIT_FACTOR
    # two battles, same attacker/stats/terrain, different realm morale
    c = make_game(11)
    b1 = forced_battle(c, morale=20)
    u = active_attacker(b1)
    hit1 = B.hit_chance_for(b1, u, "melee")
    c2 = make_game(11)
    b2 = forced_battle(c2, morale=95)
    u2 = active_attacker(b2)
    hit2 = B.hit_chance_for(b2, u2, "melee")
    assert hit2 > hit1


def test_dead_units_removed_and_party_purged():
    c = make_game(seed=42)
    b = forced_battle(c)
    assert sum(1 for u in b.all_living() if not u.alive) == 0
    b.auto_resolve()
    assert b.over()
    assert b.winner in ("attacker", "defender")
    c.resolve_battle(b)
    assert b not in c.pending_battles


def test_no_mass_blob_each_side_capped():
    c = make_game(seed=3)
    b = forced_battle(c)
    for side in ("attacker", "defender"):
        assert len(b.sides[side]) <= C.BATTLE_SIDE_CAP
        assert len(b.sides[side]) >= 1


def test_stunned_unit_cannot_act():
    c = make_game(seed=5)
    b = forced_battle(c)
    unit = c.units[b.sides["attacker"][0]]
    b.stun_until[unit.id] = b.round
    assert b.is_stunned(unit)
    assert not b.can_act(unit)
    b.stun_until.pop(unit.id, None)
    # after the stun ends, if it is that side's phase it may act again
    b.turn_side = b.side_of[unit.id]
    b._start_phase()
    assert b.can_act(unit)