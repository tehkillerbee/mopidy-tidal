from json import dump, dumps, load, loads
from pathlib import Path

import pytest

from mopidy_tidal.library import TidalLibraryProvider
from mopidy_tidal.playback import TidalPlaybackProvider
from mopidy_tidal.playlists import TidalPlaylistsProvider


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
    assert not backend._active_session
    assert backend._config is config


@pytest.mark.gt_3_7
def test_initial_login_caches_credentials(get_backend, config):
    backend, _, _, _, session = get_backend(config=config)
    session.check_login.return_value = False

    def login(*_, **__):
        session.check_login.return_value = True

    session.login_oauth_simple.side_effect = login
    backend._active_session = session
    authf = Path(config["core"]["data_dir"], "tidal/tidal-oauth.json")
    assert not authf.exists()
    backend._login()
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
def test_login_after_failed_cached_credentials_overwrites_cached_credentials(
    get_backend, config
):
    backend, _, _, _, session = get_backend(config=config)
    session.check_login.return_value = False

    def login(*_, **__):
        session.check_login.return_value = True

    session.login_oauth_simple.side_effect = login
    backend._active_session = session
    authf = Path(config["core"]["data_dir"], "tidal/tidal-oauth.json")
    cached_data = {
        "token_type": dict(data="token_type2"),
        "session_id": dict(data="session_id2"),
        "access_token": dict(data="access_token2"),
        "refresh_token": dict(data="refresh_token2"),
    }
    authf.write_text(dumps(cached_data))

    backend._login()
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
def test_failed_login_does_not_overwrite_cached_credentials(
    get_backend, mocker, config, tmp_path
):
    backend, _, _, _, session = get_backend(config=config)
    session.check_login.return_value = False

    backend._active_session = session
    authf = Path(config["core"]["data_dir"], "tidal/tidal-oauth.json")
    cached_data = {
        "token_type": dict(data="token_type2"),
        "session_id": dict(data="session_id2"),
        "access_token": dict(data="access_token2"),
        "refresh_token": dict(data="refresh_token2"),
    }
    authf.write_text(dumps(cached_data))

    with pytest.raises(ConnectionError):
        backend._login()

    data = loads(authf.read_text())
    assert data == cached_data
    session.login_oauth_simple.assert_called_once()


@pytest.mark.gt_3_7
def test_failed_overall_login_throws_error(get_backend, tmp_path, mocker, config):
    backend, _, _, _, session = get_backend(config=config)
    session.check_login.return_value = False
    backend._active_session = session
    authf = tmp_path / "auth.json"
    with pytest.raises(ConnectionError):
        backend.on_start()
    assert not authf.exists()


@pytest.mark.gt_3_7
def test_logs_in(get_backend, mocker, config):
    backend, _, _, session_factory, session = get_backend(config=config)
    backend._active_session = session

    def set_logged_in(*_, **__):
        session.check_login.return_value = True

    session.login_oauth_simple.side_effect = set_logged_in
    session.check_login.return_value = False
    backend.on_start()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id == config["tidal"]["client_id"]
    assert config_obj.client_secret == config["tidal"]["client_secret"]


@pytest.mark.gt_3_7
def test_accessing_session_triggers_lazy_login(get_backend, mocker, config):
    config["tidal"]["lazy"] = True
    backend, _, _, session_factory, session = get_backend(config=config)

    def set_logged_in(*_, **__):
        session.check_login.return_value = True

    session.check_login.return_value = False
    session.login_oauth_simple.side_effect = set_logged_in
    backend.on_start()
    session.login_oauth_simple.assert_not_called()
    assert not backend._active_session.check_login()
    assert backend.session
    assert backend.session.check_login()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id == config["tidal"]["client_id"]
    assert config_obj.client_secret == config["tidal"]["client_secret"]


@pytest.mark.gt_3_7
def test_logs_in_only_client_secret(get_backend, mocker, config):
    config["tidal"]["client_id"] = ""
    backend, _, _, session_factory, session = get_backend(config=config)

    def set_logged_in(*_, **__):
        session.check_login.return_value = True

    session.login_oauth_simple.side_effect = set_logged_in
    session.check_login.return_value = False
    backend.on_start()
    session.login_oauth_simple.assert_called_once()
    session_factory.assert_called_once()
    config_obj = session_factory.mock_calls[0].args[0]
    assert config_obj.quality == config["tidal"]["quality"]
    assert config_obj.client_id and config_obj.client_id != config["tidal"]["client_id"]
    assert (
        config_obj.client_secret
        and config_obj.client_secret != config["tidal"]["client_secret"]
    )


@pytest.mark.gt_3_7
def test_logs_in_default_id_secret(get_backend, mocker, config):
    config["tidal"]["client_id"] = ""
    config["tidal"]["client_secret"] = ""
    backend, _, _, session_factory, session = get_backend(config=config)

    def set_logged_in(*_, **__):
        session.check_login.return_value = True

    session.login_oauth_simple.side_effect = set_logged_in
    session.check_login.return_value = False
    backend.on_start()
    session.login_oauth_simple.assert_called_once()
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
    session.login_oauth_simple.assert_not_called()
    session.load_oauth_session.assert_called_once_with(**args)
    session_factory.assert_called_once()
