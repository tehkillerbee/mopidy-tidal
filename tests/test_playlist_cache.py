from pathlib import Path

import pytest

from mopidy_tidal.playlists import PlaylistCache, PlaylistMetadataCache, TidalPlaylist


def test_metadata_cache(config):
    cache = PlaylistMetadataCache(directory="cache")
    uniq = object()
    outf = (
        Path(config["core"]["cache_dir"], "tidal/cache/playlist_metadata/00")
        / "tidal:playlist:00-1-2.cache"
    )
    assert not outf.exists()
    cache["tidal:playlist:00-1-2"] = uniq
    assert outf.exists()
    assert cache["tidal:playlist:00-1-2"] is uniq


def test_cached_as_str(config):
    cache = PlaylistCache(persist=False)
    uniq = object()
    cache["tidal:playlist:0-1-2"] = uniq
    assert cache["tidal:playlist:0-1-2"] is uniq
    assert cache["0-1-2"] is uniq


def test_not_updated(config, mocker):
    cache = PlaylistCache(persist=False)
    session = mocker.Mock()
    key = mocker.Mock(spec=TidalPlaylist, session=session, playlist_id="0-1-2")
    key.id = "0-1-2"
    key.last_updated = 10

    playlist = mocker.Mock(last_modified=10)
    playlist.last_modified = 10
    cache["tidal:playlist:0-1-2"] = playlist
    assert cache[key] is playlist


def test_updated(config, mocker):
    cache = PlaylistCache(persist=False)
    session = mocker.Mock()
    resp = mocker.Mock(headers={"etag": None})
    session.request.request.return_value = resp
    key = mocker.Mock(spec=TidalPlaylist, session=session, playlist_id="0-1-2")
    key.id = "0-1-2"
    key.last_updated = 10

    playlist = mocker.Mock(last_modified=9)
    cache["tidal:playlist:0-1-2"] = playlist
    with pytest.raises(KeyError):
        cache[key]
