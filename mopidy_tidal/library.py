from __future__ import unicode_literals

import logging

from mopidy import backend, models

from mopidy.models import SearchResult

from mopidy_tidal import full_models_mappers

from mopidy_tidal import ref_models_mappers

from mopidy_tidal.lru_cache import LruCache

from mopidy_tidal.search import tidal_search

from mopidy_tidal.utils import apply_watermark

logger = logging.getLogger(__name__)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(uri='tidal:directory', name='Tidal')

    def __init__(self, *args, **kwargs):
        super(TidalLibraryProvider, self).__init__(*args, **kwargs)
        self.lru_album_tracks = LruCache(max_size=10)

    def get_distinct(self, field, query=None):
        logger.info("Browsing distinct %s with query %r", field, query)
        session = self.backend._session

        if not query:  # library root
            if field == "artist" or field == "albumartist":
                return [apply_watermark(a.name) for a in
                        session.user.favorites.artists()]
            elif field == "album":
                return [apply_watermark(a.name) for a in
                        session.user.favorites.albums()]
            elif field == "track":
                return [apply_watermark(t.name) for t in
                        session.user.favorites.tracks()]
        else:
            if field == "artist":
                return [apply_watermark(a.name) for a in
                        session.user.favorites.artists()]
            elif field == "album" or field == "albumartist":
                artists, _, _ = tidal_search(session,
                                             query,
                                             exact=True,
                                             map_to_mopidy_models=False)
                if len(artists) > 0:
                    artist = artists[0]
                    return [apply_watermark(a.name) for a in
                            session.get_artist_albums(artist.id)]
            elif field == "track":
                return [apply_watermark(t.name) for t in
                        session.user.favorites.tracks()]
            pass

        return []

    def browse(self, uri):
        logger.info("Browsing uri %s", uri)
        if not uri or not uri.startswith("tidal:"):
            return []

        session = self.backend._session

        # summaries

        if uri == self.root_directory.uri:
            return ref_models_mappers.create_root()

        elif uri == "tidal:my_artists":
            return ref_models_mappers.create_artists(
                    session.user.favorites.artists())
        elif uri == "tidal:my_albums":
            return ref_models_mappers.create_albums(
                    session.user.favorites.albums())
        elif uri == "tidal:my_playlists":
            return ref_models_mappers.create_playlists(
                    session.user.favorites.playlists())

        # details

        parts = uri.split(':')
        nr_of_parts = len(parts)

        if nr_of_parts == 3 and parts[1] == "album":
            return ref_models_mappers.create_tracks(
                    session.get_album_tracks(parts[2]))

        if nr_of_parts == 3 and parts[1] == "artist":
            top_10_tracks = session.get_artist_top_tracks(parts[2])[:10]
            albums = ref_models_mappers.create_albums(
                    session.get_artist_albums(parts[2]))
            return albums + ref_models_mappers.create_tracks(top_10_tracks)

        logger.debug('Unknown uri for browse request: %s', uri)
        return []

    def search(self, query=None, uris=None, exact=False):
        try:
            artists, albums, tracks = \
                tidal_search(self.backend._session, query, exact)
            return SearchResult(artists=artists,
                                albums=albums,
                                tracks=tracks)
        except Exception as ex:
            logger.info("EX")
            logger.info("%r", ex)

    def lookup(self, uris=None):
        logger.info("Lookup uris %r", uris)
        session = self.backend._session
        if not hasattr(uris, '__iter__'):
            uris = [uris]

        tracks = []
        for uri in uris:
            parts = uri.split(':')
            if uri.startswith('tidal:track:'):
                tracks += self._lookup_track(session, parts)
            elif uri.startswith('tidal:album'):
                tracks += self._lookup_album(session, parts)
            elif uri.startswith('tidal:artist'):
                tracks += self._lookup_artist(session, parts)

        logger.info("Returning %d tracks", len(tracks))
        return tracks

    def _lookup_track(self, session, parts):
        album_id = parts[3]
        tracks = self.lru_album_tracks.hit(album_id)
        if tracks is None:
            tracks = session.get_album_tracks(album_id)
            self.lru_album_tracks[album_id] = tracks

        track = [t for t in tracks if t.id == int(parts[4])][0]
        artist = full_models_mappers.create_mopidy_artist(track.artist)
        album = full_models_mappers.create_mopidy_album(track.album, artist)
        return [full_models_mappers.create_mopidy_track(artist, album, track)]

    def _lookup_album(self, session, parts):
        album_id = parts[2]
        tracks = session.get_album_tracks(album_id)
        return full_models_mappers.create_mopidy_tracks(tracks)

    def _lookup_artist(self, session, parts):
        artist_id = parts[2]
        artist_tracks = session.get_artist_top_tracks(artist_id)
        return full_models_mappers.create_mopidy_tracks(artist_tracks)
