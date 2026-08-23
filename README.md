# Total Battle Brothers

Total Battle Brothers is a single-player Linux sandbox about a grim medieval
duchy and its named company. It has no magic, fantasy creatures, scripted
story campaign, or multiplayer. The goal is to outlast every rival ducal line.

## Purpose

A complete, playable first slice: start a seeded campaign from the title
screen, read the world from the window (map, settlements, resources, date),
march your hero company month by month, build and staff holdings, fight
individual-unit hex battles generated from the terrain you stand on, and
save/load the whole campaign — while all game rules stay headless-testable
in `tbb/rules` with zero pygame imports.

## Requirements and launch

Ubuntu 26.04 (or another Linux with Python 3.10+) is required. `run.sh`
creates `.venv` and installs pygame-ce and pytest on its first run:

```sh
./run.sh
```

Equivalent commands are `make run` and `.venv/bin/python3 -m tbb`. If the
machine cannot run `ensurepip`, both `run.sh` and the Makefile retry with a
`--without-pip` virtualenv and install through `pip3 --python`.
The title screen offers New / Load / Quit, a typed seed (empty falls back to 734102)
and a **Generate** button that fills a fresh numeric seed you can still edit;
Enter starts. A seed can also be supplied with `--seed 734102`; `--new-game`
skips the title screen and `--frames 45` is useful for a dummy-video smoke
run:

The reproducible test entry point is `make test`; it uses the same fallback
bootstrap instead of invoking the system Python environment directly.

```sh
make test
```

For the launch smoke, use the fallback-aware launcher:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./run.sh \
  --seed 734102 --new-game --frames 45
```

To inspect the live happy path without a display, render all four main screens
to PNG files:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy ./run.sh \
  --seed 734102 --dump-frames /tmp/tbb-frames
test -s /tmp/tbb-frames/campaign.png
test -s /tmp/tbb-frames/settlement.png
test -s /tmp/tbb-frames/court.png
test -s /tmp/tbb-frames/battle.png
```

For a display-free save check, use the rules-only CLI path:

```sh
./run.sh --save-smoke plan-smoke
test -s saves/plan-smoke.tbb
```

## What works

Each campaign contains a **46×34** painted hex world of clustered biomes:
plains, forest, hills, a coast strip on one edge, marsh, farmland, rivers
with fords and bridges, roads, and a **mountain spine** that blocks travel
except through generated **passes**. Crossing the long axis costs at least 20
movement points, so the world takes months to cross. The world holds **one
player duchy plus five AI duchies**, 4–8 neutral holdings, empty land, and
exactly **three robber bands** camped on or beside ruins. The player starts
as either a border count with one village or a minor duke with two or three
village/town holdings.

One turn is one month. A year has **thirteen four-week months** labelled
I–XIII. A company has at most **12 named people including its living hero**.
Warriors have a name, origin, age, three growth talents, melee, ranged, hit
points, fatigue and resolve. Combat XP and whole-month training grow only
talent-affined stats; death is permanent. **Temporary wounds** (gash, bruise,
broken ribs) mend after three month ticks; permanent wounds (shattered arm,
maimed leg, lost eye) never heal. Stun is battle-only.

The economy uses only wheat and gold. Farms produce food, granaries reduce
spoilage, markets trade explicitly at 5 wheat for 2 gold or 2 wheat for 4
gold, and every staffed building consumes one resident (closing a staffed
building returns the resident). The buildings are:

| Building | Gold | Wheat | Months | Size gate | Effect |
|---|---:|---:|---:|---|---|
| Farm | 20 | 5 | 2 | any | pop-scaled wheat |
| Granary | 15 | 1 | 2 | any | reduces spoilage |
| Market | 25 | 2 | 2 | town | poor explicit trade |
| Militia Hall | 15 | 1 | 1 | any | +3 garrison |
| Drill Yard | 40 | 5 | 3 | town | melee/fatigue training |
| Smithy | 50 | 8 | 3 | any | heavy kits and practice |
| Fletcher | 30 | 4 | 2 | any | bow kits and practice |
| Stables | 35 | 6 | 3 | any | fatigue practice and +1 march |
| Palisade/Walls | 30 | 4 | 2 | town | +5 garrison and cover |
| Keep | 60 | 10 | 4 | town | +4 garrison and +3 morale |

