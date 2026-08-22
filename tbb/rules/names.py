"""Grim medieval European names for warriors, heroes, realms and settlements.

Names are generated deterministically from the seeded RNG so a fixed seed
always yields the same roster. Surnames are compounded descriptors; no
fantasy names.
"""
FIRST_NAMES = [
    "Aldric", "Baldwin", "Bertram", "Cuthbert", "Dolfin", "Egbert", "Folcard",
    "Gamelin", "Godfrey", "Hamelin", "Hlothar", "Hugh", "Ivo", "Jorund",
    "Knut", "Lambert", "Malcolm", "Milo", "Nigel", "Osbert", "Oswin",
    "Perkin", "Radulf", "Reynard", "Rolf", "Sigmund", "Sta", "Tancred",
    "Ulf", "Valdemar", "Warin", "William", "Wulfstan", "Aelric", "Borel",
    "Cenwulf", "Drusus", "Edric", "Fu", "Geoffrey", "Heribert", "Ingulf",
    "Jard", "Leofric", "Marlin", "Norbert", "Odo", "Piers", "Renward",
    "Siward", "Thibaut", "Udolf", "Vitus", "Wymund", "Yvor", "Zoltan",
]
SURNAMES = [
    "the Grim", "the Stern", "Blackheart", "Ironhand", "the Bitter",
    "of Greyford", "the Wild", "Stonefist", "the Oathbound", "Halfgold",
    "the Lean", "Wolfsbane", "the Unyielding", "of the Ford", "Redmane",
    "the Sleepless", "Clanklift", "the Horseshoe", "the Flintbeard",
    "the Mudcutter", "Ravenborn", "the Cartwright", "of Thistledown",
    "the Hoarse", "Toughbody", "the Wall", "Lugbur", "the Ceaseless",
    "of Deeps", "the Fairless", "Hallowspell", "the Beacon-less", "the Rook",
    "Torchcrest", "the Greycloak", "of the High Path", "the Winds",
    "the Bitterroot", "Scytheman", "the Starved", "the Grainless",
]
REALM_NAMES = [
    "House", "Duchy", "March", "Realm", "Carrena", "Holds", "Westermark",
    "East", "Vend", "Nordhold", "Mirrormere", "Forth", "Silvertree",
    "Grimwaad", "Brokenfield", "Harrowford",
]
SETTLEMENT_NAMES = [
    "Brek", "Ford", "Hay", "Moor", "Wyn", "Aston", "Kettle", "Ravenna",
    "Barrow", "Sted", "Oakham", "Fording", "Nettle", "Dreber", "Somme",
    "Toren", "Ashby", "Crowle", "Middleton", "Witherholm",
]

def first_name(rng):
    return rng.choice(FIRST_NAMES)


def surname(rng):
    return rng.choice(SURNAMES)


def warrior_name(rng):
    """e.g. 'Roland the Ironvale'."""
    while True:
        n = "%s %s" % (first_name(rng), surname(rng))
        return n


def hero_name(rng):
    return warrior_name(rng)


def unique_warrior_name(rng, taken):
    """Generate a name unique within the company (append a disambiguator if
    the pool collides, keeping the result readable in UI and saves)."""
    base = warrior_name(rng)
    name = base
    i = 2
    while name in taken:
        name = "%s %d" % (base, i)
        i += 1
    taken.add(name)
    return name


def realm_name(rng):
    return "%s of %s" % (rng.choice(REALM_NAMES), rng.choice(REALM_NAMES))


def settlement_name(rng):
    return rng.choice(SETTLEMENT_NAMES)