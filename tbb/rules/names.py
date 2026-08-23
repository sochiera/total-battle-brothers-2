"""Small, historical-sounding name lists."""
FIRST_NAMES = ("Aldric", "Baldwin", "Bertram", "Cuthbert", "Edmund", "Folcard",
               "Gamelin", "Godfrey", "Hamelin", "Hugh", "Ivo", "Lambert",
               "Malcolm", "Milo", "Nigel", "Osbert", "Perkin", "Radulf",
               "Reynard", "Rolf", "Tancred", "Ulf", "Warin", "Wulfstan",
               "Aelric", "Cenwulf", "Edric", "Geoffrey", "Leofric", "Siward")
SURNAMES = ("the Grim", "the Stern", "Blackheart", "Ironhand", "the Bitter",
            "of Greyford", "Stonefist", "the Lean", "of the Ford", "Redmane",
            "the Sleepless", "the Cartwright", "the Gruff", "the Wall",
            "the Ceaseless", "the Fairless", "the Rook", "the Greycloak",
            "of the High Road", "the Starved")
REALM_NAMES = ("Aldmere", "Bracken", "Coldwell", "Dunmarsh", "East Fell",
               "Greyford", "Harrow", "Longfield", "Redwater", "Stonebridge",
               "Westmarch", "Wycham", "Ashen Vale", "Blackmere", "Crownfield",
               "Dalehurst", "Eldwater", "Foxcombe", "Greenbarrow", "High Rill",
               "Ironmere", "Kingsfield", "Lowmarsh", "Northwatch", "Oakrest",
               "Pennford", "Ravenholt", "Southmere", "Thornwick", "White Down")
SETTLEMENT_NAMES = ("Brek", "Ford", "Hay", "Moor", "Wyn", "Aston", "Kettle",
                    "Raven", "Barrow", "Sted", "Oakham", "Nettle", "Dreber",
                    "Somme", "Toren", "Ashby", "Crowle", "Middleton", "Witherholm",
                    "Briar", "Chalk", "Dun", "Elm", "Fallow", "Gorse", "Hearth",
                    "Ivydale", "Juniper", "Kirk", "Lark", "Marden", "Nook",
                    "Orchard", "Pike", "Quarry", "Rowan", "Sable", "Tarn",
                    "Umber", "Vane", "Willow", "Yew", "Zeal")
REGION_NAMES = ("The Western March", "The Crown Vale", "The Eastern Weald",
                "The Southern Fields", "The Northern Downs", "The Riverlands",
                "The High Country", "The Low Country")
RIVER_NAMES = ("Greywater", "Red Run", "The Mereflow", "Kingswater",
               "Blackstream", "The Long Ford")

def warrior_name(rng):
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(SURNAMES)}"

def unique_warrior_name(rng, taken):
    base = warrior_name(rng); name = base; suffix = 2
    while name in taken:
        name = f"{base} {suffix}"; suffix += 1
    taken.add(name)
    return name

def hero_name(rng):
    return warrior_name(rng)

def realm_name(rng):
    return rng.choice(REALM_NAMES)

def settlement_name(rng):
    return rng.choice(SETTLEMENT_NAMES)

def _unique(rng, chooser, taken):
    base = chooser(rng)
    name = base
    # A numeric suffix is easy to spot in the UI and makes a generated world
    # feel like a collision.  Use a historical qualifier instead, and keep a
    # final deterministic pool for adversarial fixed-choice RNGs in tests.
    qualifiers = ("East", "West", "North", "South", "Upper", "Lower",
                  "by the Ford", "on the Hill", "of the Downs", "in the Vale")
    index = 0
    while name in taken:
        qualifier = qualifiers[index % len(qualifiers)]
        name = f"{base} {qualifier}"
        index += 1
        if index >= len(qualifiers) and name in taken:
            name = f"{base} {chr(65 + (index - len(qualifiers)) % 26)}"
    taken.add(name)
    return name

def unique_realm_name(rng, taken):
    return _unique(rng, realm_name, taken)

def unique_settlement_name(rng, taken):
    return _unique(rng, settlement_name, taken)
