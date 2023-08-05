from __future__ import unicode_literals

from typing import TYPE_CHECKING

from login_hack import speak_login_hack

if TYPE_CHECKING:  # pragma: no cover
    from mopidy_tidal.backend import TidalBackend

import logging

from mopidy import backend
from tidalapi import Quality

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):
    backend: "TidalBackend"

    @speak_login_hack
    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        parts = uri.split(":")
        track_id = int(parts[4])
        session = self.backend.session
        if session.config.quality == Quality.master:
            if "HIRES_LOSSLESS" in session.track(track_id).media_metadata_tags:
                logger.info("Playback quality: %s", session.config.quality)
            else:
                logger.info(
                    "No HI_RES available for this track; Using playback quality: %s",
                    "LOSSLESS",
                )

        newurl = session.track(track_id).get_url()
        logger.info("transformed into %s", newurl)
        return newurl
