"""Small result object shared by all headless campaign rule modules."""


class Check:
    __slots__ = ("ok", "reason")

    def __init__(self, ok, reason=""):
        self.ok = bool(ok)
        self.reason = reason

    def __bool__(self):
        return self.ok
