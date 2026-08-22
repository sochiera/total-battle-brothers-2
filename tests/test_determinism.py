"""Determinism guarantees: string seeds and branch tags must not depend on
interpreter hash randomisation, and save files must be JSON."""
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


def test_branch_uses_stable_int():
    assert stable_int("x") == stable_int("x")
    child = RNG("root-1").branch("aux")
    child2 = RNG("root-1").branch("aux")
    assert [child.random() for _ in range(5)] == \
        [child2.random() for _ in range(5)]


def test_branch_is_same_in_processes_with_different_hash_seeds():
    code = ("from tbb.rules.rng import RNG; "
            "print([RNG('root').branch('aux').randint(0, 1000000) "
            "for _ in range(6)])")
    outputs = []
    for hash_seed in ("0", "random"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        outputs.append(subprocess.check_output(
            [sys.executable, "-c", code], env=env, text=True))
    assert outputs[0] == outputs[1]


def test_campaign_state_is_same_in_processes_with_different_hash_seeds():
    code = ("from tbb.rules.campaign import Campaign; "
            "from tbb.rules import persistence as P; "
            "c=Campaign(2468); c._make_battle(c.hero_party(0), "
            "c.hero_party(1), False); print(P.canonical(c))")
    outputs = []
    for hash_seed in ("0", "random"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        outputs.append(subprocess.check_output(
            [sys.executable, "-c", code], env=env, text=True))
    assert outputs[0] == outputs[1]


def test_save_file_is_json(tmp_path):
    c = Campaign(seed=5)
    c.player.gold = 123.25
    c.player.wheat = 77
    P.save(c, "s1", save_dir=tmp_path)
    raw = open(P.save_path("s1", tmp_path)).read()
    assert raw.lstrip().startswith("{")
    obj = json.loads(raw)
    assert obj["version"] == 1
    assert obj["seed"] == 5
    assert "grid" in obj["world"]


def test_load_matches_saved_rng_stream():
    import tempfile
    c = Campaign(seed=999)
    for _ in range(5):
        c.rng.randint(0, 10 ** 6)
    d = tempfile.mkdtemp()
    P.save(c, "m", save_dir=d)
    c2 = P.load("m", save_dir=d)
    assert [c.rng.randint(0, 1000) for _ in range(6)] == \
        [c2.rng.randint(0, 1000) for _ in range(6)]


def test_stable_int_same_across_bitness():
    assert stable_int(42) == 42
    assert stable_int(b"k").__class__ is int
