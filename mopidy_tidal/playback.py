from __future__ import unicode_literals

import logging

from cachetools import TTLCache, cachedmethod
from mopidy import backend
from mopidy_tidal.uri import URI

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):

    __cache = TTLCache(maxsize=128, ttl=120)

    @cachedmethod(lambda slf: slf.__cache)
    def translate_uri(self, uri):
        logger.debug("TidalPlaybackProvider translate_uri: %s", uri)
        return self.backend.session.track(URI.from_string(uri).track).get_url()
