import pytest
from mopidy.models import Album, Artist, Image, Ref, SearchResult, Track
from tidalapi.playlist import Playlist

from mopidy_tidal.library import HTTPError, TidalLibraryProvider


@pytest.fixture
def backend(mocker):
    return mocker.Mock()


@pytest.fixture
def library_provider(backend, config):
    lp = TidalLibraryProvider(backend)
    for cache_type in {"artist", "album", "track", "playlist"}:
        getattr(lp, f"_{cache_type}_cache")._persist = False

    return lp


def test_search_no_match(library_provider, backend, tidal_search):
    assert not library_provider.search("nonsuch")


def test_search(mocker, library_provider, backend):
    query, exact = object(), object()
    artists = [mocker.Mock(spec=Artist)]
    albums = [mocker.Mock(spec=Album)]
    tracks = [mocker.Mock(spec=Track)]
    tidal_search = mocker.Mock()
    tidal_search.return_value = (artists, albums, tracks)
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert library_provider.search(query=query, exact=exact) == SearchResult(
        artists=artists, albums=albums, tracks=tracks
    )
    tidal_search.assert_called_once_with(backend.session, query=query, exact=exact)


def test_get_track_images(library_provider, backend, mocker):
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    backend.session.album.return_value = get_album
    assert library_provider.get_images(uris) == {
        uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]
    }
    backend.session.album.assert_called_once_with("1-1-1")


@pytest.mark.xfail
def test_track_cache(library_provider, backend, mocker):
    # I think the caching logic is broken here
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    backend.session.album.return_value = get_album
    first = library_provider.get_images(uris)
    assert first == {uris[0]: [Image(height=320, uri="tidal:album:1-1-1", width=320)]}
    assert library_provider.get_images(uris) == first
    backend.session.album.assert_called_once_with("1-1-1")


@pytest.mark.xfail(reason="returning nothing")
def test_get_noimages(library_provider, backend, mocker):
    uris = ["tidal:track:0-0-0:1-1-1:2-2-2"]
    backend.session.mock_add_spec([])
    assert library_provider.get_images(uris) == {uris[0]: []}


@pytest.mark.parametrize("field", ("artist", "album", "track"))
def test_get_distinct_root(library_provider, backend, mocker, field):
    session = backend.session
    thing = mocker.Mock()
    thing.name = "Thing"
    session.configure_mock(**{f"user.favorites.{field}s.return_value": [thing]})
    res = library_provider.get_distinct(field)
    assert res[0] == "Thing [TIDAL]"
    assert len(res) == 1


def test_get_distinct_root_nonsuch(library_provider, mocker):
    assert not library_provider.get_distinct("nonsuch")


def test_get_distinct_query_nonsuch(library_provider, mocker):
    assert not library_provider.get_distinct("nonsuch", query={"any": "any"})


@pytest.mark.parametrize("field", ("artist", "track"))
def test_get_distinct_ignore_query(library_provider, backend, mocker, field):
    session = backend.session
    thing = mocker.Mock()
    thing.name = "Thing"
    session.configure_mock(**{f"user.favorites.{field}s.return_value": [thing]})
    res = library_provider.get_distinct(field, query={"any": "any"})
    assert res[0] == "Thing [TIDAL]"
    assert len(res) == 1


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_no_results(library_provider, backend, mocker, field):
    session = backend.session
    tidal_search = mocker.Mock()
    tidal_search.return_value = ([], [], [])
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert not library_provider.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_new_api(library_provider, backend, mocker, field):
    session = backend.session
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
    res = library_provider.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)
    session.artist.assert_called_once_with("1")
    artist.get_albums.assert_called_once_with()
    assert len(res) == 1
    assert res[0] == "Thing [TIDAL]"


@pytest.mark.parametrize("field", ("album", "albumartist"))
def test_get_distinct_album_new_api_no_artist(library_provider, backend, mocker, field):
    session = backend.session
    session.mock_add_spec(("tidal_search", "artist", "artist.get_albums"))

    artist = mocker.Mock()
    artist.uri = "tidal:artist:1"

    tidal_search = mocker.Mock()
    tidal_search.return_value = ([artist], [], [])
    session.artist.return_value = None
    mocker.patch("mopidy_tidal.search.tidal_search", tidal_search)
    assert not library_provider.get_distinct(field, query={"any": "any"})
    tidal_search.assert_called_once_with(session, query={"any": "any"}, exact=True)
    session.artist.assert_called_once_with("1")


