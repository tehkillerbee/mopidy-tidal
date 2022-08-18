import pytest
from mopidy.models import Album, Artist, SearchResult, Track

from mopidy_tidal.library import TidalLibraryProvider


@pytest.fixture
def tlp(mocker, config):
    backend = mocker.Mock()
    lp = TidalLibraryProvider(backend)
    for cache_type in {"artist", "album", "track", "playlist"}:
        getattr(lp, f"_{cache_type}_cache")._persist = False

    return lp, backend


def test_search_no_match(tlp):
    tlp, backend = tlp
    assert not tlp.search("nonsuch")


def test_search(mocker, tlp):
    tlp, backend = tlp
    query, exact = object(), object()
    artists = [mocker.Mock(spec=Artist)]
    albums = [mocker.Mock(spec=Album)]
    tracks = [mocker.Mock(spec=Track)]
    tidal_search = mocker.Mock()
    tidal_search.return_value = (artists, albums, tracks)
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert tlp.search(query=query, exact=exact) == SearchResult(
        artists=artists, albums=albums, tracks=tracks
    )
    tidal_search.assert_called_once_with(backend._session, query=query, exact=exact)