Terrain move costs: plains/road/village/ruins/farmland/coast 1, forest/hills
2, marsh 3, mountain pass 2, rivers only at fords/bridges (1). Founding new
villages is allowed on empty **plains, ruins, or farmland** adjacent to your
own land. Allowed kits are Light armour, Shield + one-hander, Bow, Heavy
armour, and Two-hander. Heavy armour and Two-hander require a staffed
Smithy; Bow requires a staffed Fletcher (no smithy, no heavy plate).
Recruiting costs 10 gold, 2 wheat, one month, and one population. Founding
costs 50 gold, 15 wheat, three months, and two settlers. Village→Town costs
80 gold/20 wheat/four months; Town→City costs 180 gold/45 wheat/seven months.

AI rivals staff their buildings, build by a fixed priority list, recruit,
train, outfit, **found new villages on legal adjacent land**, and march on
weak neutrals or rival seats. Robber bands raid holdings and pick fights with
weaker guards, never with each other.

### Battles

A hostile contact or settlement assault opens an individual-unit **18×13**
hex battle painted from the overworld hex and its neighbours, so forest
fights are mostly woods with clearings, hills show ridges, river contacts
keep a water band with fords, and farmland, marsh, coast, mountain-pass,
village, and ruins contacts each read distinctly. Battles are **side-based**:
act with any number of your warriors (each has 2 AP), then press Space to end
your side and the scripted foe takes its full turn using the same rules —
adjacent melee first, else a legal bow shot, else a step toward you; stunned
warriors are skipped and nothing invents free damage. Movement, melee,
ranged with range 2–3 and a clear line, terrain cover, AP, HP, stun, wounds
and permadeath are all in. **Morale changes hit chance only** — no routs.
Auto-resolve (A) remains the fallback and writes back wounds, deaths,
capture, and succession.

### End states

Court designates or clears an heir. A dead hero with a living heir continues
with the locked morale hit (-20, shaken resolve cap for the company); with no
heir but a town/city the council raises a new commander (-15); no settlements
plus no living hero and no heir is defeat; being the last ruling duchy is
victory. Banners on the campaign map and the Court chronicle make these
visible without reading logs.

### Save/load

Named save slots are JSON files in `saves/` (save schema version 3). They
include the full world grid with crossings, calendar, orders, parties, every
warrior field including remaining temporary-wound months, pending battles
with their exact canvas and RNG state, and the campaign RNG stream. Old
schema versions and corrupt files are reported as readable errors in the
load menu, never a crash.

## Controls

On the campaign map, click a hero token and an adjacent hex to march (the
token tweens between hexes; owned holdings pulse). Use `M` to end the month,
`O` to open the selected settlement, `F` to enter found mode, `B` to enter a
pending battle, `A` to auto-resolve, `C` for Court, and `S`/`L` for
save/load. Arrow keys pan the map. The side panel shows date, wheat, gold,
population, morale, the selected-settlement card, company roster, robber
bands, and the realm chronicle. In battle, click a unit then an adjacent hex
or hostile unit; `Space` ends your side's turn and `A` auto-resolves. The
settlement screen offers building, staffing, recruiting, training, equipping,
market trade, development, and **garrison transfer** (attach garrison
soldiers to the company up to 12, detach non-heroes into the garrison up to
its cap), each with a reason shown when disabled. UI open/close, melee hit,
bow, wound, and death-cry sounds plus looping ambient music are always on
when an audio device exists.

## Demo data and limitations

Seeds, the default 734102 world, generated names, and generated settlement
contents are demo data. Original pixel-art files live in `assets/tiles/`,
`assets/settlements/`, `assets/banners/`, `assets/units/`, and `assets/ui/`
(`tools/render_tiles.py` regenerates the terrain tiles). The shipped sounds
live in `assets/audio/`; synthesis is only a fallback, and audio stays
silent when the machine has no audio device.

Out of scope by design: story campaign, multiplayer, networking, editor,
new resources, routs, and magic. Battle auto-resolve is provided as the
practical fallback for a player who does not want to issue individual unit
orders.

## Summary and test evidence

Rules are in `tbb/rules` and import no pygame (a source-scan test locks
this); presentation is in `tbb/app`; original art/audio live in `assets/`.
Run `make test` for the 70 headless tests, the `--save-smoke` command above
for a real JSON slot, the dummy `--frames`
command above for a launch smoke check, and dummy `--dump-frames` to inspect
the four display-free screens. The checked-in suite covers start layouts and
names, the multi-biome worldgen contract (every biome present, mountain
walls, passes, ≥20 MP long axis, capital spacing, camps), staffed economy,
population carry, movement and pass gates, AI orders and founding, talents,
18×13 battle fields, side-based turns and the scripted foe, wound expiry,
battle writeback and capture, garrison transfer, succession, victory/defeat,
save/load roundtrips including mid-battle, art files, frame dumping, and
pygame isolation. Last verification: 70 tests passed, the 45-frame dummy SDL
smoke, the save smoke, and the four-screen dump all completed successfully.
