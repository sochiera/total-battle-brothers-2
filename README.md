# Total Battle Brothers

A grimm realistic medieval ruler game for Linux. You command a company that
moves with your hero across a large hex world, manage the wheat, gold and
people of your duchy, march on four rival duchies, or fall to them. There is
no magic and no fantasy — only iron, hunger, winter, and war.

Built in the tradition of Battle Brothers' company fights, Stainless Steel's
slow burning realm, and Wesnoth's hex battles.

## What works

- A **campaign world** of ~46 × 34 hexes with plains, woods, hills, rivers,
  wastes and lakes; five duchies (you plus four AI), independent holdings and
  2–4 robber bands — every seed different.
- **Realm economy**: wheat and gold, a shared population pool, the locked
  building roster (Farm, Granary, Market, Militia Hall, Training Yard,
  Smithy, Bowyer, Walls, Keep, Chapel). Buildings must be staffed and paid;
  close a building and its craftsperson returns to the pool.
- **Named warriors** with rolled talents that decide which stats training
  (whole months in a Training Yard) and combat experience actually improve.
  A bow-gifted scout and a swordsman trained the same way do not converge.
- **Gear as kits** — light, militia, bow, heavy plate, two-hander, longbow.
  A smithy is required before heavy plate, a bowyer before quality bows.
- **One hero per duchy** with a field company of at most 12 + the hero.
  Without the hero nothing marches. Designate an heir in the settlement
  screen; when the hero falls and an heir waits, the campaign marches on.
- **Turn-based hex battles**: move, melee, bow, end turn. Terrain from the
  world map (wood, hill, ford, village) modifies hit chances; morale only
  changes hit chance — there are no routs. Stuns, temporary wounds and
  permanent wounds (a maimed leg or a lost eye stay for life), death is
  permanent.
- **AI duchies** develop, recruit, train, equip and will march on weak
  neighbours and on you. Bandits raid roads and villages. Neutrals defend
  but never expand.
- **Save and load** in named slots, from the title screen and in game.

## Requirements & install

Ubuntu 26.04 (other Linuxes with Python 3.12+ work the same; system Python
is PEP 668 so nothing should ever be installed globally):

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

(On a Linux install whose Python lacks `ensurepip` because the `python3-venv`
package is missing, install it with `sudo apt install python3-venv` first.)

## Playing

```sh
make run
```

or, equivalently, with a specific seed:

```sh
./run.sh
.venv/bin/python3 -m tbb
.venv/bin/python3 -m tbb --seed 12345
.venv/bin/python3 -m tbb --seed 12345 --new-game
.venv/bin/python3 -m tbb --seed 12345 --new-game --resolve-battle --frames 45
```

The windowed game opens on the title screen. Type a number for a seed, or run
with the default seed, and press **New Game** (or just press Enter).

### Controls

| Screen | Action | Key/Mouse |
|--------|--------|-----------|
| Title | start a new game | click **New Game** or Enter |
| Title | load a game | click **Load Game** |
| Title | focus the seed box | click the box, type digits |
| Campaign | select a hero company | click the hero's hex |
| Campaign | march the selected company | click an adjacent hex |
| Campaign | pan the map | **Left / Right / Up / Down** |
| Campaign | open a waiting battle | **B** or the panel button |
| Campaign | auto-resolve pending battles | **A** |
| Campaign | end the month (turn) | **M** or the panel button |
| Campaign | open the selected settlement | **O** or the panel button |
| Campaign | found a village / exit found mode | **F** or the panel button |
| Campaign | save / load (named slots) | **S** / **L** or the panel buttons; **Enter**, **Backspace**, **Esc** on the slot screen |
| Campaign | return to title / cancel found mode | **Esc** |
| Settlement | build / staff / unstaff / close a building | click the named controls |
| Settlement | train / gear field warriors | click the control; use **More warriors** pages |
| Settlement | recruit garrison / company | click the row |
| Settlement | develop to next size, found on map | click the row |
| Settlement | name a new heir | click a soldier's name in the right-hand list |
| Settlement | page the heir list | click **Previous heirs** / **More heirs** |
| Settlement | back to the map | **Esc** / **O** |
| Battle | select one of your warriors | click the warrior |
| Battle | move / strike | click a hex / a foe |
| Battle | end the turn | **Space** or the button |
| Battle | auto-resolve the whole fight | **A** or the button |
| Battle | return to the map (after) | click **Return to Map** |

