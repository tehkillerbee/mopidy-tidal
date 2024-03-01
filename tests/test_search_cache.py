from mopidy_tidal.lru_cache import SearchCache, SearchKey


def test_search_cache_returns_cached_value_if_present(mocker):
    search_function = mocker.Mock()
    cache = SearchCache(search_function)
    query = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    search_key = SearchKey(**query)
    cache[str(search_key)] = mocker.sentinel.results

    results = cache("arg", **query)

    assert results is mocker.sentinel.results
    search_function.assert_not_called()


def test_search_defers_to_search_function_if_not_present_and_stores(mocker):
    search_function = mocker.Mock(return_value=mocker.sentinel.results)
    cache = SearchCache(search_function)
    query = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    search_key = SearchKey(**query)
    assert str(search_key) not in cache

    results = cache("arg", **query)

    assert results is mocker.sentinel.results
    assert str(search_key) in cache
    search_function.assert_called_once_with("arg", **query)
