"""Succession, defeat and victory edge cases: heir takes over with morale drop,
campaign continues; hero dead but a town can raise a commander is NOT defeat;
last-duchy victory is enforced."""
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign


def game(seed=17):
    return Campaign(seed)


def _kill_hero(c, realm):
    u = c.units[realm.hero]
    u.alive = False


def test_heir_takes_over_on_hero_death():
    c = game()
    r = c.player
    if r.heir is None:
        # designate one first
        cand = [u for u in r.unit_ids if u != r.hero]
        assert cand
        assert c.designate_heir(cand[0]).ok
    heir = r.heir
    assert heir is not None
    morale_before = r.morale
    _kill_hero(c, r)
    c._ensure_succession(r)
    assert r.hero == heir
    assert r.heir is None
    assert r.morale < morale_before
    assert c.units[heir].is_hero
    # campaign continues
    assert c.ended is False


def test_hero_dead_with_town_but_no_heir_continues():
    c = game()
    r = c.player
    r.heir = None
    if not any(c.settlements[s].size != C.SIZE_V for s in r.settlement_ids):
        # promote a holding so a town exists
        for sid in r.settlement_ids:
            c.settlements[sid].size = C.SIZE_T
            break
    _kill_hero(c, r)
    c._ensure_succession(r)
    assert r.hero is not None
    assert r.hero is not None  # the council raises a new commander
    assert c.ended is False
    u = c.units[r.hero]
    assert u.is_hero and u.alive


def test_hero_dead_no_heir_no_town_with_villages_is_not_defeat():
    c = game()
    r = c.player
    r.heir = None
    # keep only villages
    for sid in r.settlement_ids:
        c.settlements[sid].size = C.SIZE_V
    # keep one village
    r.settlement_ids = r.settlement_ids[:1]
    _kill_hero(c, r)
    c._ensure_succession(r)
    assert r.hero is None
    c.check_end_conditions()
    assert not c.ended  # village remains: not a total loss yet


def test_defeat_when_all_lost_hero_dead_no_estate():
    c = game()
    r = c.player
    r.heir = None
    r.settlement_ids = []
    _kill_hero(c, r)
    c.check_end_conditions()
    assert c.ended
    assert c.end_reason == "defeat"


def test_victory_last_duchy():
    c = game()
    pk = c.player.key
    for k in c.realms:
        if k != pk:
            r = c.realms[k]
            r.settlement_ids = []
            r.destroyed = False
            if r.hero is not None:
                c.units[r.hero].alive = False
    c.check_end_conditions()
    assert c.ended
    assert c.end_reason == "victory"


def test_mid_loss_of_hero_with_heir_loses_morale_but_continues():
    c = game()
    r = c.player
    if r.heir is None:
        cand = [u for u in r.unit_ids if u != r.hero]
        assert cand
        c.designate_heir(cand[0])
    morale_before = r.morale
    _kill_hero(c, r)
    c._ensure_succession(r)
    assert c.ended is False
    assert r.morale < morale_before


def test_conquest_destroys_duchy_only_with_hero_gone():
    """TASK-032/035: an assault that takes the last holding does not end the
    game while that duchy's hero still stands; it ends only when the hero is
    gone too."""
    c = game()
    target = c.realms[1]
    # take every settlement of realm 1 for the player
    for sid in list(target.settlement_ids):
        c._conquer(sid, c.player.key)
    assert not target.settlement_ids
    c.check_end_conditions()
    assert not c.ended
    assert not target.destroyed   # hero still alive
    # now the hero falls
    c.units[target.hero].alive = False
    c.check_end_conditions()
    assert target.destroyed
    assert not c.ended            # the player is still whole
    # last duchy left => victory
    for k in c.realms:
        if k not in (0, target.key):
            rr = c.realms[k]
            rr.settlement_ids = []
            c.units[rr.hero].alive = False
    c.check_end_conditions()
    assert c.ended and c.end_reason == "victory"


def test_destroyed_duchy_flag():
    c = game()
    r = c.realms[1]
    r.settlement_ids = []
    if r.hero is not None:
        c.units[r.hero].alive = False
    c.check_end_conditions()
    assert r.destroyed
