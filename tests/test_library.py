import pytest

from mopidy_tidal.library import HTTPError, Image, ImagesGetter


@pytest.fixture
def images_getter(mocker, config):
    session = mocker.Mock()
    getter = ImagesGetter(session)
    return getter, session


@pytest.mark.parametrize("dimensions", (750, 640, 480))
def test_get_album_image_new_api(images_getter, mocker, dimensions):
    ig, session = images_getter
    uri = "tidal:album:1-1-1"
    get_album = mocker.Mock()

    get_uri_args = None

    def get_uri(dim, *args):
        nonlocal get_uri_args
        get_uri_args = [dim] + list(args)
        if dim != dimensions:
            raise ValueError()
        return uri

    get_album.image = get_uri
    session.get_album.return_value = get_album
    assert ig(uri) == (
        uri,
        [
            Image(height=320, uri=uri, width=320)
        ],  # Why can we just set the dimensions like that?
    )
    assert get_uri_args == [dimensions]


def test_get_album_no_image_new_api(images_getter, mocker):
    ig, session = images_getter
    uri = "tidal:album:1-1-1"
    get_album = mocker.Mock()

    def get_uri(*_):
        raise ValueError()

    get_album.image = get_uri
    session.get_album.return_value = get_album
    assert ig(uri) == (uri, [])


def test_get_album_no_getter_methods_new_api(images_getter, mocker):
    ig, session = images_getter
    uri = "tidal:album:1-1-1"
    get_album = mocker.Mock(spec={"id", "__name__"}, name="get_album", id="1")
    session.get_album.return_value = get_album
    assert ig(uri) == (uri, [])


@pytest.mark.parametrize("dimensions", (750, 640, 480))
def test_get_album_image_old_api(images_getter, mocker, dimensions):
    ig, session = images_getter
    uri = "tidal:album:1-1-1"
    get_album = mocker.Mock(spec={"picture"})

    get_uri_args = None

    def get_uri(dim, *args):
        nonlocal get_uri_args
        get_uri_args = [dim] + list(args)
        if dim != dimensions:
            raise ValueError()
        return uri

    get_album.picture = get_uri
    session.get_album.return_value = get_album
    assert ig(uri) == (
        uri,
        [
            Image(height=320, uri=uri, width=320)
        ],  # Why can we just set the dimensions like that?
    )
    assert get_uri_args == [dimensions, dimensions]


def test_get_track_image(images_getter, mocker):
    ig, session = images_getter
    uri = "tidal:track:0-0-0:1-1-1:2-2-2"
    get_album = mocker.Mock()
    get_album.image.return_value = "tidal:album:1-1-1"
    session.get_album.return_value = get_album
    assert ig(uri) == (
        uri,
        [
            Image(height=320, uri="tidal:album:1-1-1", width=320)
        ],  # Why can we just set the dimensions like that?
    )
    session.get_album.assert_called_once_with("1-1-1")


def test_get_artist_image(images_getter, mocker):
    ig, session = images_getter
    uri = "tidal:artist:2-2-2"
    get_artist = mocker.Mock()
    get_artist.image.return_value = uri
    session.get_artist.return_value = get_artist
    assert ig(uri) == (
        uri,
        [
            Image(height=320, uri=uri, width=320)
        ],  # Why can we just set the dimensions like that?
    )


def test_get_artist_no_image(images_getter, mocker):
    ig, session = images_getter
    uri = "tidal:artist:2-2-2"
    get_artist = mocker.Mock()
    get_artist.picture = None
    session.get_artist.return_value = get_artist
    assert ig(uri) == (uri, [])


@pytest.mark.parametrize("error", {HTTPError, AttributeError})
def test_get_artist_error(images_getter, mocker, error):
    ig, session = images_getter
    uri = "tidal:artist:2-2-2"
    get_artist = mocker.Mock()

    def raiser(*_):
        raise error()

    get_artist.image = raiser
    session.get_artist.return_value = get_artist
    assert ig(uri) == (uri, [])
