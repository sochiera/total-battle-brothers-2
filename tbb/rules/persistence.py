"""Named save slots around the versioned rules JSON."""
import json, os, re
from . import constants as C
from .save import to_state_dict, from_state_dict

def _directory(save_dir=None): return os.fspath(save_dir) if save_dir is not None else C.SAVE_DIR
def _slot_name(slot):
    slot=os.fspath(slot)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,48}",slot): raise ValueError("slot names use 1-48 letters, digits, '_' or '-'")
    return slot
def save_path(slot,save_dir=None): return os.path.join(_directory(save_dir),_slot_name(slot)+C.SAVE_EXT)
def save(campaign,slot,save_dir=None):
    os.makedirs(_directory(save_dir),exist_ok=True); path=save_path(slot,save_dir)
    with open(path,"w",encoding="utf-8") as f: json.dump(to_state_dict(campaign),f,sort_keys=True,separators=(",",":")); f.write("\n")
    return path
def load(slot,save_dir=None):
    path=save_path(slot,save_dir)
    if not os.path.exists(path): return None
    try:
        with open(path,encoding="utf-8") as f: return from_state_dict(json.load(f))
    except (OSError,ValueError,TypeError,KeyError,IndexError,UnicodeError) as exc: raise ValueError(f"could not load slot '{slot}': {exc}") from exc
def delete(slot,save_dir=None):
    path=save_path(slot,save_dir)
    if os.path.exists(path): os.remove(path)
def list_slots(save_dir=None):
    directory=_directory(save_dir)
    return sorted(fn[:-len(C.SAVE_EXT)] for fn in os.listdir(directory) if fn.endswith(C.SAVE_EXT)) if os.path.isdir(directory) else []
def canonical(campaign): return json.dumps(to_state_dict(campaign),sort_keys=True,default=str)
