from tbb.rules import constants as C
from tbb.rules.rng import RNG
from tbb.rules.worldgen import generate
from tbb.rules.campaign import Campaign
from tbb.rules import names


def test_world_is_large_varied_and_seeded():
    first, second = generate(RNG(2)), generate(RNG(3))
    assert first["world"].hex_count() == C.MAP_WIDTH * C.MAP_HEIGHT
    assert set(first["world"].grid.values()) == set(C.CAMPAIGN_TERRAINS)
    assert first["world"].crossings and first["world"].grid != second["world"].grid
    assert len(first["realms"]) == C.NUM_DUCHIES
    assert sum(p.kind == "bandit" for p in first["parties"]) == C.NUM_ROBBER_BANDS
    assert len([h for h in first["settlements"].values() if h.owner is None]) >= C.MIN_NEUTRALS


def test_start_archetypes_have_one_hero_and_company_cap():
    starts = []
    layouts = set()
    for seed in range(11, 111):
        campaign = Campaign(seed)
        starts.append(len(campaign.player.settlement_ids))
        layouts.add(tuple(campaign.settlements[sid].size
                          for sid in campaign.player.settlement_ids))
    assert 1 in starts and 2 in starts and 3 in starts
    assert (C.SIZE_V, C.SIZE_T) in layouts
    assert (C.SIZE_V, C.SIZE_T, C.SIZE_V) in layouts
    campaign = Campaign(734102)
    for realm in campaign.realms.values():
        party = campaign.hero_party(realm.key)
        assert realm.hero in party.unit_ids
        assert len(party.unit_ids) <= C.COMPANY_CAP
        assert sum(u.is_hero for u in realm.all_units(campaign.units)) == 1
        assert all(u.origin and 16 <= u.age <= 40 and len(u.talents) == 3
                   for u in realm.all_units(campaign.units))


def test_world_names_are_unique_and_towns_start_staffed():
    for seed in range(30, 45):
        campaign = Campaign(seed)
        assert len({realm.name for realm in campaign.realms.values()}) == len(campaign.realms)
        names = [holding.name for holding in campaign.settlements.values()]
        assert len(set(names)) == len(names)
        for holding in campaign.settlements.values():
            if holding.size in (C.SIZE_T, C.SIZE_C):
                assert holding.has(C.BUILDING_FARM)
                assert holding.buildings
                assert holding.has(C.BUILDING_MARKET) or holding.has(C.BUILDING_MILITIA_HALL)


def test_name_allocator_falls_back_after_forced_collision():
    taken = {"Raven"}
    class FixedChoice:
        def choice(self, _values):
            return "Raven"
    name = names.unique_settlement_name(FixedChoice(), taken)
    assert name == "Raven East"
    assert not name[-1].isdigit()
    assert name in taken
