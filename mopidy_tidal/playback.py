from __future__ import unicode_literals

import inspect
import logging

from mopidy import backend
from mopidy_tidal.lru_cache import track_cache

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        logger.debug(''.join('{}\n{}'.format(':'.join(str(x) for x in i[1:-2]), ''.join(i[-2]))
                            for i in inspect.stack()))
        parts = uri.split(':')
        track_id = int(parts[4])
        newurl = self.backend.session.get_media_url(track_id)
        logger.info("transformed into %s", newurl)
        cached_track = track_cache.hit(uri)
        logger.info('Track transformed: %s', "({t.length}) {t.name} {t.artists!s} {t.album!s}".format(t=cached_track)
                    if cached_track else "Not cached")
        return newurl
