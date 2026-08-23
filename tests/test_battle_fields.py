"""Battle field generation, side-based turns, the scripted foe, and
outcome writeback (wounds, deaths, stun, capture)."""
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


# ------------------------------------------------------------- field shape
def test_field_is_18x13_and_themed_by_contact_terrain():
    sparse = {C.TERRAIN_RIVER, C.TERRAIN_MOUNTAIN}
    for terrain in C.CAMPAIGN_TERRAINS:
        field = B.generate_field(terrain)
        assert len(field) == C.BATTLE_WIDTH * C.BATTLE_HEIGHT
        assert all(0 <= q < C.BATTLE_WIDTH and 0 <= r < C.BATTLE_HEIGHT
                   for (q, r) in field)
        count = sum(1 for t in field.values() if t == terrain)
        if terrain in sparse:
            # clearly themed: a visible water band / rock spine
            assert count >= C.BATTLE_HEIGHT * 2
        else:
            others = len(field) - count
            assert count > others // 3
    forest = B.generate_field(C.TERRAIN_FOREST)
    plains_field = B.generate_field(C.TERRAIN_PLAINS)
    assert sum(t == C.TERRAIN_FOREST for t in forest.values()) > \
        sum(t == C.TERRAIN_FOREST for t in plains_field.values())


def test_river_and_mountain_fields_keep_deployment_columns_walkable():
    for terrain in (C.TERRAIN_RIVER, C.TERRAIN_MOUNTAIN, C.TERRAIN_MARSH,
                    C.TERRAIN_COAST):
        field = B.generate_field(terrain)
        for r in range(C.BATTLE_HEIGHT):
            for q in list(range(0, 5)) + list(range(C.BATTLE_WIDTH - 5,
                                                   C.BATTLE_WIDTH)):
                assert field[(q, r)] not in C.BATTLE_IMPASSABLE_TERRAIN
    river = B.generate_field(C.TERRAIN_RIVER)
    assert any(t == C.TERRAIN_RIVER for t in river.values())
    mountain = B.generate_field(C.TERRAIN_MOUNTAIN)
    assert any(t == C.TERRAIN_MOUNTAIN for t in mountain.values())


def test_field_generation_varies_with_rng_state():
    from tbb.rules.rng import RNG
    first = B.generate_field(C.TERRAIN_FOREST, RNG(500))
    second = B.generate_field(C.TERRAIN_FOREST, RNG(501))
    third = B.generate_field(C.TERRAIN_FOREST, RNG(500))
    assert first != second
    assert first == third


def test_field_paints_from_campaign_neighbours_and_rng():
    campaign = Campaign(734102)
    hero = campaign.hero_party(0)
    field = B.battle_from_contact(campaign, hero,
                                  campaign.hero_party(1))
    assert field is not None
    assert len(field.canvas) == C.BATTLE_WIDTH * C.BATTLE_HEIGHT


# ---------------------------------------------------------- side-based flow
def test_several_player_actions_before_the_foe_acts():
    campaign, battle = _battle(61)
    human = battle.human_side()
    assert battle.turn_side == human
    first = battle.campaign.units[battle.sides[human][0]]
    moves = battle.available_moves(first)
    assert battle.move(first, moves[0]).ok
    # still our side: act with a second warrior
    second_id = battle.sides[human][1]
    second = battle.campaign.units[second_id]
    second_moves = battle.available_moves(second)
    assert battle.move(second, second_moves[0]).ok
    assert battle.turn_side == human
    assert battle.ap[first.id] == 1 and battle.ap[second.id] == 1
    # End Turn hands the fight to the scripted foe and back again
    result = battle.end_player_turn()
    assert result.ok
    assert battle.turn_side == human
    assert battle.round == 2
    assert battle.ap[first.id] == 2


def test_scripted_foe_uses_shared_rules_and_records_actions():
    campaign, battle = _battle(62)
    human = battle.human_side()
    foe_side = "defender" if human == "attacker" else "attacker"
    battle.turn_side = foe_side
    records = battle.scripted_turn()
    assert battle.turn_side == human
    if not battle.over():
        assert records
        allowed = {"melee", "ranged", "move"}
        assert all(record["kind"] in allowed for record in records)
        for record in records:
            if record["kind"] in ("melee", "ranged"):
                damage = record["damage"]
                assert damage >= 0


def test_stunned_warrior_is_skipped_by_the_foe():
    campaign, battle = _battle(63)
    foe_side = "defender" if battle.human_side() == "attacker" else "attacker"
    stunned = battle.sides[foe_side][0]
    battle.stun_until[stunned] = battle.round + 1
    battle.turn_side = foe_side
    battle.scripted_turn()
    assert battle.ap[stunned] == 2  # never acted


def test_auto_resolve_ends_the_fight_and_writes_back():
    campaign, battle = _battle(64)
    battle.auto_resolve()
    assert battle.over()
    campaign.resolve_battle(battle)
    assert battle not in campaign.pending_battles


# ----------------------------------------------------------------- outcomes
def test_forced_hit_wounds_without_killing_and_lethal_hit_writes_back():
    campaign, battle = _battle(65)
    attacker, defender = _adjacent(battle)
    battle.hit_chance = lambda *_a, **_k: 1.0
    defender.max_hit_points = 20
    defender.current_hit_points = 20
    result = battle.do_melee(attacker, defender)
    assert result.ok and result.hit and defender.wounds and defender.alive
    # same fight, next kill
    while defender.alive:
        battle.ap[attacker.id] = 1
        battle.do_melee(attacker, defender)
    assert not defender.alive
    assert defender.id in battle.defender.unit_ids
    campaign.resolve_battle(battle)
    assert defender.id not in battle.defender.unit_ids
    assert not campaign.units[defender.id].alive


def test_wounds_carry_temporary_month_counters():
    campaign, battle = _battle(66)
    attacker, defender = _adjacent(battle)
    battle.hit_chance = lambda *_a, **_k: 1.0
    defender.max_hit_points = 20
    defender.current_hit_points = 20
    battle.do_melee(attacker, defender)
    assert defender.wounds
    for wound in defender.wounds:
        kind = C.WOUNDS[defender.wound_name(wound)]
        if kind == "temporary":
            assert defender.wound_months(wound) == C.TEMP_WOUND_MONTHS
        else:
            assert defender.wound_months(wound) is None


def test_morale_only_changes_hit_chance_never_forces_flight():
    campaign, battle = _battle(67)
    attacker, defender = _adjacent(battle)
    campaign.realms[0].morale = 10
    low = battle.hit_chance(attacker, defender)
    campaign.realms[0].morale = 95
    high = battle.hit_chance(attacker, defender)
    assert high > low
    # low morale never removes control: the warrior may still act
    assert battle.can_act(attacker)


def test_assault_victory_transfers_the_holding():
    campaign = Campaign(68)
    hero = campaign.hero_party(campaign.player.key)
    target_realm = campaign.realms[1]
    sid = target_realm.settlement_ids[0]
    guard = campaign.garrison_party(sid)
    for uid in list(guard.unit_ids):
        guard.remove(uid)
    # give the defender one soldier so a battle happens
    unit = campaign._make_unit(1, campaign.settlements[sid].name)
    campaign.realms[1].unit_ids.add(unit.id)
    guard.add(unit.id)
    hero.move_to(campaign.settlements[sid].hex)
    battle = campaign._make_battle(hero, guard, True)
    assert battle is not None and battle.assault
    battle.winner = "attacker"
    campaign.resolve_battle(battle)
    assert campaign.settlements[sid].owner == campaign.player.key
    assert sid in campaign.player.settlement_ids
    assert sid not in target_realm.settlement_ids


def test_walking_into_an_undefended_holding_takes_it():
    campaign = Campaign(69)
    hero = campaign.hero_party(campaign.player.key)
    neutral = next(h for h in campaign.settlements.values()
                   if h.owner is None)
    guard = campaign.garrison_party(neutral.id)
    for uid in list(guard.unit_ids):
        guard.remove(uid)
    neighbour = campaign.world.neighbours(neutral.hex)[0]
    campaign.world.set_terrain(neighbour, C.TERRAIN_PLAINS)
    hero.move_to(neighbour)
    hero.mp = C.CAMPAIGN_MOVEMENT_POINTS
    result = campaign.move_party(hero.pid, neutral.hex)
    assert result.ok
    assert neutral.owner == campaign.player.key