def test_browse_wrong_uri(library_provider):
    assert not library_provider.browse("")
    assert not library_provider.browse("spotify:something:something_else")
    assert not library_provider.browse("tidal:album:oneid:oneidtoomany")


def test_browse_root(library_provider):
    assert library_provider.browse("tidal:directory") == [
        Ref(name="For You", type="directory", uri="tidal:for_you"),
        Ref(name="Explore", type="directory", uri="tidal:explore"),
        Ref(name="Genres", type="directory", uri="tidal:genres"),
        Ref(name="Moods", type="directory", uri="tidal:moods"),
        Ref(name="Mixes", type="directory", uri="tidal:mixes"),
        Ref(name="My Artists", type="directory", uri="tidal:my_artists"),
        Ref(name="My Albums", type="directory", uri="tidal:my_albums"),
        Ref(name="My Playlists", type="directory", uri="tidal:my_playlists"),
        Ref(name="My Tracks", type="directory", uri="tidal:my_tracks"),
    ]


def test_browse_artists(library_provider, backend, mocker, tidal_artists):
    session = backend.session
    session.user.favorites.artists = tidal_artists
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert library_provider.browse("tidal:my_artists") == [
        Ref(name="Artist-0", type="artist", uri="tidal:artist:0"),
        Ref(name="Artist-1", type="artist", uri="tidal:artist:1"),
    ]


def test_browse_albums(library_provider, backend, mocker, tidal_albums):
    session = backend.session
    session.user.favorites.albums = tidal_albums
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert library_provider.browse("tidal:my_albums") == [
        Ref(name="Album-0", type="album", uri="tidal:album:0"),
        Ref(name="Album-1", type="album", uri="tidal:album:1"),
    ]


def test_browse_tracks(library_provider, backend, mocker, tidal_tracks):
    session = backend.session
    session.user.favorites.tracks = tidal_tracks
    mocker.patch("mopidy_tidal.library.get_items", lambda x: x)
    assert library_provider.browse("tidal:my_tracks") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]


def test_browse_playlists(library_provider, backend, mocker):
    as_list = mocker.Mock()
    uniq = object()
    as_list.return_value = uniq
    backend.playlists.as_list = as_list
    assert library_provider.browse("tidal:my_playlists") is uniq
    as_list.assert_called_once_with()


def test_moods_new_api(library_provider, backend, mocker):
    session = backend.session
    session.mock_add_spec(("moods",))
    mood = mocker.Mock(spec=("title", "title", "api_path"))
    mood.title = "Mood-1"
    mood.api_path = "0/0/1"
    session.moods.return_value = [mood]
    assert library_provider.browse("tidal:moods") == [
        Ref(name="Mood-1", type="directory", uri="tidal:mood:1")
    ]
    session.moods.assert_called_once_with()


def test_mixes_new_api(library_provider, backend, mocker):
    session = backend.session
    session.mock_add_spec(("mixes",))
    mix = mocker.Mock()
    mix.title = "Mix-1"
    mix.sub_title = "[Subtitle]"
    mix.id = "1"
    session.mixes.return_value = [mix]
    assert library_provider.browse("tidal:mixes") == [
        Ref(name="Mix-1 ([Subtitle])", type="playlist", uri="tidal:mix:1")
    ]
    session.mixes.assert_called_once_with()


def test_genres_new_api(library_provider, backend, mocker):
    session = backend.session
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
    assert library_provider.browse("tidal:genres") == [
        Ref(name="Genre-1", type="directory", uri="tidal:genre:1")
    ]
    session.genre.get_genres.assert_called_once_with()


def test_specific_album_new_api(library_provider, backend, mocker, tidal_albums):
    session = backend.session
    session.mock_add_spec(("album",))
    album = tidal_albums[0]
    session.album.return_value = album
    assert library_provider.browse("tidal:album:1") == [
        Ref(name="Track-0", type="track", uri="tidal:track:1234:0:0")
    ]
    session.album.assert_called_once_with("1")
    album.tracks.assert_called_once_with()


