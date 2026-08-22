"""Versioned JSON representation of every playable campaign field."""
from . import constants as C
from .calendar import Calendar
from .rng import RNG
from .world import World
from .settlements import Holding, Building, Order
from .units import Unit
from .realm import Realm
from .parties import Party

SCHEMA_VERSION = C.SAVE_VERSION

def _unit(u):
    return {"id":u.id,"name":u.name,"realm":u.realm,"origin":u.origin,"age":u.age,
            "stats":dict(u.stats),"talents":list(u.talents),"kit":u.kit,"xp":u.xp,
            "seasoning":u.seasoning,"wounds":list(u.wounds),"battle_wounds":list(u.battle_wounds),
            "stun_until":u.stun_until,"alive":u.alive,"is_hero":u.is_hero,"is_heir":u.is_heir,
            "max_hit_points":u.max_hit_points,"current_hit_points":u.current_hit_points,
            "shaken":u.shaken}
def _battle(b):
    return {"attacker":b.attacker.pid,"defender":b.defender.pid,"assault":b.assault,
            "sides":b.sides,"side_of":{str(k):v for k,v in b.side_of.items()},
            "positions":{str(k):v for k,v in b.positions.items()},"canvas":{f"{q},{r}":v for (q,r),v in b.canvas.items()},
            "stun_until":{str(k):v for k,v in b.stun_until.items()},"alive":{str(k):v for k,v in b.alive.items()},"ap":{str(k):v for k,v in b.ap.items()},"round":b.round,"turn_side":b.turn_side,"winner":b.winner,"log":b.log,"contact_terrain":b.contact_terrain}
def to_state_dict(c):
    return {"version":SCHEMA_VERSION,"seed":c.seed,"calendar":c.calendar.snapshot(),"turn":c.turn,"ended":c.ended,"game_over":c.ended,"end_reason":c.end_reason,"notes":list(c.notes),"rng":list(c.rng.getstate()),
            "world":{"width":c.world.width,"height":c.world.height,"grid":{f"{q},{r}":t for (q,r),t in c.world.grid.items()},"crossings":{f"{q},{r}":v for (q,r),v in c.world.crossings.items()}},
            "settlements":[h.snapshot() for h in sorted(c.settlements.values(),key=lambda x:x.id)],
            "realms":[r.snapshot() for _,r in sorted(c.realms.items())],"units":[_unit(u) for _,u in sorted(c.units.items())],
            "parties":[p.snapshot() for p in c.parties],"pending_battles":[_battle(b) for b in c.pending_battles]}

def _required(state):
    if not isinstance(state,dict): raise ValueError("save is not a JSON object")
    if state.get("version") != SCHEMA_VERSION: raise ValueError(f"unsupported save version: {state.get('version')!r}; expected {SCHEMA_VERSION}")
    for key in ("seed","calendar","turn","world","settlements","realms","units","parties","rng"):
        if key not in state: raise ValueError(f"save is missing: {key}")

def from_state_dict(state):
    _required(state)
    from .campaign import Campaign
    c=Campaign.__new__(Campaign); c.seed=int(state["seed"]); c.rng=RNG(c.seed); c.rng.restore_state(tuple(state["rng"])); c.calendar=Calendar.from_snapshot(state["calendar"]); c.turn=state["turn"]; c.ended=bool(state.get("ended",False)); c.end_reason=state.get("end_reason",""); c.notes=list(state.get("notes",[])); c.pending_battles=[]
    wd=state["world"]; c.world=World(wd["width"],wd["height"])
    for key,t in wd["grid"].items(): q,r=(int(x) for x in key.split(",")); c.world.set_terrain((q,r),t)
    for key,v in wd.get("crossings",{}).items(): q,r=(int(x) for x in key.split(",")); c.world.crossings[(q,r)]=v
    c.settlements={}
    for item in state["settlements"]:
        h=Holding(item["id"],item["name"],tuple(item["hex"]),item["size"],item.get("owner")); c.settlements[h.id]=h
        for kind,meta in item.get("buildings",{}).items(): h.buildings[kind]=Building(kind,meta.get("staffed",False))
    c.units={}
    for item in state["units"]:
        u=Unit(item["id"],item["name"],stats=item["stats"],talents=item["talents"],origin=item.get("origin","the road"),age=item.get("age",18),kit=item.get("kit","light"),realm=item.get("realm"),is_hero=item.get("is_hero",False)); u.xp=item.get("xp",0); u.seasoning=item.get("seasoning",0); u.wounds=list(item.get("wounds",[])); u.battle_wounds=list(item.get("battle_wounds",[])); u.stun_until=item.get("stun_until"); u.alive=item.get("alive",True); u.is_heir=item.get("is_heir",False); u.shaken=item.get("shaken",False); u.max_hit_points=item.get("max_hit_points",u.max_hit_points); u.current_hit_points=item.get("current_hit_points",u.max_hit_points); c.units[u.id]=u
    c.realms={}
    for item in state["realms"]:
        r=Realm(item["key"],item["name"],item.get("is_player",False),tuple(item.get("color",(0,0,0)))); r.gold=item["gold"]; r.wheat=item["wheat"]; r.population=item["population"]; r.hero=item.get("hero"); r.heir=item.get("heir"); r.unit_ids=set(item.get("unit_ids",[])); r.settlement_ids=list(item.get("settlement_ids",[])); r.morale=item.get("morale",C.MORALE_START); r.destroyed=item.get("destroyed",False); r.orders=[]
        for o in item.get("orders",[]): r.orders.append(Order(o["kind"],o.get("kind_data"),o.get("months",1),o.get("settlement_id"),o.get("unit_id"),o.get("focus")))
        c.realms[r.key]=r
    c.parties=[]
    for item in state["parties"]:
        p=Party(item["pid"],item["kind"],item.get("realm"),tuple(item["hex"]),item.get("unit_ids",[]),item.get("settlement_id")); p.mp=item.get("mp",0); p.road_bonus=item.get("road_bonus",False); c.parties.append(p)
    c.player=c.realms[C.PLAYER_REALM_KEY]
    from .battle import Battle
    parties={p.pid:p for p in c.parties}
    for data in state.get("pending_battles",[]):
        b=Battle(c,parties[data["attacker"]],parties[data["defender"]],data.get("assault",False)); b.sides={k:list(v) for k,v in data["sides"].items()}; b.side_of={int(k):v for k,v in data["side_of"].items()}; b.positions={int(k):tuple(v) for k,v in data["positions"].items()}; b.canvas={tuple(int(x) for x in k.split(",")):v for k,v in data["canvas"].items()}; b.stun_until={int(k):v for k,v in data.get("stun_until",{}).items()}; b.alive={int(k):bool(v) for k,v in data.get("alive",{}).items()}; b.ap={int(k):v for k,v in data.get("ap",{}).items()}; b.round=data.get("round",1); b.turn_side=data.get("turn_side","attacker"); b.winner=data.get("winner"); b.log=list(data.get("log",[])); c.pending_battles.append(b)
    return c
