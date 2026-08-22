from tbb.rules import constants as C
from tbb.rules.rng import RNG
from tbb.rules.worldgen import generate
from tbb.rules.campaign import Campaign


def test_world_is_large_varied_and_seeded():
    first, second = generate(RNG(2)), generate(RNG(3))
    assert first["world"].hex_count() == C.MAP_WIDTH * C.MAP_HEIGHT
    assert set(first["world"].grid.values()) == set(C.CAMPAIGN_TERRAINS)
    assert first["world"].crossings and first["world"].grid != second["world"].grid
    assert len(first["realms"]) == C.NUM_DUCHIES
    assert sum(p.kind == "bandit" for p in first["parties"]) == C.NUM_ROBBER_BANDS
    assert len([h for h in first["settlements"].values() if h.owner is None]) >= C.MIN_NEUTRALS


def test_start_archetypes_have_one_hero_and_company_cap():
    starts = [len(Campaign(seed).player.settlement_ids) for seed in range(11, 19)]
    assert 1 in starts and (2 in starts or 3 in starts)
    campaign = Campaign(734102)
    for realm in campaign.realms.values():
        party = campaign.hero_party(realm.key)
        assert realm.hero in party.unit_ids
        assert len(party.unit_ids) <= C.COMPANY_CAP
        assert sum(u.is_hero for u in realm.all_units(campaign.units)) == 1
        assert all(u.origin and 16 <= u.age <= 40 and len(u.talents) == 3
                   for u in realm.all_units(campaign.units))
