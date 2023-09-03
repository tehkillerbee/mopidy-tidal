from typing import Iterable
from unittest.mock import Mock

import pytest
from tidalapi import Genre, Session
from tidalapi.album import Album
from tidalapi.artist import Artist
from tidalapi.media import Track
from tidalapi.mix import Mix
from tidalapi.page import Page, PageCategory
from tidalapi.playlist import UserPlaylist

from mopidy_tidal import context
from mopidy_tidal.backend import TidalBackend
from mopidy_tidal.context import set_config


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
            "lazy": False,
            "login_method": "BLOCK",
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


def counter(msg: str):
    """A counter for providing sequential names."""
    x = 0
    while True:
        yield msg.format(x)
        x += 1


# Giving each mock a unique name really helps when inspecting funny behaviour.
track_counter = counter("Mock Track #{}")
album_counter = counter("Mock Album #{}")
artist_counter = counter("Mock Artist #{}")
page_counter = counter("Mock Page #{}")
mix_counter = counter("Mock Mix #{}")
genre_counter = counter("Mock Genre #{}")


def _make_tidal_track(
    id: int,
    artist: Artist,
    album: Album,
    name: str | None = None,
    duration: int | None = None,
):
    track = Mock(spec=Track, name=next(track_counter))
    track.id = id
    track.name = name or f"Track-{id}"
    track.artist = artist
    track.album = album
    track.uri = f"tidal:track:{artist.id}:{album.id}:{id}"
    track.duration = duration or (100 + id)
    track.track_num = id
    track.disc_num = id
    return track


def _make_tidal_artist(*, name: str, id: int, top_tracks: list[Track] | None = None):
    """A list of tidal artists."""
    artist = Mock(spec=Artist, name=next(artist_counter))
    artist.id = id  # Can't set id when making a mock
    artist.get_top_tracks.return_value = top_tracks
    artist.name = name  # other name was the *mock's* name
    return artist


def _make_tidal_album(*, name: str, id: int, tracks: list[dict] | None = None):
    album = Mock(spec=Album, name=next(album_counter))
    album.name = name
    album.id = id
    tracks = tracks or []
    tracks = [_make_tidal_track(**spec, album=album) for spec in tracks]
    album.tracks.return_value = tracks
    return album


def _make_tidal_page(*, title: str, categories: list[PageCategory], api_path: str):
    return Mock(spec=Page, title=title, categories=categories, api_path=api_path)


def _make_tidal_mix(*, title: str, sub_title: str, id: int):
    return Mock(
        spec=Mix, title=title, sub_title=sub_title, name=next(mix_counter), id=str(id)
    )


def _make_tidal_genre(*, name: str, path: str):
    genre = Mock(sepc=Genre, name=next(genre_counter), path=path)
    genre.name = name
    return genre


@pytest.fixture()
def make_tidal_genre():
    return _make_tidal_genre


@pytest.fixture()
def make_tidal_artist():
    return _make_tidal_artist


@pytest.fixture()
def make_tidal_album():
    return _make_tidal_album


@pytest.fixture()
def make_tidal_track():
    return _make_tidal_track


@pytest.fixture()
def make_tidal_page():
    return _make_tidal_page


@pytest.fixture()
def make_tidal_mix():
    return _make_tidal_mix


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
        artist.get_top_tracks.return_value = [
            _make_tidal_track((i + 1) * 100, artist, album)
        ]
    return artists


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
        album.tracks.return_value = [_make_tidal_track(i, artist, album)]
    return albums


@pytest.fixture
def tidal_tracks(mocker, tidal_artists, tidal_albums):
    """A list of tidal tracks."""
    return [
        _make_tidal_track(i, artist, album)
        for i, (artist, album) in enumerate(zip(tidal_artists, tidal_albums))
    ]


def make_playlist(playlist_id, tracks):
    playlist = Mock(spec=UserPlaylist, session=Mock())
    playlist.name = f"Playlist-{playlist_id}"
    playlist.id = str(playlist_id)
    playlist.uri = f"tidal:playlist:{playlist_id}"
    playlist.tracks = tracks
    playlist.num_tracks = len(tracks)
    playlist.last_updated = 10
    return playlist


@pytest.fixture
def tidal_playlists(mocker, tidal_tracks):
    return [
        make_playlist(101, tidal_tracks[:2]),
        make_playlist(222, tidal_tracks[1:]),
    ]


def compare_track(tidal, mopidy):
    assert tidal.uri == mopidy.uri
    assert tidal.full_name == mopidy.name
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


def compare_playlist(tidal, mopidy):
    assert tidal.uri == mopidy.uri
    assert tidal.name == mopidy.name
    _compare(tidal.tracks, mopidy.tracks, "track")


_compare_map = {
    "artist": compare_artist,
    "album": compare_album,
    "track": compare_track,
    "playlist": compare_playlist,
}


def _compare(tidal: Iterable, mopidy: Iterable, type: str):
    assert len(tidal) == len(mopidy)
    for t, m in zip(tidal, mopidy):
        _compare_map[type](t, m)


@pytest.fixture
def compare():
    """Compare artists, tracks or albums.

    Args:
        tidal: The tidal tracks.
        mopidy: The mopidy tracks.
        type: The type of comparison: one of "artist", "album" or "track".
    """

    return _compare


@pytest.fixture
def get_backend(mocker):
    def _get_backend(config=mocker.MagicMock(), audio=mocker.Mock()):
        backend = TidalBackend(config, audio)
        session_factory = mocker.Mock()
        session = mocker.Mock()
        session.token_type = "token_type"
        session.session_id = "session_id"
        session.access_token = "access_token"
        session.refresh_token = "refresh_token"
        session_factory.return_value = session
        mocker.patch("mopidy_tidal.backend.Session", session_factory)
        return backend, config, audio, session_factory, session

    yield _get_backend
    set_config(None)


class SessionForTest(Session):
    """Session has an attribute genre which is set in __init__ doesn't exist on
    the class.  Thus mock gets the spec wrong, i.e. forbids access to genre.
    This is a bug in Session, but until it's fixed we mock it here.

    See https://docs.python.org/3/library/unittest.mock.html#auto-speccing

    Tracked at https://github.com/tamland/python-tidal/issues/192
    """

    genre = None


@pytest.fixture
def session(mocker):
    return mocker.Mock(spec=SessionForTest)


@pytest.fixture
def backend(mocker, session):
    return mocker.Mock(session=session)
