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
               "Westmarch", "Wycham")
SETTLEMENT_NAMES = ("Brek", "Ford", "Hay", "Moor", "Wyn", "Aston", "Kettle",
                    "Raven", "Barrow", "Sted", "Oakham", "Nettle", "Dreber",
                    "Somme", "Toren", "Ashby", "Crowle", "Middleton", "Witherholm")

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
