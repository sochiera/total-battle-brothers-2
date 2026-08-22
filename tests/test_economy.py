"""Economy: monthly wheat/gold, upkeep, staffed vs unstaffed buildings,
granary/market/farm effects, population growth, starvation and unpaid
upkeep penalties - all deterministic under a seed."""
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules.settlements import Building


def new_campaign(seed=31):
    return Campaign(seed=seed)


def build_and_staff(c, sid, kind):
    h = c.settlements[sid]
    b = Building(kind)
    h.buildings[kind] = b
    realm = c._realm_of_settlement(sid)
    realm.population += 2
    ch = c.staff_building(sid, kind)
    assert ch.ok
    return b


def test_unstaffed_building_yields_nothing():
    c = new_campaign()
    realm = c.player
    sid = realm.settlement_ids[0]
    h = c.settlements[sid]
    h.buildings[C.BUILDING_FARM] = Building(C.BUILDING_FARM)
    h.buildings[C.BUILDING_MARKET] = Building(C.BUILDING_MARKET)
    assert realm.food_income(c.settlements) == 0
    assert realm.gold_income(c.settlements) == 0
    assert h.upkeep() == 0


def test_farm_granary_market_effects_when_staffed():
    c = new_campaign()
    realm = c.player
    sid = realm.settlement_ids[0]
    build_and_staff(c, sid, C.BUILDING_FARM)
    build_and_staff(c, sid, C.BUILDING_GRANARY)
    build_and_staff(c, sid, C.BUILDING_MARKET)
    assert realm.food_income(c.settlements) == C.FARM_FOOD + C.GRANARY_FOOD
    assert realm.gold_income(c.settlements) == C.MARKET_GOLD
    assert realm.building_upkeep(c.settlements) == \
        (C.BUILDINGS[C.BUILDING_FARM]["upkeep"] +
         C.BUILDINGS[C.BUILDING_GRANARY]["upkeep"] +
         C.BUILDINGS[C.BUILDING_MARKET]["upkeep"])


def test_staffing_consumes_population_and_closing_returns_it():
    c = new_campaign()
    realm = c.player
    sid = realm.settlement_ids[0]
    realm.population = 5
    build_and_staff(c, sid, C.BUILDING_MARKET)
    assert realm.population == 6  # +2 seed people, then staff took 1
    # another staff still consumes one more
    realm.population += 1
    ch = c.staff_building(sid, C.BUILDING_MARKET)  # already staffed
    assert not ch.ok
    assert realm.population == 7
    # close it - 1 population returns to the pool
    ch = c.unstaff_building(sid, C.BUILDING_MARKET)
    assert ch.ok
    assert realm.population == 8
    assert realm.gold_income(c.settlements) == 0


def test_starvation_reduces_morale_and_population():
    c = new_campaign()
    r = c.player
    r.wheat = 0.0
    r.gold = 1000.0
    r.population = 40
    morale_before = r.morale
    pop_before = r.population
    c._resolve_realm_month(r)
    assert r.wheat == 0
    assert r.morale < morale_before
    assert r.population < pop_before


def test_unpaid_upkeep_drops_morale():
    c = new_campaign()
    r = c.player
    r.gold = 0.0
    r.wheat = 500
    r.population = 5
    m = r.morale
    c._resolve_realm_month(r)
    assert r.gold == 0
    assert r.morale <= m


def test_population_grows_toward_cap_under_surplus():
    c = new_campaign()
    r = c.player
    r.wheat = 500
    r.morale = 100
    cap = r.holdings_cap(c.settlements)
    start = r.population
    assert cap >= start
    c._resolve_realm_month(r)
    assert start < r.population <= cap


def test_orders_advance_a_whole_month_per_turn():
    c = new_campaign()
    realm = c.player
    realm.gold = 1000
    realm.wheat = 1000
    sid = realm.settlement_ids[0]
    ch = c.order_build(sid, C.BUILDING_FARM)
    assert ch.ok
    assert realm.orders and realm.orders[0].months == C.BUILDINGS[
        C.BUILDING_FARM]["months"]
    c._advance_orders(realm)
    h = c.settlements[sid]
    assert C.BUILDING_FARM not in h.buildings  # months remain
    c._advance_orders(realm)
    assert C.BUILDING_FARM in h.buildings