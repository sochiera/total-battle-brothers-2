"""Contact classification shared by campaign movement and battle rules."""

from . import constants as C


def is_prepared_assault(holding):
    """A walled town/city contact gets the defender's prepared advantage."""
    return holding is not None and holding.size in (C.SIZE_T, C.SIZE_C) and (
        holding.size == C.SIZE_C or C.BUILDING_WALLS in holding.buildings or
        C.BUILDING_KEEP in holding.buildings)


def parties_hostile(attacker, defender):
    if attacker.realm is None and defender.realm is None:
        return False
    if attacker.realm is None or defender.realm is None:
        return True
    return attacker.realm != defender.realm
