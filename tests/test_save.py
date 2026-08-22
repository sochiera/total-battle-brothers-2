"""Save-roundtrip: a mid-campaign fixture with wounds, in-progress
gear/training orders, bandits, and a designated heir restores equal
rules-level state."""
import os
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules import persistence as P


def _fixture():
    c = Campaign(seed=1234)
    r = c.player
    # give the realm some wealth so orders can be placed
    r.gold = 500
    r.wheat = 500
    r.population = 40
    sid = r.settlement_ids[0]
    h = c.settlements[sid]
    # designate an heir
    cand = [u for u in r.unit_ids if u != r.hero]
    if cand:
        c.designate_heir(cand[0])
    # a training order and a gear order are in flight
    hp = c.hero_party(r.key)
    u = c.units[hp.unit_ids[0]] if hp.unit_ids else c.units[r.hero]
    if hp and u.id in hp.unit_ids and r.gold >= 30:
        c.order_gear(u.id, "light")
    if c.player.training_slots(c.settlements) > 0:
        c.order_train(u.id, 1)
    # wound somebody
    c.units[r.hero].wounds.append("maimed leg")
    # run a few months forward for a mid-campaign feel
    for _ in range(3):
        res = c.end_turn()
        if not res.ok:
            c.auto_resolve_pending()
            c.end_turn()
        if c.ended:
            break
    if not c.pending_battles:
        foe = c.hero_party(1)
        if foe is not None:
            c._make_battle(c.hero_party(r.key), foe, assault=False)
    return c


def test_save_roundtrip(tmp_path):
    c = _fixture()
    canon_before = P.canonical(c)
    P.save(c, "slot1", save_dir=tmp_path)
    d2 = P.load("slot1", save_dir=tmp_path)
    assert d2 is not None
    assert d2.pending_battles
    assert P.canonical(d2) == canon_before


def test_save_slot_names_and_missing(tmp_path):
    assert P.load("nope", save_dir=tmp_path) is None
    c = Campaign(seed=5)
    P.save(c, "mid", save_dir=tmp_path)
    assert os.path.exists(P.save_path("mid", tmp_path))
    assert P.load("mid", save_dir=tmp_path) is not None


def test_loaded_game_continues_deterministically(tmp_path):
    c = _fixture()
    P.save(c, "a", save_dir=tmp_path)
    loaded = P.load("a", save_dir=tmp_path)
    for game in (c, loaded):
        game.auto_resolve_pending()
        game.end_turn()
    assert P.canonical(loaded) == P.canonical(c)


def test_pending_battle_and_game_over_are_json_fields(tmp_path):
    c = _fixture()
    c.ended = True
    c.end_reason = "defeat"
    P.save(c, "ended", save_dir=tmp_path)
    loaded = P.load("ended", save_dir=tmp_path)
    assert loaded.ended is True
    assert loaded.end_reason == "defeat"
    assert loaded.pending_battles
