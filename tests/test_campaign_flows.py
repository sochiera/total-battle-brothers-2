"""Wound expiry, founding, AI expansion, garrison transfer, and save
roundtrips covering the new mechanics, all without a display."""
import ast
from pathlib import Path

from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules import persistence


def _fresh_campaign(seed=71):
    campaign = Campaign(seed)
    campaign.notes = []
    return campaign


# ------------------------------------------------------------ wound expiry
def test_temporary_wound_mends_after_three_months_permanent_never():
    campaign = _fresh_campaign()
    realm = campaign.player
    uid = realm.hero
    unit = campaign.units[uid]
    melee_before = unit.stat("melee")
    ranged_before = unit.stat("ranged")
    unit.apply_wound("gash")
    unit.apply_wound("lost eye")
    assert all(isinstance(wound, dict) and "wound" in wound
               and "months" in wound for wound in unit.wounds)
    assert unit.stat("melee") < melee_before
    campaign._ai_and_bandit_turn = lambda: None
    for _ in range(C.TEMP_WOUND_MONTHS):
        assert campaign.end_turn().ok
    names = [unit.wound_name(w) for w in unit.wounds]
    assert "gash" not in names
    assert "lost eye" in names
    assert unit.stat("melee") == melee_before
    assert unit.stat("ranged") == ranged_before + \
        C.WOUND_STAT_EFFECT["lost eye"]["ranged"]


def test_save_preserves_remaining_wound_months():
    campaign = _fresh_campaign()
    unit = campaign.units[campaign.player.hero]
    unit.apply_wound("bruise", months=2)
    path = persistence.save(campaign, "wounds", "/tmp/tbb-tests")
    loaded = persistence.load("wounds", "/tmp/tbb-tests")
    assert persistence.canonical(campaign) == persistence.canonical(loaded)
    healed = loaded.units[loaded.player.hero]
    assert [healed.wound_months(w) for w in healed.wounds] == [2]


# -------------------------------------------------------- founding villages
def test_founding_rejects_bad_ground_and_pays_on_success():
    campaign = _fresh_campaign()
    realm = campaign.player
    sid = realm.settlement_ids[0]
    holding = campaign.settlements[sid]
    realm.gold = realm.wheat = 500
    realm.population = 40
    target = next(n for n in campaign.world.neighbours(holding.hex)
                  if campaign.settlement_at(n) is None)
    for terrain in (C.TERRAIN_FOREST, C.TERRAIN_MARSH, C.TERRAIN_COAST,
                    C.TERRAIN_MOUNTAIN, C.TERRAIN_HILLS):
        campaign.world.set_terrain(target, terrain)
        assert not campaign.order_found(target)
    campaign.world.set_terrain(target, C.TERRAIN_FARMLAND)
    gold, wheat, pop = realm.gold, realm.wheat, realm.population
    assert campaign.order_found(target)
    assert realm.gold == gold - C.FOUND_COST["gold"]
    assert realm.wheat == wheat - C.FOUND_COST["wheat"]
    assert realm.population == pop - C.FOUND_COST["settlers"]


def test_found_order_completes_into_a_named_village_with_garrison():
    campaign = _fresh_campaign()
    realm = campaign.player
    sid = realm.settlement_ids[0]
    holding = campaign.settlements[sid]
    realm.gold = realm.wheat = 500
    realm.population = 40
    target = next(n for n in campaign.world.neighbours(holding.hex)
                  if campaign.settlement_at(n) is None)
    campaign.world.set_terrain(target, C.TERRAIN_PLAINS)
    assert campaign.order_found(target)
    campaign._ai_and_bandit_turn = lambda: None
    for _ in range(C.FOUND_COST["months"]):
        assert campaign.end_turn().ok
    village = campaign.settlement_at(target)
    assert village is not None
    assert village.size == C.SIZE_V
    assert village.owner == realm.key
    assert village.name
    assert campaign.world.terrain(target) == C.TERRAIN_VILLAGE
    garrison = campaign.garrison_party(village.id)
    assert garrison is not None and garrison.hex == target


# ------------------------------------------------------------- AI expansion
def test_rich_ai_founds_and_targets_external_land():
    campaign = Campaign(734102)
    for realm in campaign.realms.values():
        if not realm.is_player:
            realm.gold = realm.wheat = 900
            realm.population = 60
    assert campaign.end_turn().ok
    rivals = [r for r in campaign.realms.values() if not r.is_player]
    assert any(order.kind == "found" for r in rivals for order in r.orders)
    assert any(r.ai_target is not None and
               campaign.settlements[r.ai_target].owner != r.key
               for r in rivals)


def test_rival_that_can_afford_it_founds_next_to_own_land():
    campaign = Campaign(72)
    realm = campaign.realms[1]
    realm.gold = realm.wheat = 800
    realm.population = 60
    from tbb.rules import ai
    ai._found(campaign, realm)
    found = [o for o in realm.orders if o.kind == "found"]
    assert found
    spot = found[0].kind_data
    assert campaign.settlement_at(spot) is None
    assert campaign.world.terrain(spot) in (C.TERRAIN_PLAINS,
                                            C.TERRAIN_RUINS,
                                            C.TERRAIN_FARMLAND)
    assert any(spot in campaign.world.neighbours(
        campaign.settlements[s].hex) for s in realm.settlement_ids)
    assert realm.gold == 800 - C.FOUND_COST["gold"]


