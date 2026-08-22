# Total Battle Brothers - all design constants in one place.
# UI and tests must import numbers from here; nothing lives scattered.

# ---------------------------------------------------------------------------
# Calendar: 13 months of 4 weeks == 52 weeks == 1 year. One campaign turn == 1 month.
# ---------------------------------------------------------------------------
MONTHS_PER_YEAR = 13
WEEKS_PER_MONTH = 4
WEEKS_PER_YEAR = MONTHS_PER_YEAR * WEEKS_PER_MONTH  # 52
MONTH_NAMES = [
    "Frost", "Hoar", "Mud", "Rain", "Sowing", "Green",
    "Sun", "Heat", "Harvest", "Wine", "Hunt", "Slaughter", "Dark",
]

# ---------------------------------------------------------------------------
# Campaign world map
# ---------------------------------------------------------------------------
MAP_WIDTH = 46      # campaign hexes (axial q)
MAP_HEIGHT = 34     # campaign hexes (axial r)
# Terrain codes (also used by the battle transfer step).
TERRAIN_PLAIN = "plain"
TERRAIN_WOODS = "woods"
TERRAIN_HILLS = "hills"
TERRAIN_RIVER = "river"    # ford
TERRAIN_WATER = "water"    # impassable lakes / sea
TERRAIN_WASTE = "waste"    # barren land, cannot host a new village
TERRAIN_VILLAGE = "village"  # battle-map only: buildings on a settlement tile

# Movement cost in movement points to enter each terrain type.
# None means impassable. Crossing the ~46-wide map at base 6 MP mountains,
# average cost ~1.5, takes many months.
MOVE_COST = {
    TERRAIN_PLAIN: 1,
    TERRAIN_WOODS: 2,
    TERRAIN_HILLS: 3,
    TERRAIN_RIVER: 2,
    TERRAIN_WATER: None,
    TERRAIN_WASTE: 2,
    TERRAIN_VILLAGE: 1,
}
CAMPAIGN_MOVEMENT_POINTS = 6  # march MP restored each month for field parties

# Terrain draw/dither weights for world generation (relative).
WG_HILL_WEIGHT = 1.2
WG_WOOD_WEIGHT = 1.0
WG_WASTE_WEIGHT = 1.35

# Battle map radius: how far the battle hex patch reaches around the contact hex.
BATTLE_RADIUS = 3

# ---------------------------------------------------------------------------
# Talents (locked pool). Rolled 3 per warrior. They are NOT flat bonuses;
# they select which stat gains are kept when training OR fighting.
# ---------------------------------------------------------------------------
TALENT_POOL = [
    "swords", "spears", "bows", "toughness",
    "strength", "wits", "sight", "resolve",
]
NUM_TALENTS = 3
# Talent -> stat gains each talent keeps.
TALENT_STATS = {
    "swords":     ["melee", "initiative"],
    "spears":     ["melee", "fatigue"],
    "bows":       ["ranged", "initiative"],
    "toughness":  ["toughness", "resolve"],
    "strength":   ["melee", "toughness"],
    "wits":       ["initiative", "ranged"],
    "sight":      ["ranged", "melee"],
    "resolve":    ["resolve", "toughness"],
}
STATS = ["melee", "ranged", "toughness", "fatigue", "resolve", "initiative"]
# Conditioning/campaign channels that everyone keeps regardless of talent:
# the body remembers marching (fatigue) and war hardens nerve (resolve).
# Everything else stays strictly talent-gated, so a bow-gifted scout never
# improves melee from training.
TRAIN_CONDITIONING_STAT = "fatigue"
XP_CONDITIONING_STAT = "resolve"

# Stat gain points per training/fighting gain; diminishing via seasoning.
GAIN_POINTS_PER_GAIN = 6
TRAIN_CONDITIONING_SHARE = 1  # of GAIN_POINTS always to fatigue when training
XP_CONDITIONING_SHARE = 1     # of GAIN_POINTS always to resolve from combat
# diminishing: points_for(seasoning) = round(raw / (1 + seasoning * DIMINISH))
DIMINISH_FACTOR = 0.35

# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------
COMPANY_CAP = 12          # named warriors that may march with the hero
BATTLE_SIDE_CAP = 16      # never mass blobs

STAT_MIN = 15
STAT_MAX = 70
RECRUIT_GOLD = 10
RECRUIT_WHEAT = 1
RECRUIT_EXPERIENCE_PTS_PER_ORDER = 0  # recruits roll stats; XP only from combat

UPKEEP_GOLD_PER_UNIT = 1
UPKEEP_WHEAT_PER_UNIT = 1

# ---------------------------------------------------------------------------
# Kits (gear as kits, not an inventory puzzle)
# tier 0 = 'poor' is the default starting kit and costs nothing.
# Each kit has months, gold, wheat, building requirement and stat modifiers.
# Diminishing returns: the stat bumps grow sub-linearly while cost jumps.
# ---------------------------------------------------------------------------
KIT_POOR = "poor"
KITS = {
    KIT_POOR: dict(months=0, gold=0, wheat=0, need=None, name="Patchwork",
                   mods=dict()),
    "light": dict(months=1, gold=6, wheat=2, need=None, name="Light & blade",
                  mods=dict(melee=1, fatigue=2)),
    "militia": dict(months=2, gold=12, wheat=3, need=None, name="Militia kit",
                    mods=dict(melee=2, toughness=2)),
    "bow": dict(months=2, gold=10, wheat=3, need="bowyer", name="Bow kit",
                mods=dict(ranged=3, initiative=1)),
    "heavy": dict(months=3, gold=24, wheat=6, need="smithy",
                  name="Heavy plate", mods=dict(melee=3, toughness=4)),
    "two_hand": dict(months=4, gold=30, wheat=8, need="smithy",
                     name="Two-handed", mods=dict(melee=5, toughness=3)),
    "heavy_bow": dict(months=3, gold=28, wheat=6, need="bowyer",
                      name="Longbow heavies", mods=dict(ranged=4, toughness=2)),
}
KIT_ARMOUR = {"light": 2, "militia": 3, "heavy": 5, "two_hand": 5, "heavy_bow": 5,
              "bow": 1, KIT_POOR: 0}
KIT_SHIELD = {"militia": 1, "heavy": 1, KIT_POOR: 0}
KIT_IS_BOW = {"bow": 1, "heavy_bow": 1}

