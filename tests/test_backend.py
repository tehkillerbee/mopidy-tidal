import pytest

from mopidy_tidal.backend import TidalBackend
from mopidy_tidal.context import set_config
from mopidy_tidal.library import TidalLibraryProvider
from mopidy_tidal.playback import TidalPlaybackProvider
from mopidy_tidal.playlists import TidalPlaylistsProvider


@pytest.fixture
def backend(mocker):
    def get_backend(config=mocker.MagicMock(), audio=mocker.Mock()):
        backend = TidalBackend(config, audio)
        return backend, config, audio

    yield get_backend
    set_config(None)


def test_composition(backend):
    backend, config, audio = backend()
    assert isinstance(backend.playback, TidalPlaybackProvider)
    assert isinstance(backend.library, TidalLibraryProvider)
    assert isinstance(backend.playlists, TidalPlaylistsProvider)


def test_setup(backend):
    backend, config, audio = backend()
    assert tuple(backend.uri_schemes) == ("tidal",)  # TODO: why is this muteable?
    assert not backend._session
    assert backend._config is config
