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


def nearest_hostile(campaign, realm_key, origin):
    options = []
    for key, realm in campaign.realms.items():
        if key == realm_key or realm.destroyed:
            continue
        for sid in realm.settlement_ids:
            options.append((G.hex_distance(origin, campaign.settlements[sid].hex), sid))
    return min(options)[1] if options else None


def run_ai_turn(campaign):
    """Resolve one month for every rival and all three robber bands."""
    for realm in sorted(campaign.realms.values(), key=lambda item: item.key):
        if realm.is_player or realm.destroyed:
            continue
        _staff_existing(campaign, realm)
        _market_when_short(campaign, realm)
        _develop(campaign, realm)
        _raise_army(campaign, realm)
        _train_men(campaign, realm)
        _outfit(campaign, realm)
        _march(campaign, realm)
    _bandits_month(campaign)


def _staff_existing(campaign, realm):
    for sid in realm.settlement_ids:
        holding = campaign.settlements[sid]
        for building in holding.buildings.values():
            if building.staffed:
                continue
            if realm.population - realm.staff_total(campaign.settlements) - 1 < 1:
                return
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
        sid = nearest_hostile(campaign, realm.key, party.hex)
        if sid is None:
            return
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
    wild = (C.TERRAIN_FOREST, C.TERRAIN_RUINS, C.TERRAIN_ROAD)
    for party in campaign.parties:
        if party.kind != "bandit":
            continue
        options = [pos for pos in campaign.world.neighbours(party.hex)
                   if campaign.world.terrain(pos) in wild and
                   campaign.world.is_passable(pos)]
        if options:
            party.move_to(campaign.rng.choice(options))
            campaign._scan_contacts_for(party)
