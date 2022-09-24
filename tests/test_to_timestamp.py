from datetime import datetime, timezone

import pytest

from mopidy_tidal.helpers import to_timestamp


@pytest.mark.parametrize(
    "dt, res",
    [
        (None, 0),
        ("2022-08-06 12:38:40+00:00", 1659789520),
        (datetime(2022, 1, 5, tzinfo=timezone.utc), 1641340800),
        (12, 12),
    ],
)
def test_to_timestamp(dt, res):
    assert to_timestamp(dt) == res
