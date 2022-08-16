from mopidy_tidal.lru_cache import SearchCache, SearchKey


def test_search_cache_cached(mocker, config):
    func = mocker.Mock()
    cache = SearchCache(func)
    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d1_sk = SearchKey(**d1)
    uniq = object()
    cache[str(d1_sk)] = uniq
    assert cache("arg", **d1) is uniq


def test_search_cache_not_cached(mocker, config):
    func_ret = object
    func = mocker.Mock()
    func.return_value = func_ret
    cache = SearchCache(func)

    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d1_sk = SearchKey(**d1)
    assert str(d1_sk) not in cache
    assert cache("arg", **d1) is func_ret
    func.assert_called_once_with("arg", **d1)
