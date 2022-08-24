from mopidy_tidal.full_models_mappers import create_mopidy_album, create_mopidy_artist


def test_create_mopidy_artist_none():
    assert not create_mopidy_artist(None)


def test_create_mopidy_album_no_release_date(mocker, tidal_albums, compare):
    album = tidal_albums[0]
    del album.release_date
    del album.tidal_release_date
    resp = create_mopidy_album(album, None)
    compare([album], [resp], "album")
