"""The one source of truth for Total Battle Brothers numbers.

Rules modules import this file; the presentation layer never invents game
numbers.  Names are deliberately plain: this is a historical medieval
sandbox, not a fantasy setting.
"""

MONTHS_PER_YEAR = 13
WEEKS_PER_MONTH = 4
WEEKS_PER_YEAR = 52
MONTH_LABELS = tuple("I II III IV V VI VII VIII IX X XI XII XIII".split())
SEASON_WINTER = "winter"
SEASON_OPEN = "open months"
SEASON_HARVEST = "harvest"
SEASONS = (SEASON_WINTER, SEASON_OPEN, SEASON_HARVEST)
SEASON_BY_MONTH = {0: SEASON_WINTER, 1: SEASON_WINTER, 2: SEASON_OPEN,
                   3: SEASON_OPEN, 4: SEASON_OPEN, 5: SEASON_OPEN,
                   6: SEASON_OPEN, 7: SEASON_HARVEST, 8: SEASON_HARVEST,
                   9: SEASON_HARVEST, 10: SEASON_OPEN, 11: SEASON_OPEN,
                   12: SEASON_WINTER}
SEASON_WHEAT_MULTIPLIER = {SEASON_WINTER: 0.55, SEASON_OPEN: 1.0,
                           SEASON_HARVEST: 1.65}
SEASON_MARCH_COST = {SEASON_WINTER: 1, SEASON_OPEN: 0,
                     SEASON_HARVEST: 0}
SEASON_RAID_PRESSURE = {SEASON_WINTER: 2, SEASON_OPEN: 0,
                        SEASON_HARVEST: 1}

MAP_WIDTH, MAP_HEIGHT = 64, 48
# Crossing the long axis on the cheapest legal path costs at least this many
# movement points.  This is deliberately a campaign-scale journey, not a
# single-month stroll.
LONG_AXIS_MIN_MP = 45
TERRAIN_PLAINS = "plains"
TERRAIN_FOREST = "forest"
TERRAIN_HILLS = "hills"
TERRAIN_RIVER = "river"
TERRAIN_ROAD = "road"
TERRAIN_VILLAGE = "village"
TERRAIN_RUINS = "ruins"
TERRAIN_MOUNTAIN = "mountain"
TERRAIN_MARSH = "marsh"
TERRAIN_FARMLAND = "farmland"
TERRAIN_COAST = "coast"
TERRAIN_FORD = "ford"
TERRAIN_HIGHLAND_FARM = "highland_farm"
TERRAIN_FOREST_TRACK = "forest_track"
TERRAIN_RUINED_HOLD = "ruined_hold"
CAMPAIGN_TERRAINS = (TERRAIN_PLAINS, TERRAIN_FOREST, TERRAIN_HILLS,
                     TERRAIN_RIVER, TERRAIN_ROAD, TERRAIN_VILLAGE,
                     TERRAIN_RUINS, TERRAIN_MOUNTAIN, TERRAIN_MARSH,
                     TERRAIN_FARMLAND, TERRAIN_COAST, TERRAIN_FORD,
                     TERRAIN_HIGHLAND_FARM, TERRAIN_FOREST_TRACK,
                     TERRAIN_RUINED_HOLD)
FOUNDABLE_TERRAINS = frozenset((TERRAIN_PLAINS, TERRAIN_RUINS,
                                TERRAIN_FARMLAND, TERRAIN_HIGHLAND_FARM,
                                TERRAIN_RUINED_HOLD))
RIVER_CROSSINGS = ("ford", "bridge")
MOUNTAIN_PASS = "pass"
PASS_MOVE_COST = 2
MOVE_COST = {TERRAIN_PLAINS: 1, TERRAIN_FOREST: 2, TERRAIN_HILLS: 2,
             TERRAIN_RIVER: None, TERRAIN_ROAD: 1, TERRAIN_VILLAGE: 1,
             TERRAIN_RUINS: 1, TERRAIN_MOUNTAIN: None, TERRAIN_MARSH: 3,
             TERRAIN_FARMLAND: 1, TERRAIN_COAST: 1,
             TERRAIN_FORD: 1, TERRAIN_HIGHLAND_FARM: 2,
             TERRAIN_FOREST_TRACK: 1, TERRAIN_RUINED_HOLD: 1}
CAMPAIGN_MOVEMENT_POINTS = 4
ROAD_MOVEMENT_BONUS = 1
STABLES_MOVE_BONUS = 1

NUM_DUCHIES = 6
PLAYER_REALM_KEY = 0
NUM_ROBBER_BANDS = 3
MIN_NEUTRALS, MAX_NEUTRALS = 4, 8
BANDIT_PARTY_SIZE = (3, 7)

SIZE_V, SIZE_T, SIZE_C = "village", "town", "city"
SIZE_ORDER = (SIZE_V, SIZE_T, SIZE_C)
POP_CAP = {SIZE_V: 40, SIZE_T: 80, SIZE_C: 130}
BUILDING_SLOTS = {SIZE_V: 4, SIZE_T: 7, SIZE_C: 10}
GARRISON_BASE = {SIZE_V: 4, SIZE_T: 6, SIZE_C: 8}

