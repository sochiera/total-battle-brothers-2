from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules.settlements import Building


def test_staffing_food_market_and_closing_returns_population():
    campaign = Campaign(7)
    realm, sid = campaign.player, campaign.player.settlement_ids[0]
    holding = campaign.settlements[sid]
    realm.gold = realm.wheat = 1000
    realm.population = 30
    for kind in (C.BUILDING_FARM, C.BUILDING_GRANARY, C.BUILDING_MARKET):
        holding.buildings[kind] = Building(kind)
    assert not holding.has(C.BUILDING_FARM)
    campaign.staff_building(sid, C.BUILDING_FARM)
    campaign.staff_building(sid, C.BUILDING_GRANARY)
    holding.size = C.SIZE_T
    campaign.staff_building(sid, C.BUILDING_MARKET)
    wheat, gold = realm.wheat, realm.gold
    assert campaign.convert_market(sid, "sell")
    assert (realm.wheat, realm.gold) == (wheat - C.MARKET_SELL_WHEAT,
                                          gold + C.MARKET_SELL_GOLD)
    population = realm.population
    assert campaign.close_building(sid, C.BUILDING_FARM)
    assert realm.population == population + 1


def test_ai_uses_staffed_development_army_and_can_create_contacts():
    campaign = Campaign(734102)
    for realm in campaign.realms.values():
        realm.gold = realm.wheat = 400
        realm.population = 35
    campaign.end_turn()
    assert any(realm.orders or len(campaign.living_in_party(campaign.hero_party(realm.key))) > 1
               for realm in campaign.realms.values() if not realm.is_player)