# ---------------------------------------------------------------------------
# Buildings. Locked roster. Each entry:
#   gold, wheat (one-off build cost), months, staff (population when opened),
#   upkeep (gold/month when staffed), effect (concrete effect),
#   req_size (minimum settlement size that may host it).
# A profession nobody staffs grants no effect.
# ---------------------------------------------------------------------------
BUILDING_FARM = "farm"
BUILDING_GRANARY = "granary"
BUILDING_MARKET = "market"
BUILDING_MILITIA_HALL = "militia_hall"
BUILDING_TRAINING_YARD = "training_yard"
BUILDING_SMITHY = "smithy"
BUILDING_BOWYER = "bowyer"
BUILDING_WALLS = "walls"
BUILDING_KEEP = "keep"
BUILDING_CHAPEL = "chapel"
BUILDING_ROSTER = [
    BUILDING_FARM, BUILDING_GRANARY, BUILDING_MARKET, BUILDING_MILITIA_HALL,
    BUILDING_TRAINING_YARD, BUILDING_SMITHY, BUILDING_BOWYER,
    BUILDING_WALLS, BUILDING_KEEP, BUILDING_CHAPEL,
]
BUILDINGS = {
    BUILDING_FARM: dict(gold=20, wheat=5, months=2, upkeep=1, staff=1,
                        effect="+7 wheat each month", req=None),
    BUILDING_GRANARY: dict(gold=15, wheat=1, months=2, upkeep=1, staff=1,
                           effect="preserves food: +3 wheat",
                           req=None),
    BUILDING_MARKET: dict(gold=25, wheat=2, months=2, upkeep=2, staff=1,
                          effect="+10 gold", req="town"),
    BUILDING_MILITIA_HALL: dict(gold=15, wheat=1, months=1, upkeep=1, staff=1,
                                effect="+3 garrison capacity",
                                req=None),
    BUILDING_TRAINING_YARD: dict(gold=40, wheat=5, months=3, upkeep=2, staff=1,
                                 effect="2 training slots",
                                 req="town"),
    BUILDING_SMITHY: dict(gold=50, wheat=8, months=3, upkeep=2, staff=1,
                          effect="allows heavy plate kits",
                          req=None),
    BUILDING_BOWYER: dict(gold=30, wheat=4, months=2, upkeep=2, staff=1,
                          effect="allows quality bow kits",
                          req=None),
    BUILDING_WALLS: dict(gold=30, wheat=4, months=2, upkeep=1, staff=1,
                         effect="+5 garrison cap, +defence on assault",
                         req="town"),
    BUILDING_KEEP: dict(gold=60, wheat=10, months=4, upkeep=2, staff=1,
                        effect="+4 garrison cap, realm morale +3",
                        req="town"),
    BUILDING_CHAPEL: dict(gold=20, wheat=3, months=2, upkeep=1, staff=1,
                          effect="morale +4, births +0.4%",
                          req=None),
}
# Slot limits per settlement size in the builder.
SIZE_ORDER = ["village", "town", "city"]
BUILDING_SLOTS = {"village": 4, "town": 7, "city": 10}
MILITIA_HALL_CAP = 3
WALLS_CAP = 5
KEEP_CAP = 4
TRAINING_SLOTS_PER_YARD = 2
GRANARY_FOOD = 3
FARM_FOOD = 7
MARKET_GOLD = 10
KEEP_MORALE = 3
CHAPEL_MORALE = 4
CHAPEL_BIRTH = 0.004

# ---------------------------------------------------------------------------
# Settlement sizes / development / founding
# ---------------------------------------------------------------------------
SIZE_V = "village"
SIZE_T = "town"
SIZE_C = "city"
POP_CAP = {SIZE_V: 40, SIZE_T: 80, SIZE_C: 130}
GARRISON_BASE = {SIZE_V: 4, SIZE_T: 6, SIZE_C: 8}
DEVELOP_COST = {
    (SIZE_V, SIZE_T): dict(gold=40, wheat=10, months=3),
    (SIZE_T, SIZE_C): dict(gold=100, wheat=25, months=6),
}
FOUND_COST = dict(gold=50, wheat=15, months=3, pop=2)
FOUND_REQUIRED = {SIZE_V: 2}  # staff needed when the village rises

# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------
BASE_GOLD_INCOME = 0        # grim: only markets/keep make gold
POP_FOOD_PER_UNIT = 0.1     # wheat per population point per month
STARVATION_MORALE = -8
STARVATION_POP = -1         # people per unit of shortfall (per shortfall point)
UNPAID_MORALE = -4
BIRTH_RATE = 0.02
IMMIG_RATE = 0.02
IMMIG_FOOD_BONUS = 6        # +% immigrants per surplus wheat point of realm
MORALE_GROWTH_MOD = 0.5     # growth scaled by (morale/100)
MORALE_DROP_START = 70      # morale at game start
MORALE_HERO_LOST = -20
MORALE_HEIR_TEXT = "heir takes the crown"
START_GOLD_BASE, START_GOLD_SPREAD = 200, 80
START_WHEAT_BASE, START_WHEAT_SPREAD = 90, 40
START_POP_MIN, START_POP_ADD = 16, 12

# ---------------------------------------------------------------------------
# Morale in battle: morale changes HIT CHANCE only. No routs, no morale-lock.
# ---------------------------------------------------------------------------
MORALE_HIT_FACTOR = 0.25  # (morale-50)/100 * this added to hit chance