# -------------------------------------------------------- garrison transfer
def test_attach_detach_dry_run_reasons_match_the_rules():
    campaign = Campaign(73)
    realm = campaign.player
    sid = realm.settlement_ids[0]
    holding = campaign.settlements[sid]
    hero_party = campaign.hero_party(realm.key)
    garrison = campaign.garrison_party(sid)
    soldier = next(uid for uid in garrison.unit_ids
                   if campaign.units[uid].alive)
    # hero away: both transfers refused
    if hero_party.hex != holding.hex:
        assert not campaign.attach_to_hero(sid, soldier)
        assert not campaign.detach_to_garrison(sid, realm.hero)
    # hero arrives: attach works up to the company cap
    hero_party.move_to(holding.hex)
    before = len(hero_party.unit_ids)
    assert campaign.attach_to_hero(sid, soldier)
    assert soldier in hero_party.unit_ids
    assert soldier not in garrison.unit_ids
    assert len(hero_party.unit_ids) == before + 1
    # the hero himself never garrisons
    assert not campaign.detach_to_garrison(sid, realm.hero)
    # detach returns the soldier
    assert campaign.detach_to_garrison(sid, soldier)
    assert soldier in garrison.unit_ids


def test_company_cap_is_enforced_on_attach():
    campaign = Campaign(74)
    realm = campaign.player
    sid = realm.settlement_ids[0]
    holding = campaign.settlements[sid]
    hero_party = campaign.hero_party(realm.key)
    garrison = campaign.garrison_party(sid)
    hero_party.move_to(holding.hex)
    guard_units = list(garrison.unit_ids)
    for uid in guard_units:
        campaign.attach_to_hero(sid, uid)
    while len(hero_party.unit_ids) < C.COMPANY_CAP:
        unit = campaign._make_unit(realm.key, holding.name)
        realm.unit_ids.add(unit.id)
        hero_party.add(unit.id)
    assert len(hero_party.unit_ids) == C.COMPANY_CAP
    extra = campaign._make_unit(realm.key, holding.name)
    realm.unit_ids.add(extra.id)
    garrison.add(extra.id)
    result = campaign.attach_to_hero(sid, extra.id)
    assert not result and "full" in result.reason


# ------------------------------------------------------------- save hybrids
def test_save_roundtrip_after_a_month_and_pending_battle():
    campaign = Campaign(75)
    campaign._ai_and_bandit_turn = lambda: None
    assert campaign.end_turn().ok
    party = campaign.hero_party(0)
    rival = campaign.hero_party(1)
    rival.move_to(campaign.world.neighbours(party.hex)[0])
    campaign.world.set_terrain(rival.hex, C.TERRAIN_PLAINS)
    battle = campaign._make_battle(party, rival)
    assert battle is not None
    uid = battle.sides["attacker"][0]
    battle.positions[uid] = (4, 7)
    battle.ap[uid] = 1
    battle.stun_until[uid] = battle.round + 2
    battle.round = 3
    calendar = campaign.calendar.snapshot()
    rng_state = campaign.rng.getstate()
    path = persistence.save(campaign, "midmonth", "/tmp/tbb-tests")
    loaded = persistence.load("midmonth", "/tmp/tbb-tests")
    assert persistence.canonical(campaign) == persistence.canonical(loaded)
    assert loaded.pending_battles
    # the loaded fight continues from the same canvas and side
    original = campaign.pending_battles[0]
    resumed = loaded.pending_battles[0]
    assert resumed.canvas == original.canvas
    assert resumed.turn_side == original.turn_side
    assert resumed.positions == original.positions
    assert resumed.ap == original.ap
    assert resumed.stun_until == original.stun_until
    assert resumed.round == original.round
    assert loaded.calendar.snapshot() == calendar
    assert loaded.rng.getstate() == rng_state


def test_unsupported_and_corrupt_saves_raise_readable_errors(tmp_path):
    campaign = Campaign(76)
    path = persistence.save(campaign, "bad", tmp_path)
    from pathlib import Path as P
    import json
    raw = json.loads(P(path).read_text())
    raw["version"] = 1
    P(path).write_text(json.dumps(raw))
    try:
        persistence.load("bad", tmp_path)
    except ValueError as error:
        assert "unsupported save version" in str(error)
    else:
        raise AssertionError("old save version was accepted")
    P(path).write_text("{not json at all")
    try:
        persistence.load("bad", tmp_path)
    except ValueError as error:
        assert "could not load slot" in str(error)
    else:
        raise AssertionError("corrupt save was accepted")


# ------------------------------------------------------------------- purity
def test_rules_source_never_imports_pygame():
    root = Path(__file__).resolve().parents[1] / "tbb" / "rules"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all("pygame" not in alias.name
                           for alias in node.names), path
            elif isinstance(node, ast.ImportFrom):
                assert "pygame" not in (node.module or ""), path
