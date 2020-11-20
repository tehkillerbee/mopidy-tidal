from __future__ import unicode_literals

import logging

from mopidy import backend
from mopidy_tidal.lru_cache import track_cache
from mopidy_tidal.utils import inspect_stack

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        logger.debug(inspect_stack())
        parts = uri.split(':')
        track_id = int(parts[4])
        newurl = self.backend.session.get_media_url(track_id)
        cached_track = track_cache.hit(uri)
        logger.info("TIDAL track: ({t.length}) {t.name} - {artists} : {t.album.name}".format(
            t=cached_track, artists=' & '.join(a.name for a in cached_track.artists))
            if cached_track else "Not cached")
        logger.info("translated into %s", newurl)
        return newurl
