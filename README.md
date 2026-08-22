# Total Battle Brothers

Total Battle Brothers is a single-player Linux sandbox about a grim medieval
duchy and its named company. It has no magic, fantasy creatures, scripted
story campaign, or multiplayer. The goal is to outlast every rival ducal line.

## Requirements and launch

Ubuntu 26.04 (or another Linux with Python 3.10+) and a window-capable pygame
installation are required. Keep dependencies in the project environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh
```

Equivalent commands are `make run` and `.venv/bin/python3 -m tbb`. A seed can
be supplied with `--seed 734102`; `--new-game` skips the title screen and
`--frames 45` is useful for a dummy-video smoke run:

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python3 -m tbb \
  --seed 734102 --new-game --frames 45
```

## What works

Each campaign contains a 46×34 painted hex world, one player duchy, five AI
duchies, neutral villages, and exactly three robber bands. The player starts
as either a border count with one village or a minor duke with two or three
village/town holdings. Roads, forests, hills, rivers with fords/bridges,
villages and ruins all have distinct terrain art.

One turn is one month. A year has thirteen four-week months labelled I–XIII.
A company has at most 12 named people including its living hero. Warriors
have a name, origin, age, three growth talents, melee, ranged, hit points,
fatigue and resolve. Combat XP and whole-month training grow only talent-
affined stats; death is permanent and wounds can cap stats.

The economy uses only wheat and gold. Farms produce food, granaries reduce
spoilage, markets trade explicitly at 5 wheat for 2 gold or 2 wheat for 4
gold, and every staffed building consumes one resident. The buildings are:

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

Allowed kits are Light armour, Shield + one-hander, Bow, Heavy armour, and
Two-hander. Heavy armour and Two-hander require a staffed Smithy; Bow requires
a staffed Fletcher. Recruiting costs 10 gold, 2 wheat, one month, and one
population. Founding costs 50 gold, 15 wheat, three months, and two settlers.
Village→Town costs 80 gold/20 wheat/four months; Town→City costs 180
gold/45 wheat/seven months.

The hero company can march, recruit at a holding, garrison or detach soldiers,
train, equip, found villages, develop holdings, and fight. A hostile party or
holding contact opens an individual-unit 14×11 hex battle with movement,
melee, ranged line, terrain cover, AP, HP, stun, wounds and auto-resolve.
Morale changes hit chance only: there are no routs or mass flight. Court lets
the player designate an heir. A dead hero can be replaced by that heir, or by
a new commander while a town/city remains. Victory is the last ruling duchy;
defeat requires no settlements, no living hero, no heir, and no town/city that
could raise a commander.

Named save slots are JSON files in `saves/`. They include map crossings,
calendar, orders, parties, every warrior field, pending battles, and the RNG
stream. Old schema versions and corrupt files are reported in the load menu.

## Controls

On the campaign map, click a hero token and an adjacent hex to march. Use
`M` to end the month, `O` to open the selected settlement, `F` to enter found
mode, `B` to enter a pending battle, `A` to auto-resolve, `C` for Court, and
`S`/`L` for save/load. Arrow keys pan the map. Settlement controls show
building, population, supply, size, company and hero requirements in their
disabled state. In battle, click a unit then an adjacent hex or hostile unit;
`Space` ends the turn and `A` auto-resolves.

## Demo data and limitations

Seeds, the default 734102 world, generated names, and procedural painted
sprites are demo data. Audio is synthesized at runtime and stays silent when
the machine has no audio device. There is no story campaign, multiplayer,
networking, or external content pipeline.

## Summary and test evidence

Rules are in `tbb/rules` and import no pygame; presentation is in `tbb/app`.
Run `.venv/bin/python3 -m pytest -q` for headless tests and the dummy-video
command above for the launch smoke check. The checked-in suite covers the
deterministic rules foundation; the command is the factual verification path.
