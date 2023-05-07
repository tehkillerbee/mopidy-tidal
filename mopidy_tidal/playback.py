from __future__ import unicode_literals

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mopidy_tidal.backend import TidalBackend

import logging

from mopidy import backend

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):
    backend: "TidalBackend"

    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        parts = uri.split(":")
        track_id = int(parts[4])
        session = self.backend.session

        newurl = session.track(track_id).get_url()
        logger.info("transformed into %s", newurl)
        return newurl
