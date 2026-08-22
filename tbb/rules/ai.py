"""Rival duchy and bandit AI. Plays by the same rules: company cap, staff,
supply, movement costs. AI duchies develop holdings, recruit, outfit, train
and march on weak neighbours. Bandits raid roads and villages. Neutral
holdings never expand."""
from . import constants as C
from . import terrain as G
from . import pathfind
from .settlements import Order


def run_ai_turn(campaign):
    for key in sorted(campaign.realms):
        if key == C.PLAYER_REALM_KEY:
            continue
        realm = campaign.realms[key]
        if realm.destroyed:
            continue
        _duke_month(campaign, realm)
    _bandits_month(campaign)


# ------------------------------------------------------------ duke AI
def _duke_month(campaign, realm):
    _develop(campaign, realm)
    _raise_army(campaign, realm)
    _train_men(campaign, realm)
    _outfit(campaign, realm)
    _march(campaign, realm)


def _order_build_silent(campaign, realm, sid, kind):
    spec = C.BUILDINGS[kind]
    realm.gold -= spec["gold"]
    realm.wheat -= spec.get("wheat", 0)
    from .settlements import Order
    realm.orders.append(Order("build", kind, spec["months"],
                              settlement_id=sid))
    return ok(True)


def ok(v, reason=""):
    from .campaign import Check
    return Check(bool(v), reason)


def _develop(campaign, realm):
    for kind in C.AI_DEVELOP_PRIORITY:
        spec = C.BUILDINGS[kind]
        req = spec["req"]
        for sid in realm.settlement_ids:
            h = campaign.settlements[sid]
            if kind in h.buildings:
                continue
            if any(o.kind == "build" and o.settlement_id == sid and
                   o.kind_data == kind for o in realm.orders):
                continue
            if req and h.size_index() < C.SIZE_ORDER.index(req):
                continue
            if h.building_slots_free() <= 0:
                continue
            if realm.gold < spec["gold"] or realm.wheat < spec.get("wheat", 0):
                continue
            if realm.gold < spec["gold"] + 40:
                continue
            _order_build_silent(campaign, realm, sid, kind)
            return
    # staff up and grow a holding when wealthy
    if realm.gold > 90 and realm.wheat > 20:
        for sid in realm.settlement_ids:
            h = campaign.settlements[sid]
            tgt = _next_size(h.size)
            if tgt is None:
                continue
            cost = C.DEVELOP_COST[(h.size, tgt)]
            if realm.gold >= cost["gold"] and realm.wheat >= cost["wheat"]:
                if not any(o.kind == "develop" and o.settlement_id == sid
                           for o in realm.orders):
                    realm.gold -= cost["gold"]
                    realm.wheat -= cost["wheat"]
                    _order_develop_silent(campaign, realm, sid, tgt,
                                          cost["months"])
                    return


def _next_size(size):
    try:
        i = C.SIZE_ORDER.index(size)
    except ValueError:
        return None
    if i + 1 >= len(C.SIZE_ORDER):
        return None
    return C.SIZE_ORDER[i + 1]


def _order_develop_silent(campaign, realm, sid, tgt, months):
    from .settlements import Order
    realm.orders.append(Order("develop", tgt, months, settlement_id=sid))


def _raise_army(campaign, realm):
    if realm.population < 2 or realm.gold < 40:
        return
    hp = campaign.hero_party(realm.key)
    if hp is None:
        return
    if hp.size() >= 1 + C.COMPANY_CAP:
        return
    sid = realm.settlement_ids[0] if realm.settlement_ids else None
    if sid is None:
        return
    h = campaign.settlements[sid]
    if realm.gold < C.RECRUIT_GOLD * 3 or realm.population < 3:
        return
    # bring the company home or recruit from wherever it stands
    if tuple(hp.hex) != tuple(h.hex):
        return
    gp = campaign.garrison_party(sid)
    field = hp.size()
    if field >= 1 + C.COMPANY_CAP:
        return
    if len(gp.unit_ids) >= 1:
        unit_id = gp.unit_ids[0]
        if hp.size() < 1 + C.COMPANY_CAP:
            gp.remove(unit_id)
            hp.add(unit_id)
        return
    # recruit a fresh hand
    u = _make_ai_unit(campaign, realm, None)
    hp.add(u.id)
    realm.unit_ids.add(u.id)
    realm.population -= 1
    realm.gold -= C.RECRUIT_GOLD
    realm.wheat -= C.RECRUIT_WHEAT


def _make_ai_unit(campaign, realm, name):
    from .units import Unit
    from . import talents as T
    uid = campaign._new_uid()
    name = campaign._unique_name(realm.key) if name is None else name
    rng = campaign.rng
    base = rng.randint(24, 46)
    stats = {
        "melee": base + rng.randint(-6, 12),
        "ranged": base + rng.randint(-10, 8),
        "toughness": base + rng.randint(-4, 8),
        "fatigue": base + rng.randint(-2, 10),
        "resolve": rng.randint(22, 50),
        "initiative": base + rng.randint(-8, 6),
    }
    stats = {k: min(C.STAT_MAX, max(C.STAT_MIN, v)) for k, v in stats.items()}
    u = Unit(uid, name, stats["melee"], stats["ranged"], stats["toughness"],
             stats["fatigue"], stats["resolve"], stats["initiative"],
             T.roll_talents(rng), realm=realm.key)
    campaign.units[uid] = u
    return u


