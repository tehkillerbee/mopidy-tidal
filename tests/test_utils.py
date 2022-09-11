from mopidy_tidal.utils import apply_watermark, remove_watermark


def test_apply_watermark():
    assert apply_watermark("track") == "track [TIDAL]"


def test_remove_watermark():
    assert remove_watermark(None) is None
    assert remove_watermark("track [TIDAL]") == "track"