# ---------------------------------------------------------------------------
# Combat formulas (see battle.py)
# ---------------------------------------------------------------------------
BATTLE_BASE_HIT = 0.50
BATTLE_HIT_PER_STAT = 0.006
BATTLE_DEF_PER_TOUGH = 0.005
BATTLE_DEF_PER_SHIELD = 0.08
BATTLE_TERRAIN_MOD = {
    TERRAIN_PLAIN: 0.0,
    TERRAIN_WOODS: -0.06,    # attacker's melee/strike into cover
    TERRAIN_HILLS: 0.02,     # elevation advantage for the higher side
    TERRAIN_RIVER: -0.08,    # choke the ford
    TERRAIN_VILLAGE: -0.10,  # buildings give cover
    TERRAIN_WASTE: 0.0,
    TERRAIN_WATER: -0.5,     # unreachable-ish marker, never fought on
}
BATTLE_RANGED_PENALTY = 0.10  # per step beyond the first
BATTLE_RANGED_MIN = 0.10
BATTLE_MIN_HIT = 0.05
BATTLE_MAX_HIT = 0.95
BATTLE_MELEE_DMG = 8
BATTLE_MELEE_STR_SCALE = 0.12
BATTLE_RANGED_DMG = 6
BATTLE_RANGED_STA_SCALE = 0.08
BATTLE_ARMOUR_REDUCTION = {  # by kit
    "poor": 0, "light": 2, "military": 3, "bow": 2,
    "heavy": 5, "two_hand": 4, "heavy_bow": 5,
}
BATTLE_STUN_CHANCE = 0.30
BATTLE_STUN_THRESH = 0.8   # damage relative to toughness
BATTLE_PERM_CHANCE = 0.40
BATTLE_DEATH_MULT = 1.6    # damage > toughness*mult -> death likely
XP_PARTICIPATION = 2
XP_HIT = 4
XP_KILL = 12
XP_PER_GAIN = 12         # combat experience points per talent-gated gain
BATTLE_STEPS_PER = 1  # moves per action point

# Wound catalogue
WOUNDS = {
    "gash": "temporary", "bruise": "temporary",
    "shattered arm": "permanent", "maimed leg": "permanent",
    "lost eye": "permanent", "broken ribs": "temporary",
}
WOUND_STAT_EFFECT = {
    "gash": dict(melee=-2), "bruise": dict(toughness=-1),
    "shattered arm": dict(melee=-5, fatigue=-2),
    "maimed leg": dict(initiative=-4),
    "lost eye": dict(ranged=-6),
    "broken ribs": dict(fatigue=-3, resolve=-2),
}

# ---------------------------------------------------------------------------
# Worldgen placement budgets
# ---------------------------------------------------------------------------
NUM_DUCHIES = 5                      # player + 4 AI
PLAYER_REALM_KEY = 0
MIN_NEUTRALS = 3
MAX_NEUTRALS = 6
MIN_BANDITS = 2
MAX_BANDITS = 4
BANDIT_PARTY_SIZE = (4, 9)
HERO_COMPANY_SIZE = (4, 7)           # hero + this many field warriors
GARRISON_EXTRA = (3, 6)
AI_TARGET_DECAY = 3                  # AI rethink target every N months
AI_DEVELOP_PRIORITY = [BUILDING_FARM, BUILDING_MARKET, BUILDING_MILITIA_HALL,
                       BUILDING_TRAINING_YARD, BUILDING_SMITHY,
                       BUILDING_BOWYER, BUILDING_GRANARY, BUILDING_WALLS,
                       BUILDING_KEEP, BUILDING_CHAPEL]

# ---------------------------------------------------------------------------
# Win / lose
# ---------------------------------------------------------------------------
HEIR_RAISE_COST_TAG = "council raises a new commander"  # morale drop only
MORALE_RAISE_COMMANDER = -15

# ---------------------------------------------------------------------------
# Defaults for the out-of-the-box new game
# ---------------------------------------------------------------------------
DEFAULT_SEED = 734102

# ---------------------------------------------------------------------------
# Save/load
# ---------------------------------------------------------------------------
SAVE_DIR = "saves"
SAVE_EXT = ".tbb"