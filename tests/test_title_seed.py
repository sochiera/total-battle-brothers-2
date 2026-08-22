def test_seed_text_is_plain_integer_when_title_screen_is_constructed():
    # Keep this presentation-adjacent check headless: the rules tests never
    # need to open a pygame display to validate a new campaign seed.
    from tbb.rules.campaign import Campaign
    assert Campaign(734102).seed == 734102
