import pytest
from mopidy.models import Album, Artist, Image, Ref, SearchResult, Track
from tidalapi.playlist import Playlist

from mopidy_tidal.library import HTTPError, TidalLibraryProvider


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
    backend._session.album.return_value = get_album
    assert tlp.get_images(uris) == {
        uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]
    }
    backend._session.album.assert_called_once_with("1-1-1")


@pytest.mark.xfail
def test_track_cache(tlp, mocker):
    # I think the caching logic is broken here
    tlp, backend = tlp
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    backend._session.album.return_value = get_album
    first = tlp.get_images(uris)
    assert first == {uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]}
    assert tlp.get_images(uris) == first
    backend._session.album.assert_called_once_with("1-1-1")


def test_get_noimages(tlp, mocker):
    tlp, backend = tlp
    uris = ["tidal:nonsuch:0-0-0:1-1-1:2-2-2"]
    backend._session.mock_add_spec([])
    assert tlp.get_images(uris) == {uris[0]: []}


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


def test_browse_wrong_uri(tlp):
    tlp, backend = tlp
    assert not tlp.browse("")
    assert not tlp.browse("spotify:something:something_else")
    assert not tlp.browse("tidal:album:oneid:oneidtoomany")


def test_browse_root(tlp):
    tlp, backend = tlp
    assert tlp.browse("tidal:directory") == [
        Ref(name="Genres", type="directory", uri="tidal:genres"),
        Ref(name="Moods", type="directory", uri="tidal:moods"),
        Ref(name="Mixes", type="directory", uri="tidal:mixes"),
        Ref(name="My Artists", type="directory", uri="tidal:my_artists"),
        Ref(name="My Albums", type="directory", uri="tidal:my_albums"),
        Ref(name="My Playlists", type="directory", uri="tidal:my_playlists"),
        Ref(name="My Tracks", type="directory", uri="tidal:my_tracks"),
    ]


def test_browse_artists(tlp, mocker, tidal_artists):
    tlp, backend = tlp
    session = backend._session
    session.user.favorites.artists = tidal_artists
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert tlp.browse("tidal:my_artists") == [
        Ref(name="Artist-0", type="artist", uri="tidal:artist:0"),
        Ref(name="Artist-1", type="artist", uri="tidal:artist:1"),
    ]


def test_browse_albums(tlp, mocker, tidal_albums):
    tlp, backend = tlp
    session = backend._session
    session.user.favorites.albums = tidal_albums
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert tlp.browse("tidal:my_albums") == [
        Ref(name="Album-0", type="album", uri="tidal:album:0"),
        Ref(name="Album-1", type="album", uri="tidal:album:1"),
    ]


def test_browse_tracks(tlp, mocker, tidal_tracks):
    tlp, backend = tlp
    session = backend._session
    session.user.favorites.tracks = tidal_tracks
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert tlp.browse("tidal:my_tracks") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]


def test_browse_playlists(tlp, mocker):
    tlp, backend = tlp
    as_list = mocker.Mock()
    uniq = object()
    as_list.return_value = uniq
    backend.playlists.as_list = as_list
    assert tlp.browse("tidal:my_playlists") is uniq
    as_list.assert_called_once_with()


def test_moods_new_api(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("moods",))
    mood = mocker.Mock(spec=("title", "title", "api_path"))
    mood.title = "Mood-1"
    mood.api_path = "0/0/1"
    session.moods.return_value = [mood]
    assert tlp.browse("tidal:moods") == [
        Ref(name="Mood-1", type="directory", uri="tidal:mood:1")
    ]
    session.moods.assert_called_once_with()


def test_mixes_new_api(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("mixes",))
    mix = mocker.Mock()
    mix.title = "Mix-1"
    mix.sub_title = "[Subtitle]"
    mix.id = "1"
    session.mixes.return_value = [mix]
    assert tlp.browse("tidal:mixes") == [
        Ref(name="Mix-1 ([Subtitle])", type="playlist", uri="tidal:mix:1")
    ]
    session.mixes.assert_called_once_with()


