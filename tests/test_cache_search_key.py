from __future__ import unicode_literals

from mopidy_tidal.lru_cache import SearchKey


def test_search_key_hashes_are_equal():
    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d2 = {"exact": True, "query": {"album": "TestAlbum", "artist": "TestArtist"}}

    d1_sk = SearchKey(**d1)
    d2_sk = SearchKey(**d2)

    assert hash(d1_sk) == hash(d2_sk)


def test_search_key_hashes_are_different():
    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d2 = {"exact": False, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d3 = {"exact": True, "query": {"album": "TestAlbum2", "artist": "TestArtist"}}

    d1_sk = SearchKey(**d1)
    d2_sk = SearchKey(**d2)
    d3_sk = SearchKey(**d3)

    assert hash(d1_sk) != hash(d2_sk) != hash(d3_sk)


def test_str():
    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d1_sk = SearchKey(**d1)
    assert str(d1_sk) == f"tidal:search:{hash(d1_sk)}"


def test_eq():
    d1 = {"exact": True, "query": {"artist": "TestArtist", "album": "TestAlbum"}}
    d2 = {"exact": False, "query": {"artist": "TestArtist", "album": "TestAlbum"}}

    d1_sk = SearchKey(**d1)
    d2_sk = SearchKey(**d2)
    d3_sk = SearchKey(**d1)
    assert d1_sk == d3_sk
    assert d1_sk != d2_sk
    assert d1_sk != "a string"