def test_specific_album_new_api_none(library_provider, backend, mocker):
    session = backend.session
    session.mock_add_spec(("album",))
    session.album.return_value = None
    assert not library_provider.browse("tidal:album:1")
    session.album.assert_called_once_with("1")


def test_specific_playlist_new_api(library_provider, backend, mocker, tidal_tracks):
    session = backend.session
    session.mock_add_spec(("playlist",))
    playlist = mocker.Mock(name="Playlist")
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "playlist"
    session.playlist.return_value = playlist

    tracks = library_provider.browse("tidal:playlist:1")
    assert tracks[:2] == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]

    session.playlist.assert_called_once_with("1")
    playlist.tracks.assert_has_calls([mocker.call(100, 0)])


def test_specific_mood_new_api(library_provider, backend, mocker):
    session = backend.session
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
    assert library_provider.browse("tidal:mood:1") == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0"),
    ]

    session.moods.assert_called_once_with()
    mood.get.assert_called_once_with()


def test_specific_mood_new_api_none(library_provider, backend, mocker, tidal_tracks):
    session = backend.session
    session.mock_add_spec(("moods",))
    playlist_2 = mocker.Mock()
    playlist_2.api_path = "0/0/0"
    session.moods.return_value = [playlist_2]
    assert not library_provider.browse("tidal:mood:1")


def test_specific_genre_new_api(library_provider, backend, mocker):
    session = backend.session
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
    assert library_provider.browse("tidal:genre:1") == [
        Ref(name="Playlist-0", type="playlist", uri="tidal:playlist:0"),
    ]
    session.genre.get_genres.assert_called_once_with()
    genre.items.assert_called_once_with(Playlist)


def test_specific_genre_new_api_none(library_provider, backend, mocker, tidal_tracks):
    session = backend.session
    session.mock_add_spec(("genre", "genre.get_genres"))
    playlist_2 = mocker.Mock()
    playlist_2.path = "13"
    session.genre.get_genres.return_value = [playlist_2]
    assert not library_provider.browse("tidal:genre:1")
    session.genre.get_genres.assert_called_once_with()


def test_specific_mix(library_provider, backend, mocker, tidal_tracks):
    session = backend.session
    playlist = mocker.Mock()
    playlist.id = "1"
    playlist.name = "Playlist-1"
    playlist.items.return_value = tidal_tracks
    playlist_2 = mocker.Mock()
    session.mixes.return_value = [playlist, playlist_2]
    assert library_provider.browse("tidal:mix:1") == [
        Ref(name="Track-0", type="track", uri="tidal:track:0:0:0"),
        Ref(name="Track-1", type="track", uri="tidal:track:1:1:1"),
    ]
    session.mixes.assert_called_once_with()
    playlist.items.assert_called_once_with()


def test_specific_mix_none(library_provider, backend, mocker):
    session = backend.session
    playlist_2 = mocker.Mock()
    session.mixes.return_value = [playlist_2]
    assert not library_provider.browse("tidal:mix:1")
    session.mixes.assert_called_once_with()


def test_specific_artist_new_api(
    library_provider, backend, mocker, tidal_albums, tidal_artists
):
    session = backend.session
    session.mock_add_spec(("artist",))
    artist = tidal_artists[0]
    artist.get_albums.return_value = tidal_albums
    session.artist.return_value = artist
    assert library_provider.browse("tidal:artist:1") == [
        Ref(name="Album-0", type="album", uri="tidal:album:0"),
        Ref(name="Album-1", type="album", uri="tidal:album:1"),
        Ref(name="Track-100", type="track", uri="tidal:track:0:7:100"),
    ]
    artist.get_top_tracks.assert_called_once_with()
    artist.get_albums.assert_called_once_with()
    session.artist.assert_has_calls([mocker.call("1"), mocker.call("1")])


