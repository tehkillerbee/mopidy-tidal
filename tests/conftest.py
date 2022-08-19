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


@pytest.fixture
def tidal_search(config, mocker):
    # import lru_cache so we can mock the right name in sys.modules
    from mopidy_tidal import lru_cache

    # remove caching, since the cache is created only at import so otherwise we
    # can't remove it
    mocker.patch("lru_cache.SearchCache", lambda x: x)
    from mopidy_tidal.search import SearchField, fields_meta, tidal_search

    yield tidal_search, SearchField, fields_meta
