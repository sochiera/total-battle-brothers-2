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


def test_battle_grid_morale_ranges_wound_and_death():
    wound_campaign, wound_battle = _battle(240)
    wound_attacker, wounded = _adjacent(wound_battle)
    wound_battle.hit_chance = lambda *_args, **_kwargs: 1.0
    wounded.max_hit_points = 20
    wounded.current_hit_points = wounded.max_hit_points
    wounds_before = len(wounded.wounds)
    wound = wound_battle.do_melee(wound_attacker, wounded)
    assert wound.hit and len(wounded.wounds) > wounds_before
    assert wounded.alive

    death_campaign, death_battle = _battle(241)
    death_attacker, near_dead = _adjacent(death_battle)
    death_battle.hit_chance = lambda *_args, **_kwargs: 1.0
    near_dead.current_hit_points = 1
    killed = death_battle.do_melee(death_attacker, near_dead)
    assert killed.hit and near_dead.alive is False
    assert near_dead.alive is False
    assert near_dead.id in death_battle.defender.unit_ids
    death_campaign.resolve_battle(death_battle)
    assert near_dead.id not in death_battle.defender.unit_ids

    campaign, battle = _battle(24)
    attacker, defender = _adjacent(battle)
    attacker.kit = "bow"
    battle.positions[attacker.id] = (2, 2)
    battle.positions[defender.id] = (4, 2)
    battle.canvas[(3, 2)] = C.TERRAIN_FOREST
    assert not battle._line_clear((2, 2), (4, 2))
    assert not battle.do_ranged(attacker, defender).ok

    clear_campaign, clear_battle = _battle(25)
    bowman, target = _adjacent(clear_battle)
    bowman.kit = "bow"
    clear_battle.positions[bowman.id] = (2, 2)
    clear_battle.positions[target.id] = (4, 2)
    clear_battle.canvas[(3, 2)] = C.TERRAIN_PLAINS
    clear_battle.hit_chance = lambda *_args, **_kwargs: 1.0
    result = clear_battle.do_ranged(bowman, target)
    assert result.ok and result.hit
    assert clear_battle.ranged_in_range(bowman, target)

    near_campaign, near_battle = _battle(26)
    near_attacker, near_target = _adjacent(near_battle)
    near_battle.positions[near_attacker.id] = (2, 2)
    near_battle.positions[near_target.id] = (3, 2)
    assert not near_battle.ranged_in_range(near_attacker, near_target)
    near_battle.positions[near_target.id] = (6, 2)
    assert not near_battle.ranged_in_range(near_attacker, near_target)


def test_battle_los_uses_hex_intermediate_cells_and_terrain_modifiers():
    campaign, battle = _battle(24)
    attacker, defender = _adjacent(battle)
    bow = campaign.units[battle.sides["attacker"][0]]
    bow.kit = "bow"
    battle.positions[bow.id] = (2, 2)
    defender_id = battle.sides["defender"][0]
    battle.positions[defender_id] = (4, 3)
    battle.canvas[(3, 2)] = C.TERRAIN_FOREST
    assert not battle._line_clear((2, 2), (4, 3))


def test_river_field_keeps_deployment_columns_clear():
    field = B.generate_field(C.TERRAIN_RIVER)
    attacker = {q for (q, _r) in field if q in range(1, 4)}
    defender = {q for (q, _r) in field if q in range(C.BATTLE_WIDTH - 4,
                                                       C.BATTLE_WIDTH - 1)}
    assert all(field[(q, r)] != C.TERRAIN_RIVER
               for q in attacker | defender
               for r in range(C.BATTLE_HEIGHT))
    assert any(value == C.TERRAIN_RIVER for value in field.values())
