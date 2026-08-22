from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules.settlements import Building


def test_worker_floor_is_proved_with_a_staffed_building():
    campaign = Campaign(8)
    realm, sid = campaign.player, campaign.player.settlement_ids[0]
    holding = campaign.settlements[sid]
    party = campaign.hero_party(realm.key)
    party.move_to(holding.hex)
    realm.gold = realm.wheat = 100
    holding.buildings[C.BUILDING_FARM] = Building(C.BUILDING_FARM, staffed=True)
    realm.population = realm.staff_total(campaign.settlements) + 1
    before = len(party.unit_ids)
    target = next(n for n in campaign.world.neighbours(holding.hex)
                  if campaign.settlement_at(n) is None)
    campaign.world.set_terrain(target, C.TERRAIN_PLAINS)
    assert not campaign.order_found(target)
    assert not campaign.recruit_to_company(sid)
    assert "idle resident" in campaign.recruit_to_company(sid).reason
    campaign.unstaff_building(sid, C.BUILDING_FARM)
    assert campaign.recruit_to_company(sid)
    assert len(party.unit_ids) == before
    campaign.end_turn()
    assert len(party.unit_ids) == before + 1


def test_company_cap_and_matching_supply_gates():
    campaign = Campaign(9)
    realm, sid = campaign.player, campaign.player.settlement_ids[0]
    holding, party = campaign.settlements[sid], campaign.hero_party(realm.key)
    party.move_to(holding.hex)
    realm.gold = realm.wheat = 1000
    realm.population = 60
    holding.size = C.SIZE_T
    holding.buildings[C.BUILDING_SMITHY] = Building(C.BUILDING_SMITHY, staffed=True)
    unit = next(uid for uid in party.unit_ids if uid != realm.hero)
    assert campaign.order_gear(unit, "heavy")
    assert not campaign.order_gear(unit, "bow")
    for _ in range(C.COMPANY_CAP - len(party.unit_ids)):
        assert campaign.recruit_to_company(sid)
    assert not campaign.recruit_to_company(sid)
    assert len(party.unit_ids) <= C.COMPANY_CAP


def test_build_develop_and_found_constraints():
    campaign = Campaign(10)
    realm, sid = campaign.player, campaign.player.settlement_ids[0]
    holding = campaign.settlements[sid]
    realm.gold = realm.wheat = 1000
    realm.population = 30
    if holding.size == C.SIZE_V:
        assert not campaign.order_build(sid, C.BUILDING_MARKET)
    target = next(n for n in campaign.world.neighbours(holding.hex)
                  if campaign.settlement_at(n) is None)
    campaign.world.set_terrain(target, C.TERRAIN_FOREST)
    assert not campaign.order_found(target)
