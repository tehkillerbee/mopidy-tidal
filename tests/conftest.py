from unittest.mock import Mock

import pytest
from tidalapi.album import Album
from tidalapi.artist import Artist
from tidalapi.media import Track

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
    def _compare(tidal, mopidy, fn: str):
        assert len(tidal) == len(mopidy)
        for t, m in zip(tidal, mopidy):
            _compare_map[fn](t, m)

    return _compare
