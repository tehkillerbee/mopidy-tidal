from json import dump, load
from pathlib import Path

import pytest

from mopidy_tidal.backend import TidalBackend
from mopidy_tidal.context import set_config
from mopidy_tidal.library import TidalLibraryProvider
from mopidy_tidal.playback import TidalPlaybackProvider
from mopidy_tidal.playlists import TidalPlaylistsProvider


@pytest.fixture
def get_backend(mocker):
    def _get_backend(config=mocker.MagicMock(), audio=mocker.Mock()):
        backend = TidalBackend(config, audio)
        session_factory = mocker.Mock()
        session = mocker.Mock()
        session_factory.return_value = session
        mocker.patch("mopidy_tidal.backend.Session", session_factory)
        return backend, config, audio, session_factory, session

    yield _get_backend
    set_config(None)


@pytest.mark.gt_3_7
def test_composition(get_backend):
    backend, *_ = get_backend()
    assert isinstance(backend.playback, TidalPlaybackProvider)
    assert isinstance(backend.library, TidalLibraryProvider)
    assert isinstance(backend.playlists, TidalPlaylistsProvider)


@pytest.mark.gt_3_7
def test_setup(get_backend):
    backend, config, *_ = get_backend()
    assert tuple(backend.uri_schemes) == ("tidal",)  # TODO: why is this muteable?
    assert not backend._session
    assert backend._config is config


@pytest.mark.gt_3_7
def test_login(get_backend, tmp_path, mocker):
    backend, _, _, _, session = get_backend()
    session.check_login.return_value = True
    session.token_type = "token_type"
    session.session_id = "session_id"
    session.access_token = "access_token"
    session.refresh_token = "refresh_token"
    backend._session = session
    authf = tmp_path / "auth.json"
    assert not authf.exists()
    backend.oauth_login_new_session(authf)
    with authf.open() as f:
        data = load(f)
    assert data == {
        "token_type": dict(data="token_type"),
        "session_id": dict(data="session_id"),
        "access_token": dict(data="access_token"),
        "refresh_token": dict(data="refresh_token"),
    }
    session.login_oauth_simple.assert_called_once()


@pytest.mark.gt_3_7
def test_failed_login(get_backend, tmp_path, mocker):
    backend, _, _, _, session = get_backend()
    session.check_login.return_value = False
    backend._session = session
    authf = tmp_path / "auth.json"
    backend.oauth_login_new_session(authf)
    assert not authf.exists()
    session.login_oauth_simple.assert_called_once()


@pytest.mark.gt_3_7
def test_logs_in(get_backend, mocker, config):
    backend, _, _, session_factory, session = get_backend(config=config)
    backend.oauth_login_new_session = mocker.Mock()
    session.check_login.return_value = False
    backend.on_start()
    backend.oauth_login_new_session.assert_called_once()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id == config["tidal"]["client_id"]
    assert config_obj.client_secret == config["tidal"]["client_secret"]


@pytest.mark.gt_3_7
def test_logs_in_only_client_secret(get_backend, mocker, config):
    config["tidal"]["client_id"] = ""
    backend, _, _, session_factory, session = get_backend(config=config)
    backend.oauth_login_new_session = mocker.Mock()
    session.check_login.return_value = False
    backend.on_start()
    backend.oauth_login_new_session.assert_called_once()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id and config_obj.client_id != config["tidal"]["client_id"]
    assert (
        config_obj.client_secret
        and config_obj.client_secret != config["tidal"]["client_secret"]
    )


@pytest.mark.gt_3_7
def test_logs_in_default(get_backend, mocker, config):
    config["tidal"]["client_id"] = ""
    config["tidal"]["client_secret"] = ""
    backend, _, _, session_factory, session = get_backend(config=config)
    backend.oauth_login_new_session = mocker.Mock()
    session.check_login.return_value = False
    backend.on_start()
    backend.oauth_login_new_session.assert_called_once()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id and config_obj.client_id != config["tidal"]["client_id"]
    assert (
        config_obj.client_secret
        and config_obj.client_secret != config["tidal"]["client_secret"]
    )


def test_loads_session(get_backend, mocker, config):
    backend, config, _, session_factory, session = get_backend(config=config)
    backend.oauth_login_new_session = mocker.Mock()

    authf = Path(config["core"]["data_dir"], "tidal") / "tidal-oauth.json"
    data = {
        "token_type": dict(data="token_type"),
        "session_id": dict(data="session_id"),
        "access_token": dict(data="access_token"),
        "refresh_token": dict(data="refresh_token"),
    }
    with authf.open("w") as f:
        dump(data, f)
    session.check_login.return_value = True
    backend.on_start()
    args = {k: v["data"] for k, v in data.items() if k != "session_id"}
    backend.oauth_login_new_session.assert_not_called()
    session.load_oauth_session.assert_called_once_with(**args)
    session_factory.assert_called_once()