def test_genres_new_api(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(
        (
            "genre",
            "genre.get_genres",
        )
    )
    genre = mocker.Mock(spec=("name", "path"))
    genre.name = "Genre-1"
    genre.path = "1"
    session.genre.get_genres.return_value = [genre]
    assert tlp.browse("tidal:genres") == [
        Ref(name="Genre-1", type="directory", uri="tidal:genre:1")
    ]
    session.genre.get_genres.assert_called_once_with()


def test_specific_album_new_api(tlp, mocker, tidal_albums):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("album",))
    album = tidal_albums[0]
    session.album.return_value = album
    assert tlp.browse("tidal:album:1") == [
        Ref(name="Track-0", type="track", uri="tidal:track:1234:0:0")
    ]
    session.album.assert_called_once_with("1")
    album.tracks.assert_called_once_with()


def test_specific_album_new_api_none(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("album",))
    session.album.return_value = None
    assert not tlp.browse("tidal:album:1")
    session.album.assert_called_once_with("1")


def test_specific_playlist_new_api(tlp, mocker, tidal_tracks):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("playlist",))
    playlist = mocker.Mock(name="Playlist")
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "playlist"
    session.playlist.return_value = playlist

    tracks = tlp.browse("tidal:playlist:1")
    assert tracks[:2] == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]

    session.playlist.assert_called_once_with("1")
    playlist.tracks.assert_has_calls([mocker.call(100, 0)])


def test_specific_mood_new_api(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("moods",))
    playlist = mocker.Mock()
    playlist.id = 0
    playlist.name = "Playlist-0"
    mood = mocker.Mock()
    mood.id = 1
    mood.name = "Mood-1"
    mood.api_path = "something/somethingelse/1"
    mood.get.return_value = [playlist]
    mood_2 = mocker.Mock()
    mood_2.api_path = "0/0/0"
    session.moods.return_value = [mood, mood_2]
    assert tlp.browse("tidal:mood:1") == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0"),
    ]

    session.moods.assert_called_once_with()
    mood.get.assert_called_once_with()


def test_specific_mood_new_api_none(tlp, mocker, tidal_tracks):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("moods",))
    playlist_2 = mocker.Mock()
    playlist_2.api_path = "0/0/0"
    session.moods.return_value = [playlist_2]
    assert not tlp.browse("tidal:mood:1")


def test_specific_genre_new_api(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("genre", "genre.get_genres"))
    playlist = mocker.Mock()
    playlist.id = 0
    playlist.name = "Playlist-0"
    genre = mocker.Mock()
    genre.id = 1
    genre.name = "Genre-1"
    genre.path = "1"
    genre.items.return_value = [playlist]
    genre_2 = mocker.Mock()
    genre_2.path = "13"
    session.genre.get_genres.return_value = [genre, genre_2]
    assert tlp.browse("tidal:genre:1") == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0"),
    ]
    session.genre.get_genres.assert_called_once_with()
    genre.items.assert_called_once_with(Playlist)


def test_specific_genre_new_api_none(tlp, mocker, tidal_tracks):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("genre", "genre.get_genres"))
    playlist_2 = mocker.Mock()
    playlist_2.path = "13"
    session.genre.get_genres.return_value = [playlist_2]
    assert not tlp.browse("tidal:genre:1")
    session.genre.get_genres.assert_called_once_with()


def test_specific_mix(tlp, mocker, tidal_tracks):
    tlp, backend = tlp
    session = backend._session
    playlist = mocker.Mock()
    playlist.id = "1"
    playlist.name = "Playlist-1"
    playlist.items.return_value = tidal_tracks
    playlist_2 = mocker.Mock()
    session.mixes.return_value = [playlist, playlist_2]
    assert tlp.browse("tidal:mix:1") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]
    session.mixes.assert_called_once_with()
    playlist.items.assert_called_once_with()


