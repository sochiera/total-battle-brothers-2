import re
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules import persistence
from tbb.rules import worldgen
from tbb.rules.rng import RNG
from tbb.rules.campaign import Check as CampaignCheck
from tbb.rules.economy import Check as EconomyCheck


def test_transfer_requires_two_distinct_holdings_and_source_market():
    campaign = Campaign(13)
    sid = campaign.player.settlement_ids[0]
    holding = campaign.settlements[sid]
    same = campaign.transfer_goods(sid, sid, "wheat", dry_run=True)
    assert not same.ok
    assert "other" in same.reason or "different" in same.reason

    other = next((h for h in campaign.settlements.values()
                  if h.owner == campaign.player.key and h.id != sid), None)
    assert other is not None
    holding.buildings.pop(C.BUILDING_MARKET, None)
    missing = campaign.transfer_goods(sid, other.id, "wheat", dry_run=True)
    assert not missing.ok
    assert "market" in missing.reason


def test_is_heir_marker_is_used_by_succession_when_realm_pointer_is_missing():
    campaign = Campaign(734102)
    old_hero = campaign.player.hero
    heir = campaign.current_heir()
    campaign.player.heir = None
    assert campaign.current_heir_id() == heir.id
    campaign.units[old_hero].alive = False
    campaign._ensure_succession(campaign.player)
    assert campaign.player.hero == heir.id


def test_campaign_and_economy_use_one_check_type():
    assert CampaignCheck is EconomyCheck


def test_battle_constructor_accepts_public_battle_kind_alias():
    from tbb.rules.battle import Battle
    campaign = Campaign(734102)
    battle = Battle(campaign, campaign.hero_party(0),
                    next(p for p in campaign.parties if p.kind == "bandit"),
                    battle_kind="raid")
    assert battle.contact_kind == battle.battle_kind == "raid"


def test_player_cannot_raid_own_holding_but_neutral_can_be_sacked():
    campaign = Campaign(734102)
    own = campaign.settlements[campaign.player.settlement_ids[0]]
    assert not campaign.raid_settlement(own.id)
    neutral = next(h for h in campaign.settlements.values() if h.owner is None)
    neutral.wheat, neutral.gold, neutral.population = 20, 20, 12
    before = (neutral.wheat, neutral.gold, neutral.population)
    result = campaign.raid_settlement(neutral.id)
    assert result.ok
    assert neutral.owner is None
    assert neutral.wheat < before[0]
    assert neutral.gold < before[1]
    assert neutral.population < before[2]


def test_world_names_are_globally_unique_without_numeric_collision_suffixes():
    data = worldgen.generate(RNG(7))
    names = ([h.name for h in data["settlements"].values()] +
             [realm.name for realm in data["realms"].values()] +
             list(data["world"].regions) + list(data["world"].rivers))
    assert len(names) == len(set(names))
    assert not any(re.search(r"\d$", name) for name in names)


def test_mid_battle_save_can_continue_after_restore(tmp_path):
    campaign = Campaign(734102)
    from tbb.rules.battle import battle_from_contact
    hero = campaign.hero_party(C.PLAYER_REALM_KEY)
    bandit = next(p for p in campaign.parties if p.kind == "bandit")
    battle = battle_from_contact(campaign, hero, bandit)
    campaign.pending_battles.append(battle)
    attacker = campaign.units[battle.sides["attacker"][0]]
    target = campaign.units[battle.sides["defender"][0]]
    target.apply_wound("gash")
    target.current_hit_points = target.max_hit_points - 3
    battle.ap[attacker.id] = 1
    battle.stun_until[target.id] = 4
    battle.positions[attacker.id] = (2, 2)
    persistence.save(campaign, "mid-batch2", tmp_path)
    restored = persistence.load("mid-batch2", tmp_path)
    loaded = restored.pending_battles[0]
    assert loaded.canvas == battle.canvas
    assert loaded.positions == battle.positions
    assert loaded.ap == battle.ap
    assert loaded.stun_until == battle.stun_until
    assert restored.units[target.id].wounds == target.wounds
    assert restored.units[target.id].current_hit_points == target.current_hit_points
    assert restored.units[target.id].max_hit_points == target.max_hit_points
    battle.battle_kind = "raid"
    persistence.save(campaign, "mid-batch2-kind", tmp_path)
    restored_kind = persistence.load("mid-batch2-kind", tmp_path)
    assert restored_kind.pending_battles[0].contact_kind == "raid"
    assert restored_kind.pending_battles[0].battle_kind == "raid"
    assert restored.calendar == campaign.calendar
    assert restored.rng.getstate() == campaign.rng.getstate()
    loaded_attacker = restored.units[attacker.id]
    assert loaded.do_move(loaded_attacker,
                          next(iter(loaded.available_moves(loaded_attacker))))
