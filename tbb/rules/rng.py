"""Deterministic seedable RNG shared by every random process in the rules.

A single RNG instance is threaded through the whole campaign so the same seed
reproduces the same campaign and the same battle outcomes when the same actions
are applied. Its internal state is stored with each save so a loaded campaign
continues the exact same random stream.

Seeds and branch tags are mixed with SHA-256 so determinism never depends on
interpreter hash randomisation.
"""
import hashlib
import random


def stable_int(value):
    """Deterministic integer from an int/str on any interpreter."""
    if isinstance(value, int):
        return value
    h = hashlib.sha256(str(value).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


class RNG:
    def __init__(self, seed):
        if not isinstance(seed, int):
            seed = stable_int(seed) % (2 ** 63)
        self.seed = int(seed) % (2 ** 63)
        self._r = random.Random(self.seed)

    # ---- state -----------------------------------------------------------
    def getstate(self):
        return self._r.getstate()

    def setstate(self, state):
        self._r.setstate(state)

    def state_snapshot(self):
        """JSON-friendly serialisation of the underlying RNG state."""
        return list(self._r.getstate())

    def restore_state(self, snapshot):
        def _tuple(v):
            if isinstance(v, list):
                return tuple(_tuple(x) for x in v)
            return v

        self._r.setstate(tuple(_tuple(x) for x in snapshot))

    # ---- generators ------------------------------------------------------
    def random(self):
        return self._r.random()

    def randint(self, a, b):
        return self._r.randint(a, b)

    def choice(self, seq):
        return self._r.choice(seq)

    def choices(self, seq, k=1):
        return self._r.choices(seq, k=k)

    def shuffle(self, seq):
        self._r.shuffle(seq)
        return seq

    def sample(self, seq, k):
        return self._r.sample(seq, k)

    def sample_no_repeat(self, seq, k):
        return self.sample(seq, k)

    def branch(self, tag):
        """Deterministic sub-RNG for isolated subsystems (never used for
        campaign-critical rolls outside their parent stream)."""
        mix = stable_int("%s::%s" % (self.seed, tag))
        return random.Random(mix)

    def clone(self):
        other = RNG(self.seed)
        other.setstate(self.getstate())
        return other