def _train_men(campaign, realm):
    hp = campaign.hero_party(realm.key)
    if hp is None:
        return
    total = realm.training_slots(campaign.settlements)
    used = sum(1 for o in realm.orders if o.kind == "train")
    if used >= total:
        return
    for uid in hp.unit_ids:
        if hp.size() == 0:
            break
        if sum(1 for o in realm.orders if o.kind == "train") >= total:
            break
        u = campaign.units.get(uid)
        if u is None or not u.alive:
            continue
        if sum(1 for o in realm.orders
               if o.kind in ("train", "gear") and o.unit_id == uid):
            continue
        realm.orders.append(Order("train", 1, 1, unit_id=uid))


def _outfit(campaign, realm):
    hp = campaign.hero_party(realm.key)
    if hp is None:
        return
    can = realm.supplies(campaign.settlements)
    for uid in list(hp.unit_ids):
        u = campaign.units.get(uid)
        if u is None or not u.alive:
            continue
        if any(o.kind == "gear" and o.unit_id == uid for o in realm.orders):
            continue
        if u.kit in ("heavy", "two_hand", "heavy_bow"):
            continue
        kit = None
        if (u.stat("ranged") > u.stat("melee")) and "bowyer" in can:
            if realm.gold >= C.KITS["bow"]["gold"] * 3:
                kit = "bow"
        elif "smithy" in can and realm.gold >= C.KITS["heavy"]["gold"] * 3:
            kit = "heavy"
        elif realm.gold >= C.KITS["light"]["gold"] * 4:
            kit = "light"
        if kit is None:
            continue
        spec = C.KITS[kit]
        realm.gold -= spec["gold"]
        realm.wheat -= spec["wheat"]
        realm.orders.append(Order("gear", kit, spec["months"], unit_id=uid))


def _march(campaign, realm):
    hp = campaign.hero_party(realm.key)
    if hp is None:
        return
    if realm.hero is None or not campaign.units[realm.hero].alive:
        return
    if not hp.unit_ids:
        return
    target = _choose_target(campaign, realm)
    if target is None:
        return
    target_realm = campaign.realms[target]
    if not target_realm.settlement_ids:
        return
    goal = tuple(campaign.settlements[target_realm.settlement_ids[0]].hex)
    if tuple(hp.hex) == goal:
        campaign._scan_contacts_for(hp)
        return
    path = pathfind.a_star(campaign.world, hp.hex, goal)
    if not path:
        return
    for nxt in path[1:]:
        if hp.mp <= 0:
            break
        cost = C.MOVE_COST[campaign.world.terrain(nxt)]
        if cost is None or hp.mp < cost:
            break
        hp.mp -= cost
        hp.move_to(nxt)
        campaign._scan_contacts_for(hp)
        if campaign.pending_battles:
            break


def _choose_target(campaign, realm):
    """Weakest live realm is the favourite, else the player."""
    realm.ai_think_timer += 1
    if realm.ai_target is not None and not campaign.realms[realm.ai_target].destroyed:
        stay = realm.ai_target
        if realm.ai_think_timer % C.AI_TARGET_DECAY != 0:
            return stay
    candidates = []
    for key, r in campaign.realms.items():
        if key == realm.key or r.destroyed:
            continue
        strength = _realm_strength(campaign, r)
        candidates.append((strength, key))
    candidates.sort()
    if not candidates:
        return None
    picked = candidates[0][1]
    realm.ai_target = picked
    return picked


def _realm_strength(campaign, realm):
    s = 0
    for uid in realm.unit_ids:
        u = campaign.units.get(uid)
        if u is not None and u.alive:
            s += u.stat("melee") + 10
    for sid in realm.settlement_ids:
        h = campaign.settlements[sid]
        s += C.GARRISON_BASE[h.size] * 3
        s += h.garrison_cap() * 2
    return s


# ------------------------------------------------------------ bandits
def _bandits_month(campaign):
    for party in list(campaign.parties):
        if party.kind != "bandit":
            continue
        _bandit_wander(campaign, party)


def _nearest_holding(campaign, pos):
    best = None
    best_d = 10 ** 9
    for h in campaign.settlements.values():
        d = G.hex_distance(pos, h.hex)
        if d < best_d:
            best_d = d
            best = tuple(h.hex)
    return best


def _bandit_wander(campaign, party):
    target = _nearest_holding(campaign, party.hex)
    if target is None:
        return
    if tuple(party.hex) == tuple(target):
        campaign._scan_contacts_for(party)
        return
    path = pathfind.a_star(campaign.world, party.hex, target)
    if not path:
        return
    for nxt in path[1:]:
        if party.mp <= 0:
            break
        cost = C.MOVE_COST[campaign.world.terrain(nxt)]
        if cost is None or party.mp < cost:
            break
        party.mp -= cost
        party.move_to(nxt)
        campaign._scan_contacts_for(party)
        if campaign.pending_battles:
            break