def test_lookup_no_uris(library_provider, mocker):
    with pytest.raises(Exception):  # just check it raises
        library_provider.lookup()
    with pytest.raises(Exception):
        library_provider.lookup("")
    with pytest.raises(Exception):
        library_provider.lookup("somethingwhichisntauri")
    assert not library_provider.lookup("tidal:nonsuch:11")


def test_lookup_http_error(library_provider, backend, mocker):
    session = backend.session
    album = mocker.Mock()
    album.tracks.side_effect = HTTPError
    session.album.return_value = album
    assert not library_provider.lookup("tidal:track:0:1:0")


def test_lookup_track(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = library_provider.lookup("tidal:track:0:1:0")
    compare(tidal_tracks[:1], res, "track")
    session.album.assert_called_once_with("1")


def test_lookup_track_newstyle(
    library_provider, backend, mocker, tidal_tracks, compare
):
    session = backend.session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    track = mocker.Mock(**{"album.id": 1, "name": "track"})
    session.track.return_value = track
    res = library_provider.lookup("tidal:track:0")
    compare(tidal_tracks[:1], res, "track")
    session.album.assert_called_once_with("1")
    session.track.assert_called_once_with("0")


def test_lookup_track_cached(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = library_provider.lookup("tidal:track:0:1:0")
    compare(tidal_tracks[:1], res, "track")
    res2 = library_provider.lookup("tidal:track:0:1:0")
    assert res2 == res
    session.album.assert_called_once_with("1")


def test_lookup_track_cached_album(
    library_provider, backend, mocker, tidal_albums, compare
):
    session = backend.session
    tidal_tracks = tidal_albums[1].tracks()
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = library_provider.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    res2 = library_provider.lookup("tidal:track:1234:1:1")
    compare(tidal_tracks[:1], res2, "track")
    session.album.assert_called_once_with("1")


def test_lookup_album(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = library_provider.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    session.album.assert_called_once_with("1")


def test_lookup_album_cached(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    album = mocker.Mock()
    album.tracks.return_value = tidal_tracks
    session.album.return_value = album
    res = library_provider.lookup("tidal:album:1")
    compare(tidal_tracks, res, "track")
    res2 = library_provider.lookup("tidal:album:1")
    assert res2 == res
    session.album.assert_called_once_with("1")


def test_lookup_artist(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    artist = mocker.Mock()
    artist.get_top_tracks.return_value = tidal_tracks
    session.artist.return_value = artist
    res = library_provider.lookup("tidal:artist:1")
    compare(tidal_tracks, res, "track")
    session.artist.assert_called_once_with("1")


def test_lookup_artist_cached(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    artist = mocker.Mock()
    artist.get_top_tracks.return_value = tidal_tracks
    session.artist.return_value = artist
    res = library_provider.lookup("tidal:artist:1")
    compare(tidal_tracks, res, "track")
    res2 = library_provider.lookup("tidal:artist:1")
    assert res2 == res
    session.artist.assert_called_once_with("1")


def test_lookup_playlist(library_provider, backend, mocker, tidal_tracks, compare):
    session = backend.session
    playlist = mocker.Mock()
    playlist.name = "Playlist-1"
    playlist.last_updated = 10
    session.playlist.return_value = playlist
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "get_playlist_tracks"

    res = library_provider.lookup("tidal:playlist:99")
    compare(tidal_tracks, res[: len(tidal_tracks)], "track")

    session.playlist.assert_called_with("99")
    assert len(playlist.tracks.mock_calls) == 5, "Didn't run five fetches in parallel."


def test_lookup_playlist_cached(
    library_provider, backend, mocker, tidal_tracks, compare
):
    session = backend.session
    playlist = mocker.Mock()
    playlist.name = "Playlist-1"
    playlist.last_updated = 10
    session.playlist.return_value = playlist
    playlist.tracks.return_value = tidal_tracks
    playlist.tracks.__name__ = "get_playlist_tracks"

    res = library_provider.lookup("tidal:playlist:99")
    compare(tidal_tracks, res[: len(tidal_tracks)], "track")
    res2 = library_provider.lookup("tidal:playlist:99")
    assert res2 == res

    session.playlist.assert_called_with("99")
    assert len(playlist.tracks.mock_calls) == 5, "Didn't run five fetches in parallel."