def test_specific_mix_none(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    playlist_2 = mocker.Mock()
    session.mixes.return_value = [playlist_2]
    assert not tlp.browse("tidal:mix:1")
    session.mixes.assert_called_once_with()


def test_specific_artist_new_api(tlp, mocker, tidal_albums, tidal_artists):
    tlp, backend = tlp
    session = backend._session
    session.mock_add_spec(("artist",))
    artist = tidal_artists[0]
    artist.get_albums.return_value = tidal_albums
    session.artist.return_value = artist
    assert tlp.browse("tidal:artist:1") == [
        Ref(name="Album-0", type="album", uri="tidal:album:0"),
        Ref(name="Album-1", type="album", uri="tidal:album:1"),
        Ref(name="Track-100", type="track", uri="tidal:track:0:7:100"),
    ]
    artist.get_top_tracks.assert_called_once_with()
    artist.get_albums.assert_called_once_with()
    session.artist.assert_has_calls([mocker.call("1"), mocker.call("1")])


def test_lookup_no_uris(tlp, mocker):
    tlp, backend = tlp
    with pytest.raises(Exception):  # just check it raises
        tlp.lookup()
    with pytest.raises(Exception):
        tlp.lookup("")
    with pytest.raises(Exception):
        tlp.lookup("somethingwhichisntauri")
    assert not tlp.lookup("tidal:nonsuch:11")


def test_lookup_http_error(tlp, mocker):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.side_effect = HTTPError
    session.album.return_value = album
    assert not tlp.lookup("tidal:track:0:1:0")


def test_lookup_track(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = tlp.lookup("tidal:track:0:1:0")
    compare(tidal_tracks[:1], res, "track")
    session.album.assert_called_once_with("1")


def test_lookup_track_newstyle(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    track = mocker.Mock(**{"album.id": 1, "name": "track"})
    session.track.return_value = track
    res = tlp.lookup("tidal:track:0")
    compare(tidal_tracks[:1], res, "track")
    session.album.assert_called_once_with("1")
    session.track.assert_called_once_with("0")


def test_lookup_track_cached(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = tlp.lookup("tidal:track:0:1:0")
    compare(tidal_tracks[:1], res, "track")
    res2 = tlp.lookup("tidal:track:0:1:0")
    assert res2 == res
    session.album.assert_called_once_with("1")


def test_lookup_track_cached_album(tlp, mocker, tidal_albums, compare):
    tlp, backend = tlp
    session = backend._session
    tidal_tracks = tidal_albums[1].tracks()
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = tlp.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    res2 = tlp.lookup("tidal:track:1234:1:1")
    compare(tidal_tracks[:1], res2, "track")
    session.album.assert_called_once_with("1")


def test_lookup_album(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = tlp.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    session.album.assert_called_once_with("1")


def test_lookup_album_cached(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = tlp.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    res2 = tlp.lookup("tidal:album:1")
    assert res2 == res
    session.album.assert_called_once_with("1")


def test_lookup_artist(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    artist = mocker.Mock()
    artist.get_top_tracks.return_value = tidal_tracks
    session.artist.return_value = artist
    res = tlp.lookup("tidal:artist:1")
    compare(tidal_tracks, res, "track")
    session.artist.assert_called_once_with("1")


def test_lookup_artist_cached(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    artist = mocker.Mock()
    artist.get_top_tracks.return_value = tidal_tracks
    session.artist.return_value = artist
    res = tlp.lookup("tidal:artist:1")
    compare(tidal_tracks, res, "track")
    res2 = tlp.lookup("tidal:artist:1")
    assert res2 == res
    session.artist.assert_called_once_with("1")


@pytest.mark.gt_3_7
def test_lookup_playlist(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    playlist = mocker.Mock()
    playlist.name = "Playlist-1"
    playlist.last_updated = 10
    session.playlist.return_value = playlist
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "get_playlist_tracks"

    res = tlp.lookup("tidal:playlist:99")
    compare(tidal_tracks, res[: len(tidal_tracks)], "track")

    session.playlist.assert_called_with("99")
    assert len(playlist.tracks.mock_calls) == 5, "Didn't run five fetches in parallel."


@pytest.mark.gt_3_7
def test_lookup_playlist_cached(tlp, mocker, tidal_tracks, compare):
    tlp, backend = tlp
    session = backend._session
    playlist = mocker.Mock()
    playlist.name = "Playlist-1"
    playlist.last_updated = 10
    session.playlist.return_value = playlist
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "get_playlist_tracks"

    res = tlp.lookup("tidal:playlist:99")
    compare(tidal_tracks, res[: len(tidal_tracks)], "track")
    res2 = tlp.lookup("tidal:playlist:99")
    assert res2 == res

    session.playlist.assert_called_with("99")
    assert len(playlist.tracks.mock_calls) == 5, "Didn't run five fetches in parallel."
