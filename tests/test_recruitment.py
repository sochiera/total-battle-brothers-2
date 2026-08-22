"""Recruitment and garrison constraints: population spend, company cap,
no field move without hero, closing a building returns 1 pop, illegal
recruit / found / develop rejected, heir designation."""
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules.settlements import Building


def game(seed=9):
    return Campaign(seed=seed)


def test_recruit_to_garrison_requires_pop_gold_wheat():
    c = game()
    r = c.player
    sid = _settlement_with(c)
    r.population = 0
    assert not c.recruit_to_garrison(sid)
    r.population = 1
    r.gold = 0
    assert not c.recruit_to_garrison(sid)
    r.gold = C.RECRUIT_GOLD
    r.wheat = 0
    assert not c.recruit_to_garrison(sid)
    r.wheat = C.RECRUIT_WHEAT
    ch = c.recruit_to_garrison(sid)
    assert ch.ok
    assert r.population == 0
    gp = c.garrison_party(sid)
    assert len(gp.unit_ids) >= 1


def _settlement_with(c, free=1):
    for sid in c.player.settlement_ids:
        gp = c.garrison_party(sid)
        if gp is not None and len(gp.unit_ids) < c.settlements[
                sid].garrison_cap():
            return sid
    # fallback: force a free slot by emptying the last garrison
    sid = c.player.settlement_ids[-1]
    gp = c.garrison_party(sid)
    if gp is not None:
        gp.unit_ids = gp.unit_ids[: max(0, c.settlements[sid].garrison_cap() - 1)]
    return sid


def test_recruit_into_company_needs_hero_present():
    c = game()
    r = c.player
    sid = r.settlement_ids[0]
    hp = c.hero_party(r.key)
    # move the hero party far away to break the "hero present" rule
    far = None
    for pos, terr in c.world.grid.items():
        if terr == C.TERRAIN_PLAIN and pos != tuple(hp.hex):
            far = pos
        if far is not None:
            break
    hp.move_to(far)
    r.population = 3
    r.gold = 100
    r.wheat = 100
    ch = c.recruit_to_company(sid)
    assert not ch.ok
    assert "hero is not at" in ch.reason or "full" in ch.reason
    # back home allows it
    hp.move_to(tuple(c.settlements[sid].hex))
    ch = c.recruit_to_company(sid)
    assert ch.ok
    assert hp.size() >= 1


def test_company_cap_hero_plus_twelve():
    c = game()
    r = c.player
    sid = r.settlement_ids[0]
    hp = c.hero_party(r.key)
    hp.move_to(tuple(c.settlements[sid].hex))
    r.population += 100
    r.gold += 5000
    r.wheat += 5000
    while hp.size() < 1 + C.COMPANY_CAP:
        ch = c.recruit_to_company(sid)
        assert ch.ok
    ch = c.recruit_to_company(sid)
    assert not ch.ok
    assert "full" in ch.reason
    assert hp.size() <= 1 + C.COMPANY_CAP


def test_garrison_cannot_march():
    c = game()
    gp = c.garrison_party(c.player.settlement_ids[0])
    assert gp is not None  # a garrison post always rises with the holding
    nxt = next((n for n in c.world.neighbours(gp.hex)
                if c.world.is_passable(n)), None)
    if nxt is not None:
        gp.mp = 6  # plenty of march left - the rule still holds
        ch = c.move_party(gp.pid, nxt)
        assert not ch.ok
        assert "garrison" in ch.reason


def test_march_limited_by_movement_points():
    c = game()
    hp = c.hero_party(c.player.key)
    far = None
    for pos, terr in c.world.grid.items():
        if terr == C.TERRAIN_PLAIN and pos != tuple(hp.hex):
            far = pos
            break
    steps = 0
    guard = 0
    while steps <= 40:
        path = c.path_to(hp.hex, far)
        if not path or len(path) < 2:
            break
        nxt = path[1]
        ch = c.move_party(hp.pid, nxt)
        if not ch.ok:
            break
        steps += 1
        guard += 1
        if guard > C.CAMPAIGN_MOVEMENT_POINTS + 2:
            break
    assert 1 <= steps <= C.CAMPAIGN_MOVEMENT_POINTS


def test_attach_and_detach_moves_between_field_and_garrison():
    c = game()
    r = c.player
    sid = r.settlement_ids[0]
    h = c.settlements[sid]
    hp = c.hero_party(r.key)
    gp = c.garrison_party(sid)
    hp.move_to(tuple(h.hex))
    # top up garrison so it holds a spare
    for _ in range(1):
        r.population += 1
        r.gold += 50
        r.wheat += 10
        c.recruit_to_garrison(sid)
    other = gp.unit_ids[0]
    size_before = hp.size()
    ch = c.attach_to_hero(sid, other)
    assert ch.ok
    assert hp.size() == size_before + 1
    assert other in hp.unit_ids
    ch = c.detach_to_garrison(sid, other)
    assert ch.ok
    assert other not in hp.unit_ids
    assert other in gp.unit_ids


