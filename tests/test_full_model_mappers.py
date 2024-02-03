from mopidy_tidal.full_models_mappers import create_mopidy_album, create_mopidy_artist


class TestCreateMopidyArtist:
    def test_returns_none_if_tidal_artist_none(self):
        assert create_mopidy_artist(tidal_artist=None) is None


def test_create_mopidy_album_no_release_date(mocker, tidal_albums, compare):
    album = tidal_albums[0]
    del album.release_date
    del album.tidal_release_date
    resp = create_mopidy_album(album, None)
    compare([album], [resp], "album")
