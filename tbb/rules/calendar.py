"""The campaign calendar: thirteen four-week months per year."""
from . import constants as C

class Calendar:
    def __init__(self, year=1, month=0):
        self.year, self.month = int(year), int(month)
        if not 0 <= self.month < C.MONTHS_PER_YEAR:
            raise ValueError("month must be 0..12")

    def month_name(self):
        return C.MONTH_LABELS[self.month]

    @property
    def month_label(self):
        return self.month_name()

    @property
    def weeks(self):
        return C.WEEKS_PER_MONTH

    def label(self):
        return f"Year {self.year}, Month {self.month_name()}"

    def advance(self, months=1):
        if months < 0:
            raise ValueError("calendar only advances forward")
        absolute = (self.year - 1) * C.MONTHS_PER_YEAR + self.month + months
        self.year, self.month = divmod(absolute, C.MONTHS_PER_YEAR)
        self.year += 1

    def elapsed_months(self, other):
        return (self.year - other.year) * C.MONTHS_PER_YEAR + self.month - other.month

    def snapshot(self):
        return {"year": self.year, "month": self.month}

    @classmethod
    def from_snapshot(cls, value):
        if isinstance(value, dict):
            return cls(value["year"], value["month"])
        return cls(*value)

    def __eq__(self, other):
        return isinstance(other, Calendar) and (self.year, self.month) == (other.year, other.month)

    def __repr__(self):
        return f"Calendar({self.label()!r})"