### The count of the world

- 1 **month** = one campaign turn. There are 13 months of 4 weeks; a year is
  52 weeks. Training and gear orders finish only on whole month boundaries.
- **Wheat and gold** are produced by staffed farms, granaries, markets and
  the keep. Every warrior eats wheat and burns gold in upkeep; population
  eats too. Silence and starvation lower your realm morale, and starving folk
  simply leave the pool.
- **Winning**: be the last ruling duchy — destroy all four rivals.
  **Losing**: every settlement is lost AND the hero is dead with no heir AND
  no town remains that could raise a new commander. Between those two things
  you keep going, grimly.

| Building     | Name shown in UI | Gold | Wheat | Months | Staff | Effect |
|--------------|------------------|-----:|------:|-------:|:-----:|--------|
| Farm         | Farm             | 20   | 5     | 2      | 1     | +7 wheat / month |
| Granary      | Granary          | 15   | 1     | 2      | 1     | preserves +3 wheat |
| Market       | Market           | 25   | 2     | 2      | 1     | +10 gold / month (needs a town) |
| Militia Hall | Militia Hall     | 15   | 1     | 1      | 1     | +3 garrison cap |
| Training Yard| Training Yard    | 40   | 5     | 3      | 1     | 2 drill slots (needs a town) |
| Smithy       | Smithy           | 50   | 8     | 3      | 1     | enables heavy plate / two-handers |
| Bowyer       | Bowyer           | 30   | 4     | 2      | 1     | enables quality bows |
| Walls        | Walls            | 30   | 4     | 2      | 1     | +5 garrison, cover defence |
| Keep         | Keep             | 60   | 10    | 4      | 1     | +4 garrison, +3 morale |
| Chapel       | Chapel           | 20   | 3     | 2      | 1     | +4 morale, more births |

An unstaffed house grants nothing and costs nothing — the craftsperson must
be hired out of the shared population. Closing (tearing down) a building
returns 1 population to the pool and frees a building slot.

## Technical shape

- `tbb/rules/` — the whole rules engine, deterministic given a seed, no UI
  imports, fully unit-tested headlessly. All cost/formula constants live in
  `tbb/rules/constants.py`.
- `tbb/app/` — the pygame presentation, importing rules read-only.
- Saves are **versioned plain JSON** (`saves/*.tbb`) written by `tbb/rules/save.py`:
  every piece of a mid-campaign state — calendar, world grid, holdings and
  buildings, named units with talents/wounds/kit, orders still in flight,
  parties, heirs and the random stream — so files are inspectable, portable
  between machines, and carry no executable objects.
- Art is **original, procedurally painted in-repo** (`tbb/app/art.py`):
  dithered terrain, gabled villages, palisade towns, keeps, and unit
  silhouettes for every kit.
- Audio is **original and synthesised at runtime** (`tbb/app/audio.py`):
  UI clicks, melee thock, bow twang, pain, and a dark ambient loop. If a
  machine has no audio device the game silently runs without sound.

## Screens / data files / release notes

- Named save slots live in `saves/*.tbb` as human-readable JSON.
- Demo content: seeds are just numbers; the default seed produces a
  immediately playable duchy. There is no scripted story anywhere.
- Launcher errors clearly when the venv is missing (`./run.sh` prints the
  exact `python3 -m venv` + `pip install` commands).
- Not included: multiplayer, networking, or a story campaign. The sandbox has
  no scripted objectives beyond its rules victory and defeat conditions.

## Summary

A complete, deterministic rules engine with economy, recruitment, talent
training, movement, contact and capped hex battles, succession and
victory/defeat; a windowed pygame client with original procedurally-drawn
2D art and runtime-synthesised audio; named save/load from title and in-game.
Test evidence: `python3 -m pytest -q` passes 77 headless tests covering
economy, recruitment and garrison constraints, movement/contact, battle
hit/morale logic, succession, victory/defeat and JSON save continuation.
