from __future__ import unicode_literals

import json
import logging
from pathlib import Path

from mopidy import backend
from pykka import ThreadingActor
from tidalapi import Config, Quality, Session

from mopidy_tidal import Extension, context, library, playback, playlists

logger = logging.getLogger(__name__)


def _connecting_log(msg: str, level="info"):
    getattr(logger, level)("Connecting to TIDAL... " + msg)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super().__init__()
        self._active_session = None
        self._logged_in = False
        self._config = config
        context.set_config(self._config)
        self.playback = playback.TidalPlaybackProvider(audio=audio, backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        self.uri_schemes = ["tidal"]

    @property
    def session(self):
        if not self._logged_in:
            self._login()
        return self._active_session

    def _oauth_login_new_session(self, oauth_file: Path):
        # create a new session
        self._active_session.login_oauth_simple(function=logger.info)
        if self._active_session.check_login():
            # store current OAuth session
            data = {}
            data["token_type"] = {"data": self._active_session.token_type}
            data["session_id"] = {"data": self._active_session.session_id}
            data["access_token"] = {"data": self._active_session.access_token}
            data["refresh_token"] = {"data": self._active_session.refresh_token}
            with oauth_file.open("w") as outfile:
                json.dump(data, outfile)

    def on_start(self):
        quality = self._config["tidal"]["quality"]
        _connecting_log("Quality = %s" % quality)
        config = Config(quality=Quality(quality))
        client_id = self._config["tidal"]["client_id"]
        client_secret = self._config["tidal"]["client_secret"]

        if (client_id and not client_secret) or (client_secret and not client_id):
            _connecting_log(
                "always provide client_id and client_secret together", "warning"
            )
            _connecting_log("using default client id & client secret from python-tidal")

        if client_id and client_secret:
            _connecting_log("client id & client secret from config section are used")
            config.client_id = client_id
            config.api_token = client_id
            config.client_secret = client_secret

        if not client_id and not client_secret:
            _connecting_log("using default client id & client secret from python-tidal")

        self._active_session = Session(config)
        if not self._config["tidal"]["lazy"]:
            self._login()

    def _login(self):
        # Always store tidal-oauth cache in mopidy core config data_dir
        data_dir = Path(Extension.get_data_dir(self._config))
        oauth_file = data_dir / "tidal-oauth.json"
        try:
            # attempt to reload existing session from file
            with open(oauth_file) as f:
                logger.info("Loading OAuth session from %s...", oauth_file)
                data = json.load(f)
                self._load_oauth_session(**data)
        except Exception as e:
            logger.info("Could not load OAuth session from %s: %s", oauth_file, e)

        if not self._active_session.check_login():
            logger.info("Creating new OAuth session...")
            self._oauth_login_new_session(oauth_file)

        if self._active_session.check_login():
            logger.info("TIDAL Login OK")
            self._logged_in = True
        else:
            logger.info("TIDAL Login KO")
            raise ConnectionError("Failed to log in.")

    def _load_oauth_session(self, **data):
        assert self._active_session, "No session loaded"
        args = {
            "token_type": data.get("token_type", {}).get("data"),
            "access_token": data.get("access_token", {}).get("data"),
            "refresh_token": data.get("refresh_token", {}).get("data"),
        }

        self._active_session.load_oauth_session(**args)
