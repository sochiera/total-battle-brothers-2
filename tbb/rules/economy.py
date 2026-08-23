"""Monthly trade and hostile sack rules kept separate from Campaign flow."""

from . import constants as C
from . import terrain as GEO
from .checks import Check


def account(campaign, realm):
    """Apply one realm's seasonal food, upkeep, growth and morale ledger."""
    holdings = realm.holdings(campaign.settlements)
    capacity = realm.holdings_cap(campaign.settlements)
    multiplier = C.SEASON_WHEAT_MULTIPLIER[campaign.calendar.season]
    produced = sum(
        holding.food_produced(campaign._local_population(realm, holding))
        for holding in holdings) * multiplier
    living = len(realm.living_units(campaign.units))
    food_need = (realm.population * C.POP_FOOD_PER_MONTH +
                 living * C.WARRIOR_FOOD_UPKEEP)
    realm.wheat += produced
    remainder = realm.wheat - food_need
    if remainder < 0:
        realm.wheat = 0
        realm.morale += C.STARVATION_MORALE
        realm.population = max(0, realm.population - max(1, int(-remainder)))
    else:
        granaries = sum(1 for holding in holdings
                        if holding.has(C.BUILDING_GRANARY))
        spoilage = max(0.0, C.SPOILAGE_RATE -
                       granaries * C.GRANARY_SPOILAGE_REDUCTION)
        realm.wheat = max(0.0, remainder * (1 - spoilage))
    due = (living * C.WARRIOR_GOLD_UPKEEP +
           realm.building_upkeep(campaign.settlements))
    realm.gold -= due
    if realm.gold < 0:
        realm.gold = 0
        realm.morale += C.UNPAID_UPKEEP_MORALE
    if realm.population >= capacity:
        realm.population_fraction = 0.0
    elif realm.wheat > 0:
        growth = ((realm.population * C.BIRTH_RATE +
                   realm.population * C.IMMIGRATION_RATE) *
                  (realm.morale / 100.0)) + realm.population_fraction
        whole = int(growth)
        realm.population = min(capacity, realm.population + whole)
        realm.population_fraction = (0.0 if realm.population >= capacity
                                     else growth - whole)
    realm.morale = max(0, min(
        100, realm.morale + realm.morale_from_holdings(campaign.settlements)))


def transfer_goods(campaign, source_sid, target_sid, resource, dry_run=False):
    """Move a fixed local convoy between two distinct owned holdings."""
    source = campaign.settlements.get(source_sid)
    target = campaign.settlements.get(target_sid)
    if source is None or target is None:
        return Check(False, "both holdings must exist")
    if source.id == target.id:
        return Check(False, "a convoy needs another holding")
    if source.owner != campaign.player.key or target.owner != campaign.player.key:
        return Check(False, "both holdings must belong to your realm")
    if not source.has(C.BUILDING_MARKET):
        return Check(False, "a staffed market is required at the shipping holding")
    distance = GEO.hex_distance(source.hex, target.hex)
    if distance <= 0:
        return Check(False, "a convoy needs positive inter-holding distance")
    if distance > C.MARKET_TRANSFER_RANGE:
        return Check(False, "the market convoy cannot reach that far")
    if resource == "wheat":
        amount = C.MARKET_TRANSFER_WHEAT
        if source.wheat < amount:
            return Check(False, "the shipping holding lacks wheat")
    elif resource == "gold":
        amount = C.MARKET_TRANSFER_GOLD
        if source.gold < amount:
            return Check(False, "the shipping holding lacks gold")
    else:
        return Check(False, "ship wheat or gold")
    if not dry_run:
        if resource == "wheat":
            source.wheat -= amount
            target.wheat += amount
        else:
            source.gold -= amount
            target.gold += amount
    return Check(True, "shipped %d %s from %s to %s" %
                 (amount, resource, source.name, target.name))


def raid_settlement(campaign, sid, raider_realm=None):
    """Sack a rival or neutral holding without changing its owner."""
    holding = campaign.settlements.get(sid)
    if holding is None:
        return Check(False, "there is no stocked holding to raid")
    raider = campaign.player.key if raider_realm is None else raider_realm
    if holding.owner == raider:
        return Check(False, "a realm cannot raid its own holding")
    owner_realm = (campaign.realms.get(holding.owner)
                   if holding.owner is not None else None)
    stolen_w = min(C.RAID_SACK_WHEAT, int(holding.wheat))
    stolen_g = min(C.RAID_SACK_GOLD, int(holding.gold))
    holding.wheat -= stolen_w
    holding.gold -= stolen_g
    holding.population = max(0, holding.population - C.RAID_POP_CUT)
    if owner_realm:
        owner_realm.wheat = max(0, owner_realm.wheat - stolen_w)
        owner_realm.gold = max(0, owner_realm.gold - stolen_g)
    campaign.notes.append(
        f"{holding.name} is raided: -{stolen_w} wheat, -{stolen_g} gold, "
        f"-{C.RAID_POP_CUT} people")
    return Check(True, "raid sacks stores without annexing the holding")
