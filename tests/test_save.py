import json
from tbb.rules.campaign import Campaign
from tbb.rules import persistence


def test_full_campaign_save_roundtrip_including_battle_and_shaken(tmp_path):
    campaign = Campaign(34)
    party = campaign.hero_party(0)
    campaign.units[campaign.player.hero].shaken = True
    campaign._make_battle(party, campaign.hero_party(1))
    path = persistence.save(campaign, "mid", tmp_path)
    loaded = persistence.load("mid", tmp_path)
    assert persistence.canonical(campaign) == persistence.canonical(loaded)
    assert loaded.pending_battles
    from pathlib import Path
    raw = json.loads(Path(path).read_text())
    raw["version"] = 1
    Path(path).write_text(json.dumps(raw))
    try:
        persistence.load("mid", tmp_path)
    except ValueError as error:
        assert "unsupported save version" in str(error)
    else:
        raise AssertionError("old save version was accepted")
