from __future__ import unicode_literals

import logging

from mopidy import backend

from pykka import ThreadingActor

from tidalapi import Config, Session, Quality

from mopidy_tidal import library, playback, playlists


logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(TidalBackend, self).__init__()
        self._session = None
        self._config = config
        self._username = config['tidal']['username']
        self._password = config['tidal']['password']
        self.playback = playback.TidalPlaybackProvider(audio=audio,
                                                       backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        if config['tidal']['spotify_proxy']:
            self.uri_schemes = ['tidal', 'spotify']
        else:
            self.uri_schemes = ['tidal']

    def on_start(self):
        quality = self._config['tidal']['quality']
        logger.info("Connecting to TIDAL.. Quality = %s" % quality)
        config = Config(quality=Quality(quality))
        self._session = Session(config)
        if self._session.login(self._username, self._password):
            logger.info("TIDAL Login OK")
        else:
            logger.info("TIDAL Login KO")
