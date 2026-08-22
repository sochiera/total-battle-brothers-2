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


def test_ai_month_has_priority_order_and_non_player_path_target():
    campaign = Campaign(734102)
    for realm in campaign.realms.values():
        realm.gold = realm.wheat = 600
        realm.population = 50
    campaign.end_turn()
    rivals = [realm for realm in campaign.realms.values() if not realm.is_player]
    assert all(realm.ai_target is not None for realm in rivals)
    assert any(order.kind in {"build", "recruit", "train", "gear"}
               for realm in rivals for order in realm.orders)
    assert any(campaign.settlements[realm.ai_target].owner != realm.key
               for realm in rivals)


def test_fractional_births_and_immigration_carry_between_months():
    campaign = Campaign(15)
    realm = campaign.player
    realm.population = 18
    realm.population_fraction = 0.0
    realm.wheat = 1000
    realm.morale = 70
    starting = realm.population
    campaign._account(realm)
    assert realm.population_fraction > 0
    campaign._account(realm)
    assert realm.population >= starting
