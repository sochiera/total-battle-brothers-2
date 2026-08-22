"""Named-slot save / load layer on top of the JSON GameState schema.

Serialised files are human-readable JSON (`GameState`), so they
are inspectable, portable between machines/versions, and carry no arbitrary
code. `canonical` produces a deterministically-ordered summary used by the
headless roundtrip test.
"""
import json
import os
import re

from . import constants as C
from .save import to_state_dict, from_state_dict

SAVE_DIR = C.SAVE_DIR


def _directory(save_dir=None):
    return SAVE_DIR if save_dir is None else os.fspath(save_dir)


def _slot_name(slot):
    slot = os.fspath(slot)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}", slot):
        raise ValueError("slot names use 1-48 letters, digits, '_' or '-'")
    return slot


def save_path(slot, save_dir=None):
    return os.path.join(_directory(save_dir), "%s%s" % (_slot_name(slot), C.SAVE_EXT))


def save(campaign, slot, save_dir=None):
    """Serialize the live campaign into the slot as JSON."""
    directory = _directory(save_dir)
    os.makedirs(directory, exist_ok=True)
    path = save_path(slot, directory)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(to_state_dict(campaign), fh, sort_keys=True,
                  separators=(",", ":"))
        fh.write("\n")
    return path


def load(slot, save_dir=None):
    path = save_path(slot, save_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
        return from_state_dict(state)
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            AttributeError, UnicodeError) as exc:
        raise ValueError("could not load slot '%s': %s" % (slot, exc)) from exc


def delete(slot, save_dir=None):
    path = save_path(slot, save_dir)
    if os.path.exists(path):
        os.remove(path)


def canonical(campaign):
    """Deterministically-sorted JSON string over the game-state summary."""
    state = to_state_dict(campaign)
    return json.dumps(state, sort_keys=True, default=str)


def list_slots(save_dir=None):
    out = []
    directory = _directory(save_dir)
    if os.path.isdir(directory):
        for fn in sorted(os.listdir(directory)):
            if fn.endswith(C.SAVE_EXT):
                out.append(fn[: -len(C.SAVE_EXT)])
    return out
