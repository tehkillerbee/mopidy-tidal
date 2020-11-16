from __future__ import unicode_literals

import logging

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from mopidy import backend

from pykka import ThreadingActor

from tidalapi import Config, Session, Quality

from mopidy_tidal import library, playback, playlists
from mopidy_tidal.auth_http_server import start_oauth_deamon

logger = logging.getLogger(__name__)


class TidalBackend(ThreadingActor, backend.Backend):
    def __init__(self, config, audio):
        super(TidalBackend, self).__init__()
        self.session = None
        self._config = config
        self._token = config['tidal']['token']
        self._oauth = config['tidal']['oauth']
        self._oauth_port = config['tidal'].get('oauth_port')
        self.disable_images = config['tidal']['disable_images']
        self.quality = self._config['tidal']['quality']
        self.playback = playback.TidalPlaybackProvider(audio=audio,
                                                       backend=self)
        self.library = library.TidalLibraryProvider(backend=self)
        self.playlists = playlists.TidalPlaylistsProvider(backend=self)
        self.uri_schemes = ['tidal']

    def on_start(self):
        logger.info("Connecting to TIDAL.. Quality = %s" % self.quality)
        config = Config(self._token, self._oauth, quality=Quality(self.quality))
        self.session = Session(config)
        if self._oauth_port:
            start_oauth_deamon(self.session, self._oauth_port)