BUILDING_FARM = "farm"
BUILDING_GRANARY = "granary"
BUILDING_MARKET = "market"
BUILDING_MILITIA_HALL = "militia_hall"
BUILDING_DRILL_YARD = "drill_yard"
BUILDING_SMITHY = "smithy"
BUILDING_FLETCHER = "fletcher"
BUILDING_STABLES = "stables"
BUILDING_WALLS = "palisade_walls"
BUILDING_KEEP = "keep"
BUILDING_ROSTER = (BUILDING_FARM, BUILDING_GRANARY, BUILDING_MARKET,
                   BUILDING_MILITIA_HALL, BUILDING_DRILL_YARD,
                   BUILDING_SMITHY, BUILDING_FLETCHER, BUILDING_STABLES,
                   BUILDING_WALLS, BUILDING_KEEP)
BUILDINGS = {
    BUILDING_FARM: dict(gold=20, wheat=5, months=2, staff=1, upkeep=1,
                        effect="food production", req=None),
    BUILDING_GRANARY: dict(gold=15, wheat=1, months=2, staff=1, upkeep=1,
                           effect="reduces spoilage", req=None),
    BUILDING_MARKET: dict(gold=25, wheat=2, months=2, staff=1, upkeep=2,
                          effect="poor trade", req=SIZE_T),
    BUILDING_MILITIA_HALL: dict(gold=15, wheat=1, months=1, staff=1,
                                upkeep=1, effect="+3 garrison", req=None),
    BUILDING_DRILL_YARD: dict(gold=40, wheat=5, months=3, staff=1, upkeep=2,
                              effect="melee/fatigue training", req=SIZE_T),
    BUILDING_SMITHY: dict(gold=50, wheat=8, months=3, staff=1, upkeep=2,
                          effect="heavy kits and melee practice", req=None),
    BUILDING_FLETCHER: dict(gold=30, wheat=4, months=2, staff=1, upkeep=2,
                            effect="bows and ranged practice", req=None),
    BUILDING_STABLES: dict(gold=35, wheat=6, months=3, staff=1, upkeep=2,
                           effect="fatigue training and +1 march", req=None),
    BUILDING_WALLS: dict(gold=30, wheat=4, months=2, staff=1, upkeep=1,
                         effect="+5 garrison and cover", req=SIZE_T),
    BUILDING_KEEP: dict(gold=60, wheat=10, months=4, staff=1, upkeep=2,
                        effect="+4 garrison and +3 morale", req=SIZE_T),
}
MILITIA_HALL_CAP, WALLS_CAP, KEEP_CAP = 3, 5, 4
TRAINING_SLOTS_PER_DRILL_YARD = 2
TRAINING_SLOTS_PER_SPECIALIST = 1

DEVELOP_COST = {(SIZE_V, SIZE_T): dict(gold=80, wheat=20, months=4),
                (SIZE_T, SIZE_C): dict(gold=180, wheat=45, months=7)}
DEVELOP_POP_GATE = {(SIZE_V, SIZE_T): 24, (SIZE_T, SIZE_C): 65}
DEVELOP_BUILDING_GATE = {(SIZE_V, SIZE_T): 2, (SIZE_T, SIZE_C): 5}
FOUND_COST = dict(gold=50, wheat=15, months=3, settlers=2)

FARM_BASE_WHEAT = 4
FARM_POP_DIVISOR = 8
SPOILAGE_RATE = 0.20
GRANARY_SPOILAGE_REDUCTION = 0.08
POP_FOOD_PER_MONTH = 0.1
WARRIOR_FOOD_UPKEEP = 1
WARRIOR_GOLD_UPKEEP = 1
BIRTH_RATE = 0.02
IMMIGRATION_RATE = 0.01
MARKET_SELL_WHEAT = 5
MARKET_SELL_GOLD = 2
MARKET_BUY_WHEAT = 2
MARKET_BUY_GOLD = 4
MARKET_TRANSFER_WHEAT = 6
MARKET_TRANSFER_GOLD = 8
MARKET_TRANSFER_RANGE = 12
UNDEFENDED_ROAD_RAID_STEP = 3
RAID_SACK_WHEAT = 6
RAID_SACK_GOLD = 4
RAID_POP_CUT = 2
ASSAULT_DEFENDER_BONUS = 0.12
STARVATION_MORALE = -8
STARVATION_POP = -1
UNPAID_UPKEEP_MORALE = -4
KEEP_MORALE = 3
MORALE_START = 70

