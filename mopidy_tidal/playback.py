from __future__ import unicode_literals

from typing import TYPE_CHECKING

from login_hack import speak_login_hack

if TYPE_CHECKING:  # pragma: no cover
    from mopidy_tidal.backend import TidalBackend

import logging

from mopidy import backend
from tidalapi import Quality
from pathlib import Path

from . import Extension, context

logger = logging.getLogger(__name__)


class TidalPlaybackProvider(backend.PlaybackProvider):
    backend: "TidalBackend"

    @speak_login_hack
    def translate_uri(self, uri):
        logger.info("TIDAL uri: %s", uri)
        parts = uri.split(":")
        track_id = int(parts[4])
        session = self.backend.session
        if session.config.quality == Quality.hi_res_lossless:
            if "HIRES_LOSSLESS" in session.track(track_id).media_metadata_tags:
                logger.info("Playback quality: %s", session.config.quality)
            else:
                logger.info(
                    "No HI_RES available for this track; Using playback quality: %s",
                    "LOSSLESS",
                )
        if session.is_pkce:
            manifest = session.track(track_id).get_stream().get_stream_manifest()
            hls = manifest.get_hls()
            hls_path = Path(Extension.get_cache_dir(context.get_config()), "hls.m3u8")
            with open(hls_path, "w") as my_file:
                my_file.write(hls)
            logger.info("Starting playback of {}, (codec:{}, sampling rate:{} Hz)".format(hls_path, manifest.get_codecs(), manifest.get_sampling_rate()))
            return "file://{}".format(hls_path)
        else:
            newurl = session.track(track_id).get_url()
            logger.info("transformed into %s", newurl)
        return newurl
