import pytest
from tidalapi.album import Album
from tidalapi.artist import Artist
from tidalapi.media import Track


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


def compare(tidal, mopidy, fn):
    assert len(tidal) == len(mopidy)
    for t, m in zip(tidal, mopidy):
        fn(t, m)


test_queries = [
    (  # Any
        dict(
            any=["nonsuch"],
        ),
        dict(tracks=0, artists=0, albums=0),
        "nonsuch",
        (Artist, Album, Track),
    ),
    (  # Album
        dict(
            album=["Album-1"],
        ),
        dict(tracks=0, artists=0, albums=None),
        "Album-1",
        (Album,),
    ),
    (  # Artist
        dict(
            artist=["Artist-1"],
        ),
        dict(tracks=0, artists=None, albums=0),
        "Artist-1",
        (Artist,),
    ),
    (  # No results
        dict(
            artist=["Artist-1"],
            album=["Album-1"],
            track_name=["Track-1"],
            any=["any1"],
        ),
        dict(tracks=0, artists=0, albums=0),
        "any1 Artist-1 Album-1 Track-1",
        (Track,),
    ),
    (  # Tracks
        dict(
            artist="Artist-1",
            album=["Album-1"],
            track_name=["Track-1"],
            any=["any1"],
        ),
        dict(tracks=None, artists=0, albums=0),
        "any1 Artist-1 Album-1 Track-1",
        (Track,),
    ),
]


@pytest.mark.parametrize("query, results, query_str, models", test_queries)
def test_search_inexact(
    mocker,
    tidal_search,
    query,
    results,
    query_str,
    models,
    tidal_tracks,
    tidal_artists,
    tidal_albums,
):
    # generate the right query.  We use list slicing since we the fixture isn't
    # available in the parametrizing code.
    _l = locals()
    results = {k: _l[f"tidal_{k}"][:v] for k, v in results.items()}
    session = mocker.Mock()
    session.search.return_value = results
    artists, albums, tracks = tidal_search(session, query=query, exact=False)
    # NOTE: There is no need to copy the extra artist/album tracks into
    # results["tracks"]: the call to tidal_search() will actually do that for
    # us.
    compare(results["tracks"], tracks, compare_track)
    compare(results["artists"], artists, compare_artist)
    compare(results["albums"], albums, compare_album)
    session.search.assert_called_once_with(query_str, models=models)


@pytest.mark.parametrize("query, results, query_str, models", test_queries)
def test_search_exact(
    mocker,
    tidal_search,
    query,
    results,
    query_str,
    models,
    tidal_tracks,
    tidal_artists,
    tidal_albums,
):
    # generate the right query.  We use list slicing since we the fixture isn't
    # available in the parametrizing code.
    _l = locals()
    results = {k: _l[f"tidal_{k}"][:v] for k, v in results.items()}
    session = mocker.Mock()
    session.search.return_value = results
    artists, albums, tracks = tidal_search(session, query=query, exact=True)

    if "track_name" in query:
        results["tracks"] = [
            t for t in results["tracks"] if t.name == query["track_name"][0]
        ]
    if "album" in query:
        results["albums"] = [
            a for a in results["albums"] if a.name == query["album"][0]
        ]
        for album in results["albums"]:
            results["tracks"] += album.tracks()
    if "artist" in query:
        results["artists"] = [
            a for a in results["artists"] if a.name == query["artist"][0]
        ]
        for artist in results["artists"]:
            results["tracks"] += artist.get_top_tracks()
    compare(results["tracks"], tracks, compare_track)
    compare(results["artists"], artists, compare_artist)
    compare(results["albums"], albums, compare_album)
    session.search.assert_called_once_with(query_str, models=models)


def test_malformed_api_response(mocker, tidal_search, tidal_tracks):
    session = mocker.Mock()
    session.search.return_value = {
        # missing albums and artists
        "tracks": tidal_tracks,
        # new category
        "nonsuch": tidal_tracks,
    }
    query = dict(
        artist=["Artist-1"],
        album=["Album-1"],
        track_name=["Track-1"],
        any=["any1"],
    )
    artists, albums, tracks = tidal_search(session, query=query, exact=False)
    assert not artists
    assert not albums
    compare(tidal_tracks, tracks, compare_track)
