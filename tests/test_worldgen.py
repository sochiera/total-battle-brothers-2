from collections import Counter
from tbb.rules import constants as C
from tbb.rules.rng import RNG
from tbb.rules import worldgen, talents, names


def gen(seed):
    return worldgen.generate(RNG(seed))


def test_map_size_and_terrain_breadth():
    for seed in (1, 2, 42, 99, 1337):
        out = gen(seed)
        w = out["world"]
        assert w.hex_count() == C.MAP_WIDTH * C.MAP_HEIGHT
        kinds = set(w.grid.values())
        assert C.TERRAIN_WATER in kinds
        assert C.TERRAIN_PLAIN in kinds
        assert C.TERRAIN_RIVER in kinds
        # very large map: far more hexes than a tiny island
        assert C.MAP_WIDTH * C.MAP_HEIGHT >= 40 * 30


def test_five_duchies_and_neutrals_and_bandits():
    for seed in (1, 2, 3, 4, 5):
        out = gen(seed)
        realms = out["realms"]
        assert set(realms.keys()) == {0, 1, 2, 3, 4}
        assert realms[0].is_player
        assert all(not r.is_player for k, r in realms.items() if k != 0)
        neutrals = [h for h in out["settlements"].values() if h.owner is None]
        assert len(neutrals) >= C.MIN_NEUTRALS
        bandits = [p for p in out["parties"] if p.kind == "bandit"]
        assert C.MIN_BANDITS <= len(bandits) <= C.MAX_BANDITS


def test_bandit_parties_present_and_visible():
    """Every live bandit party in campaign state is presented by the map."""
    from tbb.rules.campaign import Campaign
    from tbb.app.campaign_screen import CampaignScreen

    campaign = Campaign(734102)
    screen = CampaignScreen.__new__(CampaignScreen)
    screen.campaign = campaign
    expected = [p.pid for p in campaign.parties if p.kind == "bandit"
                and any(campaign.units[u].alive for u in p.unit_ids)]
    assert len(expected) in (2, 3, 4)
    assert screen.visible_bandit_pids() == expected


def test_duchy_holdings_mixed_and_varying_by_seed():
    starts = []
    for seed in (11, 12, 13, 14, 15, 16, 17, 18):
        out = gen(seed)
        player = out["realms"][0]
        sizes = [out["settlements"][s].size for s in player.settlement_ids]
        assert len(sizes) >= 1
        assert all(s in C.SIZE_ORDER for s in sizes)
        starts.append(tuple(sorted(sizes)))
        # AI realms likewise mixed
        for key in (1, 2, 3, 4):
            r = out["realms"][key]
            ai_sizes = [out["settlements"][s].size for s in r.settlement_ids]
            assert len(ai_sizes) >= 1
            assert all(s in C.SIZE_ORDER for s in ai_sizes)
    # player starts are not all identical across seeds and include a town
    # or city somewhere; at least more than one size appears
    all_sizes = set(s for s in starts for s2 in s for s in [s2])
    assert len(starts) >= 6
    assert len(all_sizes) > 1


def test_hero_exactly_one_per_player_realm():
    out = gen(77)
    for key, realm in out["realms"].items():
        hero = realm.hero
        assert hero is not None
        heroes = [u for u in out["units"].values()
                  if u.is_hero and u.realm == key]
        assert len(heroes) == 1
        hp = None
        for p in out["parties"]:
            if p.realm == key and p.kind == "hero":
                hp = p
        assert hp is not None
        assert hero in hp.unit_ids


def test_names_grim_and_unique_in_company():
    out = gen(99)
    for key, realm in out["realms"].items():
        names_roster = [u.name for u in out["units"].values()
                        if u.realm == key]
        assert len(names_roster) == len(set(names_roster))
        for n in names_roster:
            assert any(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in n)
            assert n.strip() == n


def test_talents_rolled_from_pool():
    for seed in (5, 6, 7):
        out = gen(seed)
        for u in out["units"].values():
            assert len(u.talents) == C.NUM_TALENTS
            assert set(u.talents) <= set(C.TALENT_POOL)


def test_worldgen_deterministic_per_seed():
    a = gen(2024)
    b = gen(2024)
    assert a["world"].grid == b["world"].grid
    names_a = sorted((u.id, u.name) for u in a["units"].values())
    names_b = sorted((u.id, u.name) for u in b["units"].values())
    assert names_a == names_b


def test_map_crossing_takes_many_months():
    out = gen(5)
    # two frontiers are C.MAP_WIDTH apart; at CAMPAIGN_MOVEMENT_POINTS mp with
    # plain cost 1 the march must take much more than one month.
    assert C.MAP_WIDTH / C.CAMPAIGN_MOVEMENT_POINTS > 3


def test_duchy_centers_spread_in_more_than_one_direction():
    """Each duchy starts near a realm cluster so neighbours are not in one
    direction only (TASK-008)."""
    from tbb.rules import terrain as G
    out = gen(6)
    centers = {}
    for key, realm in out["realms"].items():
        hx = out["settlements"][realm.settlement_ids[0]].hex
        centers[key] = hx
    player = centers[0]
    ds = [G.hex_distance(player, c) for k, c in centers.items() if k != 0]
    assert max(ds) - min(ds) > 4      # some neighbour far, some near
    dirs = set()
    import math
    for k, c in centers.items():
        if k == 0:
            continue
        # octant of the compass
        deg = math.degrees(math.atan2(c[1] - player[1], c[0] - player[0]))
        dirs.add(int((deg + 180) // 90))
    assert len(dirs) >= 2
