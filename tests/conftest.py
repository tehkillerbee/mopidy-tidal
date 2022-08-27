from typing import Iterable
from unittest.mock import Mock

import pytest
from tidalapi.album import Album
from tidalapi.artist import Artist
from tidalapi.media import Track

from mopidy_tidal import context


@pytest.fixture
def config(tmp_path):
    """Set up config.

    This fixture sets up config in context and removes it after the test.  It
    yields the config dictionary, so if you edit the dictionary you are editing
    the config.
    """

    cfg = {
        "core": {
            "cache_dir": str(tmp_path),
            "data_dir": str(tmp_path),
        },
        "tidal": {
            "client_id": "client_id",
            "client_secret": "client_secret",
            "quality": "LOSSLESS",
        },
    }
    context.set_config(cfg)
    yield cfg
    context.set_config(None)


@pytest.fixture
def tidal_search(config, mocker):
    """Provide an uncached tidal_search.

    Tidal search is cached with a decorator, so we have to mock before we
    import anything.  No test should import anything from
    `mopidy_tidal.search`.  Instead use this fixture."""
    # import lru_cache so we can mock the right name in sys.modules without it
    # being overriden.
    from mopidy_tidal import lru_cache  # noqa

    # remove caching, since the cache is created only at import so otherwise we
    # can't remove it
    mocker.patch("lru_cache.SearchCache", lambda x: x)
    from mopidy_tidal.search import tidal_search

    yield tidal_search


def make_track(track_id, artist, album):
    track = Mock(spec=Track, name=f"Track: {track_counter()}")
    track.id = track_id
    track.name = f"Track-{track_id}"
    track.artist = artist
    track.album = album
    track.uri = f"tidal:track:{artist.id}:{album.id}:{track_id}"
    track.duration = 100 + track_id
    track.track_num = track_id
    track.disc_num = track_id
    return track


@pytest.fixture()
def tidal_artists(mocker):
    """A list of tidal artists."""
    artists = [mocker.Mock(spec=Artist, name=f"Artist-{i}") for i in range(2)]
    album = mocker.Mock(spec=Album)
    album.name = "demo album"
    album.id = 7
    for i, artist in enumerate(artists):
        artist.id = i
        artist.name = f"Artist-{i}"
        artist.get_top_tracks.return_value = [make_track((i + 1) * 100, artist, album)]
    return artists


def track_counter(i=[0]):
    i[0] += 1
    return i


@pytest.fixture()
def tidal_albums(mocker):
    """A list of tidal albums."""
    albums = [mocker.Mock(spec=Album, name=f"Album-{i}") for i in range(2)]
    artist = mocker.Mock(spec=Artist, name="Album Artist")
    artist.name = "Album Artist"
    artist.id = 1234
    for i, album in enumerate(albums):
        album.id = i
        album.name = f"Album-{i}"
        album.artist = artist
        album.tracks.return_value = [make_track(i, artist, album)]
    return albums


@pytest.fixture
def tidal_tracks(mocker, tidal_artists, tidal_albums):
    """A list of tidal tracks."""
    return [
        make_track(i, artist, album)
        for i, (artist, album) in enumerate(zip(tidal_artists, tidal_albums))
    ]


def compare_track(tidal, mopidy):
    assert tidal.uri == mopidy.uri
    assert tidal.name == mopidy.name
    assert tidal.duration * 1000 == mopidy.length
    assert tidal.disc_num == mopidy.disc_no
    assert tidal.track_num == mopidy.track_no
    compare_artist(tidal.artist, list(mopidy.artists)[0])
    compare_album(tidal.album, mopidy.album)


def compare_artist(tidal, mopidy):
    assert tidal.name == mopidy.name
    assert f"tidal:artist:{tidal.id}" == mopidy.uri


def compare_album(tidal, mopidy):
    assert tidal.name == mopidy.name
    assert f"tidal:album:{tidal.id}" == mopidy.uri


_compare_map = {
    "artist": compare_artist,
    "album": compare_album,
    "track": compare_track,
}


@pytest.fixture
def compare():
    """Compare artists, tracks or albums.

    Args:
        tidal: The tidal tracks.
        mopidy: The mopidy tracks.
        type: The type of comparison: one of "artist", "album" or "track".
    """

    def _compare(tidal: Iterable, mopidy: Iterable, type: str):
        assert len(tidal) == len(mopidy)
        for t, m in zip(tidal, mopidy):
            _compare_map[type](t, m)

    return _compare
