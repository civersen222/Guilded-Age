from tools.audio_foundry.derive import derive_for_event


def test_uses_title_and_desc():
    p = derive_for_event({"id": "e1", "title": "The Harvest Fails", "desc": "Famine grips the land."})
    assert "Harvest" in p.tts_line and "Famine" in p.tts_line
    assert p.sfx_caption == "The Harvest Fails"


def test_missing_fields_fallback():
    p = derive_for_event({"id": "e2"})
    assert p.tts_line == "e2"
    assert p.sfx_caption == "generic event sting"