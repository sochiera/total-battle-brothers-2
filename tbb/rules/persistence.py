"""Named-slot save / load layer on top of the JSON GameState schema.

Serialised files are human-readable JSON (`GameState`), not pickles, so they
are inspectable, portable between machines/versions, and carry no arbitrary
code. `canonical` produces a deterministically-ordered summary used by the
headless roundtrip test.
"""
import json
import os

from . import constants as C
from .save import to_state_dict, from_state_dict


def save_path(slot):
    return os.path.join(C.SAVE_DIR, "%s%s" % (slot, C.SAVE_EXT))


def save(campaign, slot):
    """Serialize the live campaign into the slot as JSON."""
    os.makedirs(C.SAVE_DIR, exist_ok=True)
    path = save_path(slot)
    with open(path, "w") as fh:
        json.dump(to_state_dict(campaign), fh, sort_keys=True,
                  separators=(",", ":"))
    return path


def load(slot):
    path = save_path(slot)
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        state = json.load(fh)
    return from_state_dict(state)


def delete(slot):
    path = save_path(slot)
    if os.path.exists(path):
        os.remove(path)


def canonical(campaign):
    """Deterministically-sorted JSON string over the game-state summary."""
    state = to_state_dict(campaign)
    return json.dumps(state, sort_keys=True, default=str)


def list_slots():
    out = []
    if os.path.isdir(C.SAVE_DIR):
        for fn in sorted(os.listdir(C.SAVE_DIR)):
            if fn.endswith(C.SAVE_EXT):
                out.append(fn[: -len(C.SAVE_EXT)])
    return out