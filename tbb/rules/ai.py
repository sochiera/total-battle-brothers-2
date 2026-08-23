"""Deterministic duke and robber turns.

AI deliberately calls the same order and unit primitives as the player.  It
does not get free soldiers, free buildings, or a special combat resolver.
"""
from . import constants as C
from . import terrain as G
from . import pathfind
from .settlements import Order


def priority_buildings():
    return list(C.AI_DEVELOP_PRIORITY)


def _holding_strength(campaign, holding):
    guard = campaign.garrison_party(holding.id)
    if not guard:
        return 0
    return sum(campaign.units[uid].stat("melee")
               for uid in guard.unit_ids if campaign.units[uid].alive)


def _target_score(campaign, holding, origin):
    """Prefer an exposed holding, with a small preference for neutrals."""
    strength = _holding_strength(campaign, holding) / 30.0
    weakness = max(0.0, 12.0 - strength)
    neutral_bonus = 3.0 if holding.owner is None else 0.0
    distance = G.hex_distance(origin, holding.hex)
    return weakness * 2.0 + neutral_bonus - distance


def choose_march_target(campaign, realm_key, origin, bandit=False):
    options = []
    for holding in campaign.settlements.values():
        if not bandit and holding.owner == realm_key:
            continue
        if holding.owner is not None:
            other = campaign.realms.get(holding.owner)
            if other is None or other.destroyed:
                continue
        options.append((_target_score(campaign, holding, origin), holding.id))
    return max(options)[1] if options else None


def nearest_hostile(campaign, realm_key, origin):
    """Choose a reachable weak holding, not a hard-coded player capital."""
    return choose_march_target(campaign, realm_key, origin)


def run_ai_turn(campaign):
    """Resolve one month for every rival and all three robber bands."""
    for realm in sorted(campaign.realms.values(), key=lambda item: item.key):
        if realm.is_player or realm.destroyed:
            continue
        _staff_existing(campaign, realm)
        _market_when_short(campaign, realm)
        _develop(campaign, realm)
        _found(campaign, realm)
        _raise_army(campaign, realm)
        _train_men(campaign, realm)
        _outfit(campaign, realm)
        _march(campaign, realm)
    _bandits_month(campaign)


def _found(campaign, realm):
    """A rival that can afford it seeds a new village on legal adjacent
    land, keeping one idle worker at home."""
    if _has_order(realm, "found"):
        return
    if realm.gold < C.FOUND_COST["gold"] or realm.wheat < C.FOUND_COST["wheat"]:
        return
    if not campaign._can_spend_population(realm, C.FOUND_COST["settlers"]):
        return
    world = campaign.world
    candidates = []
    for sid in realm.settlement_ids:
        for pos in sorted(world.neighbours(campaign.settlements[sid].hex)):
            if campaign.settlement_at(pos) is not None:
                continue
            if not G.can_found(world.terrain(pos)):
                continue
            if any(p.hex == pos and p.kind == "bandit" and
                   p.alive_units(campaign.units) for p in campaign.parties):
                continue
            candidates.append(pos)
    if not candidates:
        return
    realm.gold -= C.FOUND_COST["gold"]
    realm.wheat -= C.FOUND_COST["wheat"]
    realm.population -= C.FOUND_COST["settlers"]
    realm.orders.append(Order("found", candidates[0],
                              C.FOUND_COST["months"]))


def _staff_existing(campaign, realm):
    for sid in realm.settlement_ids:
        holding = campaign.settlements[sid]
        for building in holding.buildings.values():
            if building.staffed:
                continue
            if not campaign._can_spend_population(realm):
                continue
            building.staffed = True
            realm.population -= 1


def _market_when_short(campaign, realm):
    if realm.gold >= 30 or not realm.staffed(campaign.settlements, C.BUILDING_MARKET):
        return
    if realm.wheat >= C.MARKET_SELL_WHEAT:
        realm.wheat -= C.MARKET_SELL_WHEAT
        realm.gold += C.MARKET_SELL_GOLD


def _has_order(realm, kind, sid=None):
    return any(order.kind == kind and (sid is None or order.settlement_id == sid)
               for order in realm.orders)


def _develop(campaign, realm):
    for sid in realm.settlement_ids:
        holding = campaign.settlements[sid]
        if holding.building_slots_free() <= 0 or _has_order(realm, "build", sid):
            continue
        for kind in C.AI_DEVELOP_PRIORITY:
            spec = C.BUILDINGS[kind]
            if kind in holding.buildings:
                continue
            if spec["req"] and holding.size_index() < C.SIZE_ORDER.index(spec["req"]):
                continue
            if realm.gold < spec["gold"] or realm.wheat < spec["wheat"]:
                continue
            realm.gold -= spec["gold"]
            realm.wheat -= spec["wheat"]
            realm.orders.append(Order("build", kind, spec["months"], sid))
            return
    # Growth is a separate order and is only attempted when no building was
    # affordable, so a duke does not spend the same treasury twice.
    for sid in realm.settlement_ids:
        holding = campaign.settlements[sid]
        if _has_order(realm, "develop", sid):
            continue
        index = C.SIZE_ORDER.index(holding.size)
        if index + 1 >= len(C.SIZE_ORDER):
            continue
        target = C.SIZE_ORDER[index + 1]
        if holding.population < C.DEVELOP_POP_GATE[(holding.size, target)]:
            continue
        if len(holding.buildings) < C.DEVELOP_BUILDING_GATE[(holding.size, target)]:
            continue
        cost = C.DEVELOP_COST[(holding.size, target)]
        if realm.gold >= cost["gold"] and realm.wheat >= cost["wheat"]:
            realm.gold -= cost["gold"]
            realm.wheat -= cost["wheat"]
            realm.orders.append(Order("develop", target, cost["months"], sid))
            return


