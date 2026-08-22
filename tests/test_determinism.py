from tbb.rules.campaign import Campaign
from tbb.rules import persistence


def test_same_seed_same_campaign_and_rng_stream(tmp_path):
    first, second = Campaign(456789), Campaign(456789)
    assert persistence.canonical(first) == persistence.canonical(second)
    first.end_turn()
    second.end_turn()
    assert persistence.canonical(first) == persistence.canonical(second)
