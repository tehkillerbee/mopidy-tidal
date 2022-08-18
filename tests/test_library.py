import pytest

from mopidy_tidal.library import Image, ImagesGetter


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