def _raise_army(campaign, realm):
    if _has_order(realm, "recruit"):
        return
    if realm.gold < C.RECRUIT_COST["gold"] or realm.wheat < C.RECRUIT_COST["wheat"]:
        return
    if not campaign._can_spend_population(realm, C.RECRUIT_COST["population"]):
        return
    for sid in realm.settlement_ids:
        holding = campaign.settlements[sid]
        garrison = campaign.garrison_party(sid)
        queued = sum(1 for order in realm.orders
                     if order.kind == "recruit" and order.kind_data == "garrison"
                     and order.settlement_id == sid)
        if garrison and len(garrison.unit_ids) + queued < holding.garrison_cap():
            realm.gold -= C.RECRUIT_COST["gold"]
            realm.wheat -= C.RECRUIT_COST["wheat"]
            realm.population -= C.RECRUIT_COST["population"]
            realm.orders.append(Order("recruit", "garrison", C.RECRUIT_COST["months"], sid))
            return
    party = campaign.hero_party(realm.key)
    if party is None or realm.hero not in party.unit_ids:
        return
    if len(party.unit_ids) >= C.COMPANY_CAP:
        return
    for sid in realm.settlement_ids:
        if party.hex == campaign.settlements[sid].hex:
            realm.gold -= C.RECRUIT_COST["gold"]
            realm.wheat -= C.RECRUIT_COST["wheat"]
            realm.population -= C.RECRUIT_COST["population"]
            realm.orders.append(Order("recruit", "field", C.RECRUIT_COST["months"], sid))
            return


def _train_men(campaign, realm):
    slots = realm.training_slots(campaign.settlements)
    used = sum(1 for order in realm.orders if order.kind == "train")
    if used >= slots:
        return
    party = campaign.hero_party(realm.key)
    if party is None:
        return
    disciplines = (C.BUILDING_DRILL_YARD, C.BUILDING_SMITHY,
                   C.BUILDING_FLETCHER, C.BUILDING_STABLES)
    focus = next((kind for kind in disciplines
                  if realm.staffed(campaign.settlements, kind)), None)
    if focus is None:
        return
    for uid in party.unit_ids:
        unit = campaign.units[uid]
        if unit.alive and not any(order.kind == "train" and order.unit_id == uid
                                  for order in realm.orders):
            realm.orders.append(Order("train", focus, 1, unit_id=uid, focus=focus))
            return


def _outfit(campaign, realm):
    party = campaign.hero_party(realm.key)
    if party is None:
        return
    for uid in party.unit_ids:
        unit = campaign.units[uid]
        if not unit.alive or any(order.kind == "gear" and order.unit_id == uid
                                 for order in realm.orders):
            continue
        kit = None
        if (unit.stat("ranged") >= unit.stat("melee") and
                realm.staffed(campaign.settlements, C.BUILDING_FLETCHER)):
            kit = "bow"
        elif realm.staffed(campaign.settlements, C.BUILDING_SMITHY):
            kit = "two_hander" if unit.stat("melee") >= 42 else "heavy"
        if kit is None:
            continue
        if unit.kit == kit:
            continue
        spec = C.KITS[kit]
        if realm.gold < spec["gold"] or realm.wheat < spec["wheat"]:
            continue
        realm.gold -= spec["gold"]
        realm.wheat -= spec["wheat"]
        realm.orders.append(Order("gear", kit, spec["months"], unit_id=uid))
        return


def _march(campaign, realm):
    party = campaign.hero_party(realm.key)
    if party is None or realm.hero not in party.unit_ids:
        return
    if not campaign.units[realm.hero].alive:
        return
    while party.mp > 0 and not campaign.pending_battles:
        sid = choose_march_target(campaign, realm.key, party.hex)
        if sid is None:
            return
        realm.ai_target = sid
        goal = campaign.settlements[sid].hex
        route = pathfind.a_star(campaign.world, party.hex, goal)
        if len(route) < 2:
            return
        target = route[1]
        cost = G.move_cost(campaign.world.terrain(target),
                           campaign.world.crossing(target))
        if cost is None:
            return
        if campaign.world.terrain(target) == C.TERRAIN_ROAD and not party.road_bonus:
            party.mp += C.ROAD_MOVEMENT_BONUS
            party.road_bonus = True
        if party.mp < cost:
            return
        party.mp -= cost
        party.move_to(target)
        campaign._scan_contacts_for(party)


def _bandits_month(campaign):
    for party in campaign.parties:
        if party.kind != "bandit":
            continue
        if not party.alive_units(campaign.units):
            continue
        target_id = choose_march_target(campaign, None, party.hex, bandit=True)
        if target_id is None:
            continue
        target = campaign.settlements[target_id]
        route = pathfind.a_star(campaign.world, party.hex, target.hex)
        if len(route) < 2:
            campaign._scan_contacts_for(party)
            continue
        step = route[1]
        cost = G.move_cost(campaign.world.terrain(step),
                           campaign.world.crossing(step))
        if (campaign.world.terrain(step) == C.TERRAIN_ROAD and
                not party.road_bonus):
            party.mp += C.ROAD_MOVEMENT_BONUS
            party.road_bonus = True
        if cost is None or party.mp < cost:
            continue
        party.mp -= cost
        party.move_to(step)
        campaign._scan_contacts_for(party)
