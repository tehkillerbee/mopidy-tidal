from __future__ import unicode_literals

from mopidy_tidal.lru_cache import SearchKey


def test_hashes_of_equal_objects_are_equal():
    params = dict(exact=True, query=dict(artist="Arty", album="Alby"))
    assert SearchKey(**params) == SearchKey(**params)

    assert hash(SearchKey(**params)) == hash(SearchKey(**params))


def test_hashes_of_different_objects_are_different():
    key_1 = SearchKey(exact=True, query=dict(artist="Arty", album="Alby"))
    key_2 = SearchKey(exact=False, query=dict(artist="Arty", album="Alby"))
    key_3 = SearchKey(exact=True, query=dict(artist="Arty", album="Albion"))

    assert hash(key_1) != hash(key_2) != hash(key_3)


def test_as_str_constructs_uri_from_hash():
    key = SearchKey(exact=True, query=dict(artist="Arty", album="Alby"))

    assert str(key) == f"tidal:search:{hash(key)}"
