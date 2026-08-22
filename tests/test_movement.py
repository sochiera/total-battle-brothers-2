from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules.settlements import Building


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


def test_road_and_staffed_stables_bonuses_stack_mid_month():
    campaign = Campaign(13)
    realm = campaign.player
    sid = realm.settlement_ids[0]
    campaign.settlements[sid].buildings[C.BUILDING_STABLES] = Building(
        C.BUILDING_STABLES, staffed=True)
    party = campaign.hero_party(realm.key)
    start = party.hex
    target = campaign.world.neighbours(start)[0]
    campaign.world.set_terrain(start, C.TERRAIN_PLAINS)
    campaign.world.set_terrain(target, C.TERRAIN_ROAD)
    party.mp = C.CAMPAIGN_MOVEMENT_POINTS + C.STABLES_MOVE_BONUS
    party.road_bonus = False
    assert campaign.move_party(party.pid, target)
    assert party.mp == (C.CAMPAIGN_MOVEMENT_POINTS +
                        C.STABLES_MOVE_BONUS + C.ROAD_MOVEMENT_BONUS - 1)


def test_hostile_party_contact_opens_a_player_battle():
    campaign = Campaign(14)
    player_party = campaign.hero_party(campaign.player.key)
    rival = campaign.hero_party(1)
    target = campaign.world.neighbours(player_party.hex)[0]
    campaign.world.set_terrain(target, C.TERRAIN_PLAINS)
    rival.move_to(target)
    player_party.mp = 4
    assert campaign.move_party(player_party.pid, target)
    assert campaign.pending_battles