COMPANY_CAP = 12  # includes the hero
RECRUIT_COST = dict(gold=10, wheat=2, months=1, population=1)
RECRUIT_GOLD, RECRUIT_WHEAT = 10, 2
KITS = {
    "light": dict(name="Light armour", months=1, gold=6, wheat=2,
                  need=None, mods={"fatigue": 2}, armour=1, shield=False,
                  bow=False),
    "shield_onehander": dict(name="Shield + one-hander", months=2, gold=12,
                              wheat=3, need=None, mods={"melee": 2}, armour=2,
                              shield=True, bow=False),
    "bow": dict(name="Bow", months=2, gold=10, wheat=3, need="fletcher",
                mods={"ranged": 3}, armour=1, shield=False, bow=True),
    "heavy": dict(name="Heavy armour", months=3, gold=24, wheat=6,
                  need="smithy", mods={"melee": 2, "hit_points": 3}, armour=5,
                  shield=False, bow=False),
    "two_hander": dict(name="Two-hander", months=4, gold=30, wheat=8,
                       need="smithy", mods={"melee": 5}, armour=3,
                       shield=False, bow=False),
}
KIT_LIGHT, KIT_SHIELD, KIT_BOW, KIT_HEAVY, KIT_TWO_HAND = tuple(KITS)

STATS = ("melee", "ranged", "hit_points", "fatigue", "resolve")
STAT_MIN, STAT_MAX = 15, 70
TALENT_POOL = ("blade", "bow", "vitality", "endurance", "courage", "scouting")
NUM_TALENTS = 3
TALENT_STATS = {
    "blade": ("melee",), "bow": ("ranged",), "vitality": ("hit_points",),
    "endurance": ("fatigue",), "courage": ("resolve",),
    "scouting": ("ranged", "fatigue"),
}
GAIN_POINTS_PER_GAIN = 6
DIMINISH_FACTOR = 0.35
TRAIN_CONDITIONING_STAT, XP_CONDITIONING_STAT = "fatigue", "resolve"
TRAINING_XP = 0
XP_PARTICIPATION, XP_HIT, XP_KILL, XP_PER_GAIN = 2, 4, 12, 12

BATTLE_WIDTH, BATTLE_HEIGHT = 30, 20
BATTLE_BASE_HIT = 0.50
BATTLE_HIT_PER_STAT = 0.006
BATTLE_DEF_PER_STAT = 0.003
BATTLE_DEF_PER_SHIELD = 0.08
BATTLE_TERRAIN_MOD = {TERRAIN_PLAINS: 0.0, TERRAIN_FOREST: -0.08,
                      TERRAIN_HILLS: 0.04, TERRAIN_RIVER: -0.10,
                      TERRAIN_ROAD: 0.0, TERRAIN_VILLAGE: -0.10,
                      TERRAIN_RUINS: -0.04, TERRAIN_MOUNTAIN: -0.12,
                      TERRAIN_MARSH: -0.06, TERRAIN_FARMLAND: 0.0,
                      TERRAIN_COAST: -0.04, TERRAIN_HIGHLAND_FARM: 0.04,
                      TERRAIN_FOREST_TRACK: -0.02,
                      TERRAIN_RUINED_HOLD: -0.08}
BATTLE_RANGED_PENALTY = 0.10
BATTLE_BLOCKING_TERRAIN = (TERRAIN_FOREST, TERRAIN_HILLS, TERRAIN_RIVER,
                           TERRAIN_MOUNTAIN)
BATTLE_IMPASSABLE_TERRAIN = (TERRAIN_RIVER, TERRAIN_MOUNTAIN)
BATTLE_MIN_HIT, BATTLE_MAX_HIT = 0.05, 0.95
BATTLE_MELEE_DAMAGE, BATTLE_RANGED_DAMAGE = 8, 6
TEMP_WOUND_MONTHS = 3
MORALE_HIT_FACTOR = 0.25
BATTLE_STUN_CHANCE, BATTLE_STUN_THRESHOLD = 0.30, 0.8
BATTLE_PERMANENT_WOUND_CHANCE = 0.40
BATTLE_DEATH_MULTIPLIER = 1.6
WOUNDS = {"gash": "temporary", "bruise": "temporary",
          "shattered arm": "permanent", "maimed leg": "permanent",
          "lost eye": "permanent", "broken ribs": "temporary"}
WOUND_STAT_EFFECT = {
    "gash": {"melee": -2}, "bruise": {"hit_points": -2},
    "shattered arm": {"melee": -5}, "maimed leg": {"fatigue": -4},
    "lost eye": {"ranged": -6}, "broken ribs": {"hit_points": -4, "resolve": -2},
}

MORALE_HEIR_SUCCESSION = -20
MORALE_NEW_COMMANDER = -15
SHAKEN_RESOLVE_CAP = 30
START_ARCHETYPES = {
    "border_count": ((SIZE_V,),),
    "minor_duke": ((SIZE_V, SIZE_T), (SIZE_V, SIZE_T, SIZE_V)),
    "high_duke": ((SIZE_C, SIZE_T, SIZE_V),),
}
START_ARCHETYPE_LABELS = {"border_count": "Border Count",
                          "minor_duke": "Minor Duke",
                          "high_duke": "High Duke"}
DEFAULT_SEED = 734102
SAVE_DIR, SAVE_EXT, SAVE_VERSION = "saves", ".tbb", 3
AI_DEVELOP_PRIORITY = (BUILDING_FARM, BUILDING_GRANARY, BUILDING_MILITIA_HALL,
                       BUILDING_DRILL_YARD, BUILDING_SMITHY, BUILDING_FLETCHER,
                       BUILDING_STABLES, BUILDING_MARKET, BUILDING_WALLS,
                       BUILDING_KEEP)