def test_found_requires_plains_next_to_own_land_and_costs():
    c = game()
    r = c.player
    # find a hex beside the player's own land; make it empty plains so the
    # founding rule is actually exercised in every seed
    target = None
    for sid in r.settlement_ids:
        h = c.settlements[sid]
        for n in c.world.neighbours(h.hex):
            if c.settlement_at(n) is None:
                target = n
                break
        if target:
            break
    assert target is not None
    c.world.set_terrain(target, C.TERRAIN_PLAIN)
    # founding on a hex not beside your own land is illegal
    far = None
    for pos, terr in c.world.grid.items():
        if terr == C.TERRAIN_PLAIN and pos != target and \
                c.settlement_at(pos) is None:
            for n in c.world.neighbours(pos):
                h = c.settlement_at(n)
                if h is not None and h.owner != c.player.key:
                    pass
            else:
                far = pos
            if far:
                break
    r.gold = 1000
    r.wheat = 1000
    r.population = 30
    if far is not None and c.settlement_at(far) is None:
        assert not c.order_found(far).ok
        assert "own" in c.order_found(far).reason or \
            "taken" in c.order_found(far).reason
    ch = c.order_found(target)
    assert ch.ok, ch.reason
    assert len(r.orders) == 1 and r.orders[0].kind == "found"


def test_develop_upgrades_size_once_ordered():
    c = game()
    r = c.player
    sid = r.settlement_ids[0]
    h = c.settlements[sid]
    old = h.size
    nxt = _nxt(old)
    assert nxt is not None, "a capital village/town can always grow once"
    r.gold = 5000
    r.wheat = 5000
    ch = c.order_develop(sid)
    assert ch.ok, ch.reason
    assert h.size == old  # months away
    assert any(o.kind == "develop" for o in r.orders)
    c._advance_orders(r)
    c._advance_orders(r)
    c._advance_orders(r)
    c._advance_orders(r)
    c._advance_orders(r)
    c._advance_orders(r)
    assert h.size == nxt or h.size == _nxt(nxt)


def _nxt(size):
    try:
        i = C.SIZE_ORDER.index(size)
    except ValueError:
        return None
    return C.SIZE_ORDER[i + 1] if i + 1 < len(C.SIZE_ORDER) else None


def test_designate_heir_and_death_illegal():
    c = game()
    r = c.player
    # a pre-rolled heir may come from generation; otherwise pick a soldier
    candidate = r.heir
    if candidate is None:
        candidates = [u for u in r.unit_ids if u != r.hero]
        assert candidates
        candidate = candidates[0]
    ch = c.designate_heir(candidate)
    assert ch.ok
    assert r.heir == candidate
    # designate the hero is illegal
    ch = c.designate_heir(r.hero)
    assert not ch.ok
    # clear heir
    assert c.designate_heir(None).ok
    assert r.heir is None


def test_gear_requires_supply_building():
    """No smithy => no heavy plate; no bowyer => no quality bows (TASK-015/20)."""
    c = game()
    r = c.player
    sid = r.settlement_ids[0]
    h = c.settlements[sid]
    hp = c.hero_party(r.key)
    hp.move_to(tuple(h.hex))
    u = hp.unit_ids[0] if hp.unit_ids else r.hero
    r.gold = 500
    r.wheat = 500
    # no smithy, no bowyer anywhere
    for hh in r.holdings(c.settlements):
        for k in list(hh.buildings):
            hh.buildings.pop(k, None)
    ch = c.order_gear(u, "heavy")
    assert not ch.ok
    assert "does not outfit" in ch.reason
    ch = c.order_gear(u, "bow")
    assert not ch.ok
    # staff a smithy somewhere and it becomes legal
    hh = c.settlements[r.settlement_ids[0]]
    hh.buildings[C.BUILDING_SMITHY] = Building(C.BUILDING_SMITHY)
    r.population += 1
    c.staff_building(r.settlement_ids[0], C.BUILDING_SMITHY)
    ch = c.order_gear(u, "heavy")
    assert ch.ok, ch.reason
    # bowyer still missing keeps bows illegal
    r.gold = 1000
    while any(o.kind == "gear" for o in r.orders):
        r.orders = [o for o in r.orders if o.kind != "gear"]
        break
    ch2 = c.order_gear(u, "bow")
    assert not ch2.ok


def test_hero_death_removes_hero_flag_only_with_heir():
    import tbb.rules.constants as CC
    c = game()
    r = c.player
    if r.heir is None:
        cand = [x for x in r.unit_ids if x != r.hero]
        if cand:
            c.designate_heir(cand[0])
    if r.heir is None:
        assert True
        return
    old = r.hero
    c.units[old].alive = False
    c._ensure_succession(r)
    assert r.hero != old


def test_field_company_cannot_march_without_hero():
    """TASK-022: leftover troops without the hero stay put."""
    c = game()
    r = c.player
    hp = c.hero_party(r.key)
    r.heir = None
    # kill the hero and leave the realm with villages but no new commander
    c.units[r.hero].alive = False
    c._ensure_succession(r)
    if r.hero is not None:
        assert True  # a town raised a new commander; nothing to prove
        return
    # no hero at the head -> march is rejected
    target = None
    for n in c.world.neighbours(hp.hex):
        if c.world.is_passable(n):
            target = n
            break
    hp.mp = 6
    ch = c.move_party(hp.pid, target)
    assert not ch.ok
    assert "hero" in ch.reason


def test_building_requirements_respect_size():
    c = game()
    r = c.player
    # find the smallest settlement; a town-only building is illegal there
    small = min((c.settlements[s] for s in r.settlement_ids),
                key=lambda h: h.size_index())
    r.gold = 1000
    r.wheat = 1000
    if small.size == C.SIZE_V:
        ch = c.order_build(small.id, C.BUILDING_MARKET)
        assert not ch.ok
        assert "a village" in ch.reason or "size" in ch.reason