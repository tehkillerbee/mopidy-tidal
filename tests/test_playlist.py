from time import sleep

import pytest
from mopidy.models import Track

from mopidy_tidal.playlists import (
    MopidyPlaylist,
    PlaylistCache,
    Ref,
    TidalPlaylist,
    TidalPlaylistsProvider,
)


@pytest.fixture
def tpp(config, mocker):
    mocker.patch("mopidy_tidal.playlists.Timer")
    backend = mocker.Mock()
    tpp = TidalPlaylistsProvider(backend)
    tpp._playlists = PlaylistCache(persist=False)
    yield tpp, backend


# Currently unimplemented
def test_smoketest_create(tpp):
    tpp, backend = tpp
    tpp.create("new playlist")


def test_smoketest_save(tpp):
    tpp, backend = tpp
    tpp.save("new playlist")


def test_smoketest_delete(tpp):
    tpp, backend = tpp
    tpp.delete("new playlist")


@pytest.fixture
def tidal_playlists(mocker):
    playlists = [
        mocker.Mock(spec=TidalPlaylist, session=mocker.Mock, playlist_id=f"{i}-{i}-{i}")
        for i in range(2)
    ]
    for i, pl in enumerate(playlists):
        pl.id = pl.playlist_id
        pl.name = f"Playlist-{i}"
        pl.last_updated = 10
        pl.num_tracks = 2
    return playlists


def test_lookup_unmodified_cached(tpp, mocker):
    tpp, backend = tpp
    remote_playlist = mocker.Mock(last_updated=9)
    backend._session.get_playlist.return_value = remote_playlist
    playlist = mocker.MagicMock(last_modified=9)
    tpp._playlists["tidal:playlist:0:1:2"] = playlist
    assert tpp.lookup("tidal:playlist:0:1:2") is playlist


def test_refresh_metadata(tpp, mocker, tidal_playlists):
    listener = mocker.Mock()
    mocker.patch("mopidy_tidal.playlists.backend.BackendListener", listener)
    tpp, backend = tpp
    tpp._current_tidal_playlists = tidal_playlists
    assert not len(tpp._playlists_metadata)
    tpp.refresh(include_items=False)

    listener.send.assert_called_once_with("playlists_loaded")

    tracks = [Track(uri="tidal:track:0:0:0")] * 2
    assert dict(tpp._playlists_metadata) == {
        "tidal:playlist:0-0-0": MopidyPlaylist(
            last_modified=10,
            name="Playlist-0",
            uri="tidal:playlist:0-0-0",
            tracks=tracks,
        ),
        "tidal:playlist:1-1-1": MopidyPlaylist(
            last_modified=10,
            name="Playlist-1",
            uri="tidal:playlist:1-1-1",
            tracks=tracks,
        ),
    }


def api_test(tpp, mocker, api_method, tp):
    listener = mocker.Mock()
    mocker.patch("mopidy_tidal.playlists.backend.BackendListener", listener)
    tpp._current_tidal_playlists = [tp]
    tracks = [mocker.Mock() for _ in range(2)]
    for i, track in enumerate(tracks):
        track.id = i
        track.uri = f"tidal:track:{i}:{i}:{i}"
        track.name = f"Track-{i}"
        track.artist.name = "artist_name"
        track.artist.id = i
        track.album.name = "album_name"
        track.album.id = i
        track.duration = 100 + i
        track.track_num = i
        track.disc_num = i
    api_method.return_value = tracks
    api_method.__name__ = "get_playlist_tracks"

    tpp.refresh(include_items=True)
    listener.send.assert_called_once_with("playlists_loaded")
    assert len(tpp._playlists) == 1
    playlist = tpp._playlists["tidal:playlist:1-1-1"]
    assert isinstance(playlist, MopidyPlaylist)
    assert playlist.last_modified == 10
    assert playlist.name == "Playlist-1"
    assert playlist.uri == "tidal:playlist:1-1-1"
    assert len(playlist.tracks) == 2 * len(api_method.mock_calls)
    attr_map = {"disc_num": "disc_no"}
    assert all(
        getattr(orig_tr, k) == getattr(tr, attr_map.get(k, k))
        for orig_tr, tr in zip(tracks, playlist.tracks)
        for k in {"name", "uri", "disc_num"}
    )


def test_refresh_new_api(tpp, mocker):
    tpp, backend = tpp
    session = backend._session
    session.mock_add_spec([])
    tp = mocker.Mock(spec=TidalPlaylist, session=mocker.Mock, playlist_id="1-1-1")
    tp.id = tp.playlist_id
    tp.name = "Playlist-1"
    tp.last_updated = 10
    tp.tracks = mocker.Mock()
    api_method = tp.tracks
    api_test(tpp, mocker, api_method, tp)


def test_as_list(tpp, mocker, tidal_playlists):
    tpp, backend = tpp
    mocker.patch("mopidy_tidal.playlists.get_items", lambda x: x)
    backend._session.configure_mock(**{"user.favorites.playlists": tidal_playlists[:1]})
    backend._session.user.playlists.return_value = tidal_playlists[1:]
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
    ]


def test_prevent_duplicate_playlist_sync(tpp, mocker, tidal_playlists):
    tpp, backend = tpp
    mocker.patch("mopidy_tidal.playlists.get_items", lambda x: x)
    backend._session.configure_mock(**{"user.favorites.playlists": tidal_playlists[:1]})
    backend._session.user.playlists.return_value = tidal_playlists[1:]
    tpp.as_list()
    p = mocker.Mock(spec=TidalPlaylist, session=mocker.Mock, playlist_id="2-2-2")
    backend._session.user.playlists.return_value.append(p)
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
    ]


def test_playlist_sync_downtime(mocker, tidal_playlists, config):
    backend = mocker.Mock()
    tpp = TidalPlaylistsProvider(backend)
    tpp._playlists = PlaylistCache(persist=False)
    mocker.patch("mopidy_tidal.playlists.get_items", lambda x: x)
    mocker.patch(
        "mopidy_tidal.playlists.TidalPlaylistsProvider.PLAYLISTS_SYNC_DOWNTIME_S", 0.1
    )
    backend._session.configure_mock(**{"user.favorites.playlists": tidal_playlists[:1]})
    backend._session.user.playlists.return_value = tidal_playlists[1:]
    tpp.as_list()
    p = mocker.Mock(spec=TidalPlaylist, session=mocker.Mock, playlist_id="2-2-2")
    p.id = p.playlist_id
    p.num_tracks = 2
    p.name = "Playlist-2"
    p.last_updated = 10
    backend._session.user.playlists.return_value.append(p)
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
    ]
    sleep(0.1)
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
        Ref(name="Playlist-2", type="playlist", uri="tidal:playlist:2-2-2"),
    ]


def test_update_changes(tpp, mocker, tidal_playlists):
    tpp, backend = tpp
    tpp._playlists_metadata.update(
        {
            "tidal:playlist:0-0-0": MopidyPlaylist(
                last_modified=10, name="Playlist-0", uri="tidal:playlist:0-0-0"
            ),
            "tidal:playlist:1-1-1": MopidyPlaylist(
                last_modified=9, name="Playlist-1", uri="tidal:playlist:1-1-1"
            ),
        }
    )

    mocker.patch("mopidy_tidal.playlists.get_items", lambda x: x)
    backend._session.configure_mock(**{"user.favorites.playlists": tidal_playlists[:1]})
    backend._session.user.playlists.return_value = tidal_playlists[1:]
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
    ]


def test_update_no_changes(tpp, mocker, tidal_playlists):
    tpp, backend = tpp
    tpp._playlists_metadata.update(
        {
            "tidal:playlist:0-0-0": MopidyPlaylist(
                last_modified=10, name="Playlist-0", uri="tidal:playlist:0-0-0"
            ),
            "tidal:playlist:1-1-1": MopidyPlaylist(
                last_modified=10, name="Playlist-1", uri="tidal:playlist:1-1-1"
            ),
        }
    )

    mocker.patch("mopidy_tidal.playlists.get_items", lambda x: x)
    backend._session.configure_mock(**{"user.favorites.playlists": tidal_playlists[:1]})
    backend._session.user.playlists.return_value = tidal_playlists[1:]
    assert tpp.as_list() == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0-0-0"),
        Ref(name="Playlist-1", type="playlist", uri="tidal:playlist:1-1-1"),
    ]


def test_lookup_modified_cached(tpp, mocker):
    tpp, backend = tpp
    remote_playlist = mocker.Mock(last_updated=10)
    backend._session.get_playlist.return_value = remote_playlist
    playlist = mocker.MagicMock(last_modified=9)
    tpp._playlists["tidal:playlist:0:1:2"] = playlist
    assert tpp.lookup("tidal:playlist:0:1:2") is playlist


def test_get_items_none(tpp):
    tpp, backend = tpp
    assert not tpp.get_items("tidal:playlist:0-1-2")


def test_get_items_none_upstream(tpp, mocker):
    tpp, backend = tpp
    backend._session.get_playlist.return_value = None
    tracks = [mocker.Mock() for _ in range(2)]
    for i, track in enumerate(tracks):
        track.uri = f"tidal:track:{i}:{i}:{i}"
        track.name = f"Track-{i}"

    playlist = mocker.MagicMock(last_modified=9, tracks=tracks)
    tpp._playlists["tidal:playlist:0-1-2"] = playlist
    assert tpp.get_items("tidal:playlist:0-1-2") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]


def test_get_items_playlists(tpp, mocker):
    tpp, backend = tpp
    backend._session.get_playlist.return_value = mocker.Mock(last_updated=9)
    tracks = [mocker.Mock() for _ in range(2)]
    for i, track in enumerate(tracks):
        track.uri = f"tidal:track:{i}:{i}:{i}"
        track.name = f"Track-{i}"

    playlist = mocker.MagicMock(last_modified=9, tracks=tracks)
    tpp._playlists["tidal:playlist:0-1-2"] = playlist
    assert tpp.get_items("tidal:playlist:0-1-2") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]


def test_get_items_playlists_no_updated(tpp, mocker):
    tpp, backend = tpp
    backend._session.get_playlist.return_value = mocker.Mock(spec={})
    tracks = [mocker.Mock() for _ in range(2)]
    for i, track in enumerate(tracks):
        track.uri = f"tidal:track:{i}:{i}:{i}"
        track.name = f"Track-{i}"

    playlist = mocker.MagicMock(last_modified=9, tracks=tracks)
    tpp._playlists["tidal:playlist:0-1-2"] = playlist
    assert tpp.get_items("tidal:playlist:0-1-2") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]


def test_get_items_mix(tpp, mocker):
    tpp, backend = tpp
    tracks = [mocker.Mock() for _ in range(2)]
    for i, track in enumerate(tracks):
        track.id = i
        track.uri = f"tidal:track:{i}:{i}:{i}"
        track.name = f"Track-{i}"
        track.artist.name = "artist_name"
        track.artist.id = i
        track.album.name = "album_name"
        track.album.id = i
        track.duration = 100
        track.track_num = i
        track.disc_num = i
    tidal_playlist = mocker.Mock(last_updated=9)
    tidal_playlist.items.return_value = tracks
    backend._session.mix.return_value = tidal_playlist

    playlist = mocker.MagicMock(last_modified=9, tracks=tracks)
    tpp._playlists["tidal:mix:0-1-2"] = playlist
    assert tpp.get_items("tidal:mix:0-1-2") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]
