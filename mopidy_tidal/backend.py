from __future__ import unicode_literals

import logging
from concurrent.futures import Future
from pathlib import Path
from typing import Optional

from mopidy import backend
from pykka import ThreadingActor
from tidalapi import Config, Quality, Session

from mopidy_tidal import Extension, context, library, playback, playlists

logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super().__init__()
        # Mopidy cfg
        self._config = config
        context.set_config(self._config)
        self._tidal_config = config[Extension.ext_name]

        # Backend
        self.playback = playback.TidalPlaybackProvider(audio=audio, backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)

        # Session parameters
        self._active_session: Optional[Session] = None
        self._logged_in: bool = False
        self.uri_schemes: [str] = ["tidal"]
        self._login_future: Optional[Future] = None
        self._login_url: Optional[str] = None
        self.data_dir: Path = Path(Extension.get_data_dir(self._config))
        self.session_file_path: Path = Path("")

        # Config parameters
        # Lazy: Connect lazily, i.e. login only when user starts browsing TIDAL directories
        self.lazy_connect: bool = False
        # Login Method:
        #   BLOCK:  Immediately prompt user for login (This will block mopidy startup!)
        #   HACK:   Display URI with login URL. When clicked QR code and TTS is generated
        self.login_method: str = "BLOCK"
        # pkce_enabled: If true, TIDAL session will use PKCE auth. Otherwise OAuth2
        self.pkce_enabled: bool = False

    @property
    def session(self):
        if not self.logged_in:
            self._login()
        return self._active_session

    @property
    def logged_in(self):
        if not self._logged_in:
            if self._active_session.load_session_from_file(self.session_file_path):
                logger.info("Loaded tidal session from file %s", self.session_file_path)
                self._logged_in = True
        return self._logged_in

    @property
    def session_valid(self):
        # Returns true when session is logged in and valid
        return self._active_session.check_login()

    def on_start(self):
        quality = self._tidal_config["quality"]
        config = Config(quality=Quality(quality))
        client_id = self._tidal_config["client_id"]
        client_secret = self._tidal_config["client_secret"]
        self.login_method = self._tidal_config["login_method"]
        self.lazy_connect = self._tidal_config["lazy"]
        self.pkce_enabled = self._tidal_config["pkce_enabled"]
        logger.info("Quality: %s", quality)
        logger.info("Authentication: %s", "PKCE" if self.pkce_enabled else "OAuth")

        # Set the session filename, depending on the type of session
        if self.pkce_enabled:
            self.session_file_path = Path(self.data_dir, "tidal-pkce.json")
        else:
            self.session_file_path = Path(self.data_dir, "tidal-oauth.json")

        if self.login_method == "HACK" and not self._tidal_config["lazy"]:
            logger.warning("HACK login implies lazy connection, setting lazy=True.")
            self.lazy_connect = True
        logger.info("Login method %s", self.login_method)

        if client_id and client_secret:
            logger.info("Using client id & client secret from config")
            config.client_id = client_id
            config.api_token = client_id
            config.client_secret = client_secret
        elif (client_id and not client_secret) or (client_secret and not client_id):
            logger.warning("Always provide both client_id and client_secret")
            logger.info("Using default client id & client secret from python-tidal")
        else:
            logger.info("Using default client id & client secret from python-tidal")

        self._active_session = Session(config)
        if not self.lazy_connect:
            self._login()

    def _login(self):
        """Load session at startup or create a new session"""
        if self._active_session.load_session_from_file(self.session_file_path):
            logger.info(
                "Loaded existing tidal session from file %s...", self.session_file_path
            )
        if not self.session_valid:
            # Attempt to create new session
            if self.pkce_enabled:
                logger.info("Creating new session (PKCE)...")
                self._active_session.login_oauth_simple(function=logger.info)
                # self._active_session.save_session_to_file(self.session_file_path)
            else:
                logger.info("Creating new session (OAuth)...")
                self._active_session.login_oauth_simple(function=logger.info)
                # self._active_session.save_session_to_file(self.session_file_path)

        self._complete_login()

    def _complete_login(self):
        """Perform final steps of login sequence; save session to file"""
        if self.session_valid:
            # Check if session is valid after login
            logger.info("TIDAL Login OK")
            self._active_session.save_session_to_file(self.session_file_path)
            self._logged_in = True
        else:
            logger.error("TIDAL Login Failed")
            raise ConnectionError("Failed to log in.")

    @property
    def logging_in(self) -> bool:
        """Are we currently waiting for user confirmation to log in?"""
        return bool(self._login_future and self._login_future.running())

    @property
    def login_url(self) -> Optional[str]:
        """Start a new login sequence (if not active) and get the latest login URL"""
        if not self._logged_in and not self.logging_in:
            login_url, self._login_future = self._active_session.login_oauth()
            self._login_future.add_done_callback(lambda *_: self._complete_login())
            self._login_url = login_url.verification_uri_complete
        return f"https://{self._login_url}" if self._login_url else None
