"""Headless individual-unit battle tests, including engine writeback."""
from tbb.rules import constants as C
from tbb.rules import battle as B
from tbb.rules.campaign import Campaign


def _battle(seed=21):
    campaign = Campaign(seed)
    return campaign, B.battle_from_contact(campaign,
                                            campaign.hero_party(0),
                                            campaign.hero_party(1))


def _adjacent(battle):
    attacker = battle.campaign.units[battle.sides["attacker"][0]]
    defender = battle.campaign.units[battle.sides["defender"][0]]
    battle.positions[defender.id] = (battle.positions[attacker.id][0] + 1,
                                     battle.positions[attacker.id][1])
    return attacker, defender


def test_battle_field_morale_changes_hit_only_and_ranged_has_range_gate():
    campaign, battle = _battle()
    attacker, defender = _adjacent(battle)
    campaign.realms[0].morale = 20
    low = battle.hit_chance(attacker, defender)
    campaign.realms[0].morale = 95
    high = battle.hit_chance(attacker, defender)
    assert high > low
    assert not battle.do_ranged(attacker, defender).ok
    assert all(not "rout" in entry.lower() for entry in battle.log)


def test_battle_engine_writes_wound_and_death_then_party_writeback():
    campaign, battle = _battle(22)
    attacker, defender = _adjacent(battle)
    battle.hit_chance = lambda *_args, **_kwargs: 1.0
    defender.max_hit_points = 20
    defender.current_hit_points = defender.max_hit_points
    result = battle.do_melee(attacker, defender)
    assert result.ok and result.hit and defender.wounds
    assert defender.alive
    # A second contact uses a fresh battle so its attacker turn is available.
    campaign2, battle2 = _battle(23)
    attacker2, defender2 = _adjacent(battle2)
    battle2.hit_chance = lambda *_args, **_kwargs: 1.0
    defender2.current_hit_points = 1
    killed = battle2.do_melee(attacker2, defender2)
    assert killed.hit and not defender2.alive and not battle2.alive[defender2.id]
    assert defender2.id in battle2.defender.unit_ids
    campaign2.resolve_battle(battle2)
    assert defender2.id not in battle2.defender.unit_ids


def test_battle_los_uses_hex_intermediate_cells_and_terrain_modifiers():
    campaign, battle = _battle(24)
    attacker, defender = _adjacent(battle)
    bow = next((u for u in campaign.units.values() if u.realm == 0 and
                C.KITS[u.kit]["bow"]), None)
    if bow is not None:
        battle.positions[bow.id] = (2, 2)
        defender_id = battle.sides["defender"][0]
        battle.positions[defender_id] = (4, 3)
        campaign.world.set_terrain((3, 2), C.TERRAIN_FOREST)
        assert not battle._line_clear((2, 2), (4, 3))
