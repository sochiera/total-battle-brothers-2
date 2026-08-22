"""JSON save schema for a complete campaign (no pickling).

A GameState dict carries every piece of living rules-state: seed and random
stream, calendar, world grid, holdings and buildings, realms and resources,
named units with talents/wounds/kit/XP, orders still in flight, parties,
heir, and date. Because it is plain JSON the file is inspectable, portable and
cannot smuggle an arbitrary code object into a loader.

`persistence` builds on these two functions for the named-slot layer.
"""
from . import constants as C
from .calendar import Calendar
from .rng import RNG
from .settlements import Holding, Building, Order
from .units import Unit
from .realm import Realm
from .parties import Party
from .world import World
from .terrain import NEIGHBOURS

SCHEMA_VERSION = 1


def _pack_rng(state):
    """random.Random.getstate() -> JSON-friendly structure."""
    return list(state)


def _pack_buildings(buildings):
    return {kind: {"staffed": b.staffed} for kind, b in buildings.items()}


def _pack_orders(orders):
    return [{"kind": o.kind, "kind_data": o.kind_data, "months": o.months,
             "settlement_id": o.settlement_id, "unit_id": o.unit_id}
            for o in orders]


def _pack_unit(u):
    return {
        "id": u.id, "name": u.name, "realm": u.realm,
        "stats": dict(u.stats), "talents": list(u.talents), "kit": u.kit,
        "xp": u.xp, "seasoning": u.seasoning,
        "wounds": list(u.wounds), "battle_wounds": list(u.battle_wounds),
        "stun_until": u.stun_until,
        "alive": u.alive, "is_hero": u.is_hero, "is_heir": u.is_heir,
        "applied_gains": getattr(u, "_applied_gains", 0),
    }


def _pack_realm(rr):
    return {
        "key": rr.key, "name": rr.name, "is_player": rr.is_player,
        "color": list(rr.color), "gold": rr.gold, "wheat": rr.wheat,
        "population": rr.population, "hero": rr.hero, "heir": rr.heir,
        "unit_ids": sorted(rr.unit_ids),
        "settlement_ids": list(rr.settlement_ids),
        "morale": rr.morale, "destroyed": rr.destroyed,
        "orders": _pack_orders(rr.orders),
    }


def _pack_holding(h):
    return {"id": h.id, "name": h.name, "hex": list(h.hex), "size": h.size,
            "owner": h.owner, "buildings": _pack_buildings(h.buildings)}


def _pack_party(p):
    return {"pid": p.pid, "kind": p.kind, "realm": p.realm, "hex": list(p.hex),
            "unit_ids": list(p.unit_ids),
            "settlement_id": p.settlement_id, "mp": p.mp}


def to_state_dict(campaign):
    """Plain JSON-ready dict describing the whole campaign."""
    return {
        "version": SCHEMA_VERSION,
        "seed": campaign.seed,
        "calendar": list(campaign.calendar.snapshot()),
        "turn": campaign.turn,
        "ended": campaign.ended,
        "end_reason": campaign.end_reason,
        "rng": _pack_rng(campaign.rng.getstate()),
        "world": {"width": campaign.world.width,
                  "height": campaign.world.height,
                  "grid": {("%d,%d" % (q, r)): terr
                           for (q, r), terr in campaign.world.grid.items()}},
        "settlements": [_pack_holding(h)
                        for h in sorted(campaign.settlements.values(),
                                        key=lambda h: h.id)],
        "realms": [_pack_realm(campaign.realms[k])
                   for k in sorted(campaign.realms)],
        "units": [_pack_unit(campaign.units[u])
                  for u in sorted(campaign.units)],
        "parties": [_pack_party(p) for p in campaign.parties],
    }


def from_state_dict(state):
    """Rebuild a live Campaign from a GameState dict."""
    c = _bare_campaign(state["seed"])
    c.turn = state["turn"]
    c.ended = state["ended"]
    c.end_reason = state["end_reason"]
    c.calendar = Calendar(*state["calendar"])

    w = state["world"]
    world = World(w["width"], w["height"])
    for (q, r), terr in _iter_grid(state):
        world.set_terrain((q, r), terr)
    c.world = world

    c.settlements = {}
    for s in state["settlements"]:
        h = Holding(s["id"], s["name"], tuple(s["hex"]), s["size"], s["owner"])
        for kind, meta in s["buildings"].items():
            b = Building(kind)
            b.staffed = meta["staffed"]
            h.buildings[kind] = b
        c.settlements[h.id] = h

    c.units = {}
    for u in state["units"]:
        if u.get("stun_until") is not None:
            stun = tuple(u["stun_until"]) if not isinstance(u["stun_until"], list) else tuple(u["stun_until"])
        else:
            stun = None
        unit = Unit(u["id"], u["name"], u["stats"]["melee"],
                    u["stats"]["ranged"], u["stats"]["toughness"],
                    u["stats"]["fatigue"], u["stats"]["resolve"],
                    u["stats"]["initiative"], u["talents"], kit=u["kit"],
                    realm=u["realm"])
        unit.stats = dict(u["stats"])
        unit.xp = u["xp"]
        unit.seasoning = u["seasoning"]
        unit.wounds = list(u["wounds"])
        unit.battle_wounds = list(u["battle_wounds"])
        unit.stun_until = stun
        unit.alive = u["alive"]
        unit.is_hero = u["is_hero"]
        unit.is_heir = u["is_heir"]
        unit._applied_gains = u.get("applied_gains", 0)
        c.units[unit.id] = unit

    c.realms = {}
    for rr in state["realms"]:
        realm = Realm(rr["key"], rr["name"], is_player=rr["is_player"],
                      color=tuple(rr["color"]))
        realm.gold = rr["gold"]
        realm.wheat = rr["wheat"]
        realm.population = rr["population"]
        realm.hero = rr["hero"]
        realm.heir = rr["heir"]
        realm.unit_ids = set(rr["unit_ids"])
        realm.settlement_ids = list(rr["settlement_ids"])
        realm.morale = rr["morale"]
        realm.destroyed = rr["destroyed"]
        realm.orders = []
        for o in rr["orders"]:
            realm.orders.append(Order(o["kind"], o["kind_data"], o["months"],
                                      settlement_id=o["settlement_id"],
                                      unit_id=o["unit_id"]))
        c.realms[rr["key"]] = realm

    c.parties = []
    for pp in state["parties"]:
        party = Party(pp["pid"], pp["kind"], pp["realm"], tuple(pp["hex"]),
                      list(pp["unit_ids"]), settlement_id=pp["settlement_id"])
        party.mp = pp["mp"]
        c.parties.append(party)

    c.player = c.realms[C.PLAYER_REALM_KEY]
    c.rng.restore_state(tuple(state["rng"]))
    return c


def _iter_grid(state):
    out = []
    for key, terr in state["world"]["grid"].items():
        q, r = key.split(",")
        out.append(((int(q), int(r)), terr))
    return out


def _bare_campaign(seed):
    """A bare Campaign object before worldgen runs (no random draws)."""
    from .campaign import Campaign as C
    obj = C.__new__(C)
    obj.seed = int(seed)
    obj.rng = RNG(seed)
    obj.calendar = Calendar()
    obj.turn = 0
    obj.ended = False
    obj.end_reason = ""
    obj.pending_battles = []
    obj.notes = []
    return obj