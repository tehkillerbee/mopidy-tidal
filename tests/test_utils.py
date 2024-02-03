from mopidy_tidal.utils import apply_watermark, remove_watermark


def test_apply_watermark_adds_tidal():
    assert apply_watermark("track") == "track [TIDAL]"


def test_remove_watermark_removes_tidal_if_present():
    assert remove_watermark(None) is None
    assert remove_watermark("track [TIDAL]") == "track"
