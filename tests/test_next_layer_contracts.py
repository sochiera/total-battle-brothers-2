"""Headless contracts for the larger kingdom sandbox layer."""
from tbb.rules import constants as C
from tbb.rules import terrain as G
from tbb.rules.battle import generate_field, battle_from_contact
from tbb.rules.campaign import Campaign
from tbb.rules.rng import RNG
from tbb.rules.worldgen import generate
from tbb.rules.settlements import Building


def _largest(world):
    best = set()
    visited = set()
    for start in world.grid:
        if start in visited or not world.is_passable(start):
            continue
        seen, todo = {start}, [start]
        visited.add(start)
        while todo:
            pos = todo.pop()
            for nxt in world.walkable_neighbours(pos):
                if nxt not in seen:
                    seen.add(nxt); visited.add(nxt); todo.append(nxt)
        best = max(best, seen, key=len)
    return best


def test_forty_seed_worlds_keep_seats_in_one_named_region():
    seen_sizes = set()
    player_city_start = False
    for seed in range(40):
        data = generate(RNG(seed))
        world = data["world"]
        region = _largest(world)
        assert len(region) > world.width * world.height // 2
        assert all(data["settlements"][sid].hex in region
                   for realm in data["realms"].values()
                   for sid in realm.settlement_ids)
        names = ([h.name for h in data["settlements"].values()] +
                 [r.name for r in data["realms"].values()] +
                 list(world.regions) + list(world.rivers))
        assert len(names) == len(set(names))
        assert not any(name.rsplit(" ", 1)[-1].isdigit() for name in names)
        seen_sizes.update(h.size for h in data["settlements"].values())
        player_city_start |= any(
            data["settlements"][sid].size == C.SIZE_C
            for sid in data["realms"][C.PLAYER_REALM_KEY].settlement_ids)
    assert {C.SIZE_V, C.SIZE_T, C.SIZE_C} <= seen_sizes
    assert player_city_start


def test_calendar_seasons_change_farm_output_and_march_points():
    c = Campaign(734102)
    holding = c.settlements[c.player.settlement_ids[0]]
    holding.buildings[C.BUILDING_FARM] = Building(C.BUILDING_FARM, True)
    assert holding.farm_output(30, C.SEASON_HARVEST) > holding.farm_output(30, C.SEASON_WINTER)
    c.calendar.month = 0
    winter = c._fresh_mp(c.hero_party(0))
    c.calendar.month = 7
    harvest = c._fresh_mp(c.hero_party(0))
    assert winter < harvest


def test_default_heir_and_structured_wounds_survive_expiry():
    c = Campaign(734102)
    assert c.player.heir and c.units[c.player.heir].alive
    unit = c.units[c.player.hero]
    unit.apply_wound("gash")
    assert unit.wounds[0] == {"wound": "gash", "months": C.TEMP_WOUND_MONTHS}
    for _ in range(C.TEMP_WOUND_MONTHS):
        unit.heal_month()
    assert not unit.wounds


def test_staffed_market_moves_local_goods_and_raid_does_not_annex():
    c = None
    source = target = None
    for seed in range(40):
        candidate = Campaign(seed)
        own = [candidate.settlements[sid]
               for sid in candidate.player.settlement_ids]
        pair = next(((a, b) for a in own for b in own
                     if a is not b and a.has(C.BUILDING_MARKET) and
                     G.hex_distance(a.hex, b.hex) <=
                     C.MARKET_TRANSFER_RANGE and
                     G.hex_distance(a.hex, b.hex) > 0), None)
        if pair:
            c, (source, target) = candidate, pair
            break
    assert c and source and target
    own = [c.settlements[sid] for sid in c.player.settlement_ids]
    assert G.hex_distance(source.hex, target.hex) > 0
    source.wheat = C.MARKET_TRANSFER_WHEAT + 2
    before = target.wheat
    assert c.transfer_goods(source.id, target.id, "wheat")
    assert source.wheat == 2 and target.wheat == before + C.MARKET_TRANSFER_WHEAT
    rival = next(h for h in c.settlements.values()
                 if h.owner not in (None, c.player.key))
    rival.gold = 20; rival.wheat = 20
    owner = rival.owner
    population = rival.population
    assert c.raid_settlement(rival.id)
    assert rival.owner == owner
    assert rival.wheat < 20 and rival.gold < 20 and rival.population < population


def test_large_battle_field_has_walkable_deployment_and_reachable_edges():
    c = Campaign(734102)
    battle = battle_from_contact(c, c.hero_party(0), c.hero_party(1))
    assert len(battle.canvas) == C.BATTLE_WIDTH * C.BATTLE_HEIGHT
    for theme in (C.TERRAIN_FOREST, C.TERRAIN_HILLS, C.TERRAIN_RIVER,
                  C.TERRAIN_FARMLAND, C.TERRAIN_MOUNTAIN):
        field = generate_field(theme, RNG(theme))
        assert all(field[(q, r)] not in C.BATTLE_IMPASSABLE_TERRAIN
                   for r in range(C.BATTLE_HEIGHT)
                   for q in list(range(5)) + list(range(C.BATTLE_WIDTH - 5, C.BATTLE_WIDTH)))
        assert field[(2, C.BATTLE_HEIGHT // 2)] not in C.BATTLE_IMPASSABLE_TERRAIN


def test_endings_and_succession_are_reachable_without_ui():
    c = Campaign(77)
    old = c.player.hero
    c.units[old].alive = False
    c.end_turn()
    assert c.player.hero != old and c.units[c.player.hero].is_hero
    defeat = Campaign(78)
    defeat.player.settlement_ids = []
    defeat.player.heir = None
    defeat.units[defeat.player.hero].alive = False
    defeat.check_end_conditions()
    assert defeat.ended and defeat.end_reason == "defeat"
    victory = Campaign(79)
    for realm in victory.realms.values():
        if realm.key != victory.player.key:
            realm.settlement_ids = []
    victory.check_end_conditions()
    assert victory.ended and victory.end_reason == "victory"
