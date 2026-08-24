from tbb.rules import constants as C
from tbb.rules.campaign import Campaign


def test_heir_succeeds_with_explicit_shaken_resolve_cap():
    campaign = Campaign(31)
    realm = campaign.player
    candidate = next(uid for uid in realm.unit_ids
                     if uid != realm.hero and campaign.units[uid].alive)
    assert campaign.designate_heir(candidate)
    old = realm.hero
    campaign.units[old].alive = False
    campaign._ensure_succession(realm)
    assert realm.hero == candidate
    shaken = [campaign.units[uid] for uid in realm.unit_ids
              if uid != candidate and campaign.units[uid].alive]
    assert shaken and all(u.shaken for u in shaken)
    assert all(u.stat("resolve") <= C.SHAKEN_RESOLVE_CAP for u in shaken)
    assert not any(any(u.wound_name(wound) == "bruise"
                       for wound in u.wounds) for u in shaken)


def test_total_loss_defeat_and_last_duchy_victory():
    defeat = Campaign(32)
    defeat.player.settlement_ids = []
    defeat.designate_heir(None)
    defeat.units[defeat.player.hero].alive = False
    defeat.check_end_conditions()
    assert defeat.ended and defeat.end_reason == "defeat"
    victory = Campaign(33)
    for key, realm in victory.realms.items():
        if key != victory.player.key:
            realm.settlement_ids = []
            realm.heir = None
            victory.units[realm.hero].alive = False
    victory.check_end_conditions()
    assert victory.ended and victory.end_reason == "victory"
