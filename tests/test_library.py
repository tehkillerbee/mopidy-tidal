import pytest
from mopidy.models import Album, Artist, Image, SearchResult, Track

from mopidy_tidal.library import TidalLibraryProvider


@pytest.fixture
def tlp(mocker, config):
    backend = mocker.Mock()
    lp = TidalLibraryProvider(backend)
    for cache_type in {"artist", "album", "track", "playlist"}:
        getattr(lp, f"_{cache_type}_cache")._persist = False

    return lp, backend


def test_search_no_match(tlp, tidal_search):
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


def test_get_track_images(tlp, mocker):
    tlp, backend = tlp
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    backend._session.get_album.return_value = get_album
    assert tlp.get_images(uris) == {
        uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]
    }
    backend._session.get_album.assert_called_once_with("1-1-1")


@pytest.mark.xfail
def test_track_cache(tlp, mocker):
    # I think the caching logic is broken here
    tlp, backend = tlp
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    backend._session.get_album.return_value = get_album
    first = tlp.get_images(uris)
    assert first == {uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]}
    assert tlp.get_images(uris) == first
    backend._session.get_album.assert_called_once_with("1-1-1")


@pytest.mark.parametrize("field", ("artist", "album", "track"))
def test_get_distinct_root(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    thing = mocker.Mock()
    thing.name = "Thing"
    session.configure_mock(**{f"user.favorites.{field}s.return_value": [thing]})
    res = tlp.get_distinct(field)
    assert res[0] == "Thing [TIDAL]"
    assert len(res) == 1


def test_get_distinct_root_nonsuch(tlp, mocker):
    tlp, backend = tlp
    assert not tlp.get_distinct("nonsuch")


def test_get_distinct_query_nonsuch(tlp, mocker):
    tlp, backend = tlp
    assert not tlp.get_distinct("nonsuch", query={"any": "any"})


@pytest.mark.parametrize("field", ("artist", "track"))
def test_get_distinct_ignore_query(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    thing = mocker.Mock()
    thing.name = "Thing"
    session.configure_mock(**{f"user.favorites.{field}s.return_value": [thing]})
    res = tlp.get_distinct(field, query={"any": "any"})
    assert res[0] == "Thing [TIDAL]"
    assert len(res) == 1


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_old_api(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    tidal_search = mocker.Mock()
    artist = mocker.Mock(spec=Artist)
    artist.uri = "tidal:artist:1"
    tidal_search.return_value = ([artist], [], [])
    thing = mocker.Mock()
    thing.name = "Thing"
    session.get_artist_albums.return_value = [thing]
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    res = tlp.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)
    session.get_artist_albums.assert_called_once_with("1")
    assert len(res) == 1
    assert res[0] == "Thing [TIDAL]"


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_no_results(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    tidal_search = mocker.Mock()
    tidal_search.return_value = ([], [], [])
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert not tlp.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_new_api(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("tidal_search", "artist", "artist.get_albums"))

    artist = mocker.Mock()
    artist.uri = "tidal:artist:1"
    thing = mocker.Mock()
    thing.name = "Thing"
    artist.get_albums.return_value = [thing]

    tidal_search = mocker.Mock()
    tidal_search.return_value = ([artist], [], [])
    session.artist.return_value = artist
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    res = tlp.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)
    session.artist.assert_called_once_with("1")
    artist.get_albums.assert_called_once_with()
    assert len(res) == 1
    assert res[0] == "Thing [TIDAL]"


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_new_api_no_artist(tlp, mocker, field):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("tidal_search", "artist", "artist.get_albums"))

    artist = mocker.Mock()
    artist.uri = "tidal:artist:1"

    tidal_search = mocker.Mock()
    tidal_search.return_value = ([artist], [], [])
    session.artist.return_value = None
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert not tlp.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)
    session.artist.assert_called_once_with("1")
