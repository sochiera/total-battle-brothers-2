import os
from pathlib import Path
import subprocess
import sys
import pytest
import importlib.util

pytestmark = pytest.mark.skipif(importlib.util.find_spec("pygame") is None,
                                reason="pygame is unavailable")


ROOT = Path(__file__).resolve().parents[1]


def test_required_pixel_art_files_are_readable_and_nontrivial(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from tbb.app import art
    from tbb.rules import constants as C
    pygame.init()
    pygame.display.set_mode((1, 1))
    paths = [
        *Path(ROOT / "assets/tiles").glob("*.png"),
        *Path(ROOT / "assets/settlements").glob("*.png"),
        *Path(ROOT / "assets/banners").glob("*.png"),
        *Path(ROOT / "assets/units").glob("*.png"),
        *Path(ROOT / "assets/ui").glob("*.png"),
    ]
    assert paths
    for path in paths:
        assert path.stat().st_size > 300
        image = pygame.image.load(str(path))
        assert min(image.get_size()) >= 16
        colors = {tuple(image.get_at((x, y)))
                  for x in range(0, image.get_width(), 3)
                  for y in range(0, image.get_height(), 3)}
        assert len(colors) >= 8
    terrain = art.terrain_sprites()
    assert all(terrain.get(kind) is not None for kind in C.CAMPAIGN_TERRAINS)
    assert terrain[(C.TERRAIN_RIVER, "ford")] is not None
    assert terrain[(C.TERRAIN_RIVER, "bridge")] is not None
    assert len({pygame.image.tobytes(terrain[k], "RGBA")
                for k in C.CAMPAIGN_TERRAINS}) == len(C.CAMPAIGN_TERRAINS)
    settlements = art.settlement_sprite_sheet()
    assert all(settlements[(0, size)] is not None for size in C.SIZE_ORDER)
    assert len({pygame.image.tobytes(settlements[(0, size)], "RGBA")
                for size in C.SIZE_ORDER}) == len(C.SIZE_ORDER)
    units = art.unit_sprite_sheet()
    assert all(units[(0, kit)] is not None for kit in C.KITS)
    assert units[(0, "light", True)] is not None
    assert units[(0, "bow")] is not None
    assert art.bandit_sprite() is not None
    assert len({pygame.image.tobytes(units[(0, kit)], "RGBA")
                for kit in C.KITS}) >= 2
    banners = art.banner_sprites()
    assert set(banners) == set(range(C.NUM_DUCHIES))
    assert len({pygame.image.tobytes(banners[index], "RGBA")
                for index in banners}) == C.NUM_DUCHIES
    chrome = art.ui_chrome()
    assert chrome["panel"] is not None and chrome["button"] is not None
    assert pygame.image.tobytes(chrome["panel"], "RGBA") != \
        pygame.image.tobytes(chrome["button"], "RGBA")
    pygame.quit()


def test_dump_frames_writes_live_screens_including_title_and_epilogue(tmp_path):
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    subprocess.run([sys.executable, "-m", "tbb", "--seed", "734102",
                    "--dump-frames", str(tmp_path)], cwd=ROOT, env=env,
                   check=True)
    import pygame
    pygame.init()
    expected = ("title.png", "campaign.png", "settlement.png", "court.png",
                "battle.png", "epilogue.png")
    for name in expected:
        path = tmp_path / name
        assert path.stat().st_size > 0
        image = pygame.image.load(str(path))
        assert image.get_size() == (1280, 800)
        if name in ("title.png", "campaign.png", "battle.png", "epilogue.png"):
            colors = {tuple(image.get_at((x, y)))
                      for x in range(0, image.get_width(), 8)
                      for y in range(0, image.get_height(), 8)}
            assert len(colors) > 20
    pygame.quit()


def test_forced_ending_only_changes_epilogue_frame(tmp_path):
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    subprocess.run([sys.executable, "-m", "tbb", "--seed", "734102",
                    "--ending", "defeat", "--dump-frames", str(tmp_path)],
                   cwd=ROOT, env=env, check=True)
    import pygame
    pygame.init()
    ending = pygame.image.load(str(tmp_path / "epilogue.png"))
    for name in ("campaign.png", "settlement.png", "court.png", "battle.png"):
        frame = pygame.image.load(str(tmp_path / name))
        assert pygame.image.tobytes(frame, "RGBA") != \
            pygame.image.tobytes(ending, "RGBA")
    pygame.quit()


def test_settlement_equip_reason_matches_gear_dry_run(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.settlement_screen import SettlementScreen
    from tbb.rules.campaign import Campaign
    pygame.init()
    campaign = Campaign(19)
    app = SimpleNamespace()
    screen = SettlementScreen(app)
    screen.load(campaign, campaign.player.settlement_ids[0])
    uid = campaign.player.hero
    assert screen._equip_reason(uid, "bow") == screen._gear_reason(uid, "bow")
    pygame.quit()


def test_title_seed_entry_and_generate(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.main import TitleScreen, generated_seed
    from tbb.rules import constants as C
    pygame.init()
    pygame.display.set_mode((1, 1))

    class Audio:
        def sfx(self, *_args):
            pass

    title = TitleScreen(SimpleNamespace(audio=Audio(), focus_seed=False,
                                        new_game=lambda *a: None))
    assert title._seed() == C.DEFAULT_SEED  # empty seed falls back
    title.seed_text = "123"
    assert title._seed() == 123
    title.seed_text = "12x3"
    assert title._seed() == C.DEFAULT_SEED  # junk falls back
    seeds = {generated_seed() for _ in range(6)}
    assert len(seeds) > 1  # generate produces fresh integers
    title.generate()
    assert title.seed_text.isdigit() and int(title.seed_text) > 0
    pygame.quit()


def test_settlement_screen_offers_garrison_transfer(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.settlement_screen import SettlementScreen
    from tbb.rules.campaign import Campaign
    pygame.init()
    pygame.display.set_mode((1, 1))
    campaign = Campaign(84)
    screen = SettlementScreen(SimpleNamespace())
    sid = campaign.player.settlement_ids[0]
    screen.load(campaign, sid)
    hero_party = campaign.hero_party(campaign.player.key)
    holding = campaign.settlements[sid]
    garrison = campaign.garrison_party(sid)
    soldier = next((uid for uid in garrison.unit_ids
                    if campaign.units[uid].alive), None)
    if hero_party.hex != holding.hex:
        assert screen._attach_reason(soldier) == "hero company is not here"
        assert screen._detach_reason(campaign.player.hero) == \
            "hero company is not here"
    hero_party.move_to(holding.hex)
    assert screen._attach_reason(soldier) is None
    company_man = next(uid for uid in hero_party.unit_ids
                       if uid != campaign.player.hero)
    assert screen._detach_reason(company_man) is None
    assert "the hero never garrisons" in \
        screen._detach_reason(campaign.player.hero)
    labels = [b.label for b in screen._build_buttons()]
    assert any("To company" in label for label in labels)
    assert any("to garrison" in label for label in labels)
    pygame.quit()


def test_settlement_screen_offers_clickable_market_shipping(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.settlement_screen import SettlementScreen
    from tbb.rules.campaign import Campaign
    from tbb.rules import constants as C
    pygame.init()
    pygame.display.set_mode((1, 1))
    campaign = Campaign(13)
    screen = SettlementScreen(SimpleNamespace(audio=SimpleNamespace(
        sfx=lambda *_args: None)))
    screen.load(campaign, campaign.player.settlement_ids[0])
    target = screen._transfer_target()
    assert target is not None
    labels = [button.label for button in screen._build_buttons()]
    assert any("Ship wheat" in label for label in labels)
    assert any("Ship gold" in label for label in labels)
    assert screen._transfer_reason(target, "wheat") is None
    campaign.settlements[screen.sid].wheat = C.MARKET_TRANSFER_WHEAT + 1
    screen.do_transfer("wheat", target)
    assert campaign.settlements[screen.sid].wheat == 1
    assert campaign.settlements[target].wheat > 0
    pygame.quit()


def test_settlement_layout_keeps_shipping_above_training(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.settlement_screen import SettlementScreen
    from tbb.rules.campaign import Campaign
    pygame.init()
    screen = SettlementScreen(SimpleNamespace())
    screen.load(Campaign(13), 1)
    layout = screen.layout_contract()
    assert all(not ship.colliderect(train)
               for ship in layout["ship"] for train in layout["train"])
    pygame.quit()


def test_court_caption_uses_saved_heir_marker(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.court_screen import CourtScreen
    from tbb.rules.campaign import Campaign
    pygame.init()
    campaign = Campaign(734102)
    heir = campaign.current_heir()
    campaign.player.heir = None
    screen = CourtScreen(SimpleNamespace())
    screen.load(campaign)
    assert heir.name in screen.caption()
    assert "Current heir: none" not in screen.caption()
    pygame.quit()


def test_campaign_hud_caption_contains_month_and_season(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from types import SimpleNamespace
    from tbb.app.campaign_screen import CampaignScreen
    from tbb.rules.campaign import Campaign
    pygame.init()
    campaign = Campaign(734102)
    screen = CampaignScreen(SimpleNamespace(art={"terrain": {}}))
    # load is intentionally not needed for this text-only contract.
    screen.campaign = campaign
    assert "Year %d" % campaign.calendar.year in screen.hud_caption()
    assert campaign.calendar.month_label in screen.hud_caption()
    assert campaign.calendar.season_name in screen.hud_caption()
    pygame.quit()


def test_campaign_and_battle_juice_frames_survive_scripted_actions(
        monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from tbb.rules import battle as battle_rules
    from tbb.rules import terrain as G
    from tbb.app.main import App
    from tbb.app.ui import hex_center
    pygame.init()
    app = App()
    try:
        app.new_game(734102)
        screen = app.campaign_screen
        party = app.campaign.hero_party(0)
        target = next((n for n in app.campaign.world.neighbours(party.hex)
                       if app.campaign.world.is_passable(n) and
                       not any(o.hex == n for o in app.campaign.parties)),
                      None)
        if target is not None:
            start = party.hex
            screen.selected_pid = party.pid  # first click selected the band
            x, y = hex_center(*target, screen.ox, screen.oy)
            screen._click_hex((x, y))
            for _ in range(4):  # march tween frames
                app._draw()
            assert party.hex in app.campaign.world.neighbours(start)
            assert screen.anims
        # battle enter: strike, wound flash frames, then leave
        bandit = next(p for p in app.campaign.parties
                      if p.kind == "bandit" and
                      p.alive_units(app.campaign.units))
        battle = battle_rules.battle_from_contact(app.campaign, party,
                                                  bandit)
        app.start_battle(battle)
        bs = app.battle_screen
        attacker = app.campaign.units[battle.sides["attacker"][0]]
        defender = app.campaign.units[battle.sides["defender"][0]]
        bs._fx_from_record({"kind": "melee", "unit": attacker.id,
                            "target": defender.id, "hit": True,
                            "reason": "hit"})
        assert {effect["kind"] for effect in bs.fx} >= {
            "melee_strike", "hit_flash"}
        bs._fx_from_record({"kind": "melee", "unit": attacker.id,
                            "target": defender.id, "hit": True,
                            "reason": "wound"})
        assert any(effect["kind"] == "wound_flash" for effect in bs.fx)
        bs._fx_from_record({"kind": "ranged", "unit": attacker.id,
                            "target": defender.id, "hit": False,
                            "reason": "miss"})
        assert "projectile" in bs.playback_kinds()
        bs.selected_uid = attacker.id
        for _ in range(4):
            app._draw()
        app.finish_battle()
        # scripted defeat still renders the banner
        campaign = app.campaign
        campaign.player.settlement_ids = []
        campaign.player.heir = None
        campaign.units[campaign.player.hero].alive = False
        campaign.check_end_conditions()
        assert campaign.ended and campaign.end_reason == "defeat"
        for _ in range(3):
            app._draw()
    finally:
        app.audio.music_stop()
        pygame.quit()


def test_live_month_end_and_battle_finish_open_epilogue(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    import pygame
    from tbb.app.main import App
    from types import SimpleNamespace
    pygame.init()
    app = App()
    try:
        app.new_game(734102)
        campaign = app.campaign
        campaign.end_turn = lambda: (
            setattr(campaign, "ended", True) or
            setattr(campaign, "end_reason", "victory") or
            SimpleNamespace(ok=True, reason="victory"))
        app.campaign_screen.end_month()
        assert app.mode == "epilogue"
        app.mode = "battle"
        app.finish_battle()
        assert app.mode == "epilogue"
    finally:
        app.audio.music_stop()
        pygame.quit()
