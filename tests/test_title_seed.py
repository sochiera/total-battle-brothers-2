"""Title seed parsing is testable without opening a pygame display."""
import sys
import types


def _title_screen(monkeypatch, text):
    # App modules only need pygame at runtime for drawing. A module stub keeps
    # this unit test headless even when pygame-ce is not installed system-wide.
    monkeypatch.setitem(sys.modules, "pygame", types.ModuleType("pygame"))
    from tbb.app.main import TitleScreen

    screen = TitleScreen.__new__(TitleScreen)
    screen.seed_text = text
    return screen


def test_title_seed_defaults_and_uses_typed_digits(monkeypatch):
    assert _title_screen(monkeypatch, "")._seed() == 734102
    assert _title_screen(monkeypatch, "246813")._seed() == 246813
