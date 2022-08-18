import pytest

from mopidy_tidal import context


@pytest.fixture
def config(tmp_path):

    cfg = {
        "core": {
            "cache_dir": str(tmp_path),
        }
    }
    context.set_config(cfg)
    yield cfg
    context.set_config(None)
