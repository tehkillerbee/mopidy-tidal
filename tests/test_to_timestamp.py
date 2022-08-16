from datetime import datetime

import pytest

from mopidy_tidal.helpers import to_timestamp


@pytest.mark.parametrize(
    "dt, res",
    [
        (None, 0),
        ("2022-08-06 12:38:40", 1659782320),
        (datetime(2022, 1, 5), 1641337200),
        (12, 12),
    ],
)
def test_to_timestamp(dt, res):
    assert to_timestamp(dt) == res
