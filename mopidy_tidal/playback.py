from __future__ import unicode_literals

from typing import TYPE_CHECKING

from login_hack import speak_login_hack

if TYPE_CHECKING:  # pragma: no cover
    from mopidy_tidal.backend import TidalBackend

import logging

from mopidy import backend
from tidalapi import Quality
from tidalapi.media import ManifestMimeType
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

        stream = session.track(track_id).get_stream()
        manifest = stream.get_stream_manifest()
        logger.info("MimeType:{}".format(stream.manifest_mime_type))
        logger.info(
            "Starting playback of track:{}, (quality:{}, codec:{}, {}bit/{}Hz)".format(track_id,
                                                                                      stream.audio_quality,
                                                                                      manifest.get_codecs(),
                                                                                      stream.bit_depth,
                                                                                      stream.sample_rate))
        if stream.manifest_mime_type == ManifestMimeType.MPD.value:
            hls = manifest.get_hls()
            if hls:
                hls_path = Path(Extension.get_cache_dir(context.get_config()), "hls.m3u8")
                with open(hls_path, "w") as my_file:
                    my_file.write(hls)
                return "file://{}".format(hls_path)
            else:
                raise AttributeError("No HLS stream available")
        elif stream.manifest_mime_type == ManifestMimeType.BTS.value:
            return manifest.get_urls()
