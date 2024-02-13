from __future__ import unicode_literals

import logging

from mopidy import backend
from mopidy.models import Ref, SearchResult

from mopidy_tidal.models import lookup_uri, model_factory_map
from mopidy_tidal.search import tidal_search
from mopidy_tidal.utils import apply_watermark
from mopidy_tidal.uri import URI, URIType

logger = logging.getLogger(__name__)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = Ref.directory(uri=str(URI(URIType.DIRECTORY)), name="Tidal")

    def get_distinct(self, field, query=None):
        from mopidy_tidal.search import tidal_search

        logger.info(f"Browsing distinct {field!s} with query {query!r}")
        session = self.backend.session

        if not query:  # library root
            if field == "artist" or field == "albumartist":
                return [
                    apply_watermark(a.name) for a in session.user.favorites.artists()
                ]
            elif field == "album":
                return [
                    apply_watermark(a.name) for a in session.user.favorites.albums()
                ]
            elif field == "track":
                return [
                    apply_watermark(t.name) for t in session.user.favorites.tracks()
                ]
        else:
            if field == "artist":
                return [
                    apply_watermark(a.name) for a in session.user.favorites.artists()
                ]
            elif field == "album" or field == "albumartist":
                artists, _, _ = tidal_search(session, query=query, exact=True)
                if len(artists) > 0:
                    artist = artists[0]
                    artist_id = artist.uri.split(":")[2]
                    return [
                        apply_watermark(a.name)
                        for a in self._get_artist_albums(session, artist_id)
                    ]
            elif field == "track":
                return [
                    apply_watermark(t.name) for t in session.user.favorites.tracks()
                ]
            pass

        logger.warning(f"Browse distinct failed for: {field}")
        return []

    def browse(self, uri):
        logger.debug(f"TidalLibraryProvider.browse {uri}")
        uri = URI.from_string(uri)
        if not uri:
            return []

        session = self.backend.session

        # summaries

        summaries = {
            "genres": session.genres,
            "moods": session.moods,
            "mixes": session.mixes,
            "my_artists": session.user.favorites.artists,
            "my_albums": session.user.favorites.albums,
            "my_playlists": session.user.favorites.playlists,
            "my_tracks": session.user.favorites.tracks,
            # "my_mixes": session.user.favorites.mixes_and_radio,
            "playlists": session.user.playlists,
        }

        if uri.type == URIType.DIRECTORY:
            return [
                Ref.directory(uri=str(URI(summary)), name=summary.replace("_", " ").title())
                for summary in summaries
            ]

        summary = summaries.get(uri.type)
        if summary:
            return [m.ref for m in model_factory_map(summary())]

        # details

        try:
            model = lookup_uri(session, uri)
        except ValueError:
            logger.warning("Browse request failed for: %s", uri)
            return []
        else:
            if model:
                return [item.ref for item in model.items()]
            logger.warning("Browse request failed for: %s", uri)
            return []

    def search(self, query=None, uris=None, exact=False):
        total = self.backend.get_config("search_result_count")
        return SearchResult(**tidal_search(
            self.backend.session, query=query, total=total, exact=exact
        ))

    def get_images(self, uris):
        images = {
            uri: lookup_uri(self.backend.session, uri).images
            for uri in uris
        }
        return images

    def lookup(self, uris):
        logger.debug(f"TidalLibraryProvider.lookup({uris!r})")
        if isinstance(uris, str) or not hasattr(uris, "__iter__"):
            uris = [uris]
        return [
            t.full
            for uri in uris
            for t in lookup_uri(self.backend.session, uri).tracks()
        ]
