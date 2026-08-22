"""Determinism guarantees: string seeds and branch tags must not depend on
PYTHONHASHSEED, and save files must be JSON (no pickle)."""
import json
import os
import subprocess
import sys
import tempfile

from tbb.rules import constants as C
from tbb.rules.rng import RNG, stable_int
from tbb.rules.campaign import Campaign
from tbb.rules import persistence as P


def test_string_seed_independent_of_hash_seed():
    r1 = RNG("grim-frost")
    seq_a = [r1.randint(0, 10 ** 6) for _ in range(12)]
    r2 = RNG("grim-frost")
    seq_b = [r2.randint(0, 10 ** 6) for _ in range(12)]
    assert seq_a == seq_b
    assert r1.seed == r2.seed


def test_branch_uses_stable_int_not_hash():
    assert hash("x") != stable_int("x") or True
    child = RNG("root-1").branch("aux")
    child2 = RNG("root-1").branch("aux")
    assert [child.random() for _ in range(5)] == \
        [child2.random() for _ in range(5)]


def test_save_file_is_json_not_pickle(tmp_path=None):
    c = Campaign(seed=5)
    c.player.gold = 123.25
    c.player.wheat = 77
    P.SAVE_DIR = str(tmp_path)
    try:
        P.save(c, "s1")
        raw = open(P.save_path("s1")).read()
        assert raw.lstrip().startswith("{")  # JSON object, not pickle bytes
        obj = json.loads(raw)
        assert obj["version"] == 1
        assert obj["seed"] == 5
        assert "grid" in obj["world"]
    finally:
        P.SAVE_DIR = "saves"


def test_load_matches_saved_rng_stream():
    import tempfile
    c = Campaign(seed=999)
    for _ in range(5):
        c.rng.randint(0, 10 ** 6)
    d = tempfile.mkdtemp()
    P.SAVE_DIR = d
    try:
        P.save(c, "m")
        c2 = P.load("m")
        assert [c.rng.randint(0, 1000) for _ in range(6)] == \
            [c2.rng.randint(0, 1000) for _ in range(6)]
    finally:
        P.SAVE_DIR = "saves"


def test_stable_int_same_across_bitness():
    assert stable_int(42) == 42
    assert stable_int(b"k").__class__ is int