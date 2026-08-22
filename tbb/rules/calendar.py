"""Locked calendar: 13 named months of 4 weeks == 1 year. One campaign turn
== 1 month. Training and gear orders complete only on whole-month boundaries.
"""
from . import constants as C


class Calendar:
    def __init__(self, year=1, month=0):
        self.year = year
        self.month = month  # 0-based index into MONTH_NAMES

    def month_name(self):
        return C.MONTH_NAMES[self.month % C.MONTHS_PER_YEAR]

    def label(self):
        return "%d, month of %s" % (self.year, self.month_name())

    def advance(self):
        self.month += 1
        if self.month >= C.MONTHS_PER_YEAR:
            self.month = 0
            self.year += 1

    def elapsed_months(self, other):
        """Number of whole months from other to self."""
        return (self.year - other.year) * C.MONTHS_PER_YEAR + (self.month - other.month)

    def __eq__(self, other):
        return isinstance(other, Calendar) and (self.year, self.month) == (
            other.year, other.month
        )

    def __repr__(self):
        return "Calendar(%r)" % self.label()

    # pickling niceties
    def snapshot(self):
        return (self.year, self.month)

    @classmethod
    def from_snapshot(cls, snap):
        return cls(*snap)