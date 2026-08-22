from tbb.rules import constants as C
from tbb.rules.campaign import Campaign


def test_movement_costs_roads_rivers_and_hero_lock():
    campaign = Campaign(11)
    party = campaign.hero_party(campaign.player.key)
    start = party.hex
    campaign.world.set_terrain(start, C.TERRAIN_PLAINS)
    target = campaign.world.neighbours(start)[0]
    campaign.world.set_terrain(target, C.TERRAIN_FOREST)
    party.mp = 4
    assert campaign.move_party(party.pid, target)
    assert party.mp == 2
    campaign.world.set_terrain(target, C.TERRAIN_RIVER)
    party.move_to(start)
    party.mp = 4
    assert not campaign.move_party(party.pid, target)
    campaign.units[campaign.player.hero].alive = False
    assert not campaign.move_party(party.pid, start)


def test_robbers_do_not_start_battles_with_each_other():
    campaign = Campaign(12)
    robbers = [p for p in campaign.parties if p.kind == "bandit"]
    for party in robbers:
        party.move_to(robbers[0].hex)
    assert not campaign._parties_hostile(robbers[0], robbers[1])
