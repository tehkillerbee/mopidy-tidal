from __future__ import unicode_literals

import logging

from mopidy import backend, models

from mopidy.models import Image, SearchResult

from mopidy_tidal import full_models_mappers

from mopidy_tidal import ref_models_mappers

from mopidy_tidal.lru_cache import with_cache, image_cache

from mopidy_tidal.search import tidal_search

from mopidy_tidal.utils import apply_watermark

logger = logging.getLogger(__name__)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(uri='tidal:directory', name='Tidal')

    def get_distinct(self, field, query=None):
        logger.debug("Browsing distinct %s with query %r", field, query)

        if not query:  # library root
            if field == "artist" or field == "albumartist":
                return [apply_watermark(a.name) for a in
                        self.backend.session.user.favorites.artists()]
            elif field == "album":
                return [apply_watermark(a.name) for a in
                        self.backend.session.user.favorites.albums()]
            elif field == "track":
                return [apply_watermark(t.name) for t in
                        self.backend.session.user.favorites.tracks()]
        else:
            if field == "artist":
                return [apply_watermark(a.name) for a in
                        self.backend.session.user.favorites.artists()]
            elif field == "album" or field == "albumartist":
                artists, _, _ = tidal_search(self.backend.session,
                                             query=query,
                                             exact=True)
                if len(artists) > 0:
                    artist = artists[0]
                    artist_id = artist.uri.split(":")[3]
                    return [apply_watermark(a.name) for a in
                            self.backend.session.get_artist_albums(artist_id)]
            elif field == "track":
                return [apply_watermark(t.name) for t in
                        self.backend.session.user.favorites.tracks()]

        return []

    def browse(self, uri):
        logger.debug("Browsing uri %s", uri)
        if not uri or not uri.startswith("tidal:"):
            return []

        # summaries

        if uri == self.root_directory.uri:
            return ref_models_mappers.create_root()

        elif uri == "tidal:my_artists":
            return ref_models_mappers.create_artists(
                self.backend.session.user.favorites.artists())
        elif uri == "tidal:my_albums":
            return ref_models_mappers.create_albums(
                self.backend.session.user.favorites.albums())
        elif uri == "tidal:my_playlists":
            return ref_models_mappers.create_playlists(
                self.backend.session.user.favorites.playlists())
        elif uri == "tidal:my_tracks":
            return ref_models_mappers.create_tracks(
                self.backend.session.user.favorites.tracks())
        elif uri == "tidal:moods":
            return ref_models_mappers.create_moods(
                self.backend.session.get_moods())
        elif uri == "tidal:genres":
            return ref_models_mappers.create_genres(
                self.backend.session.get_genres())

        # details

        parts = uri.split(':')
        nr_of_parts = len(parts)

        if nr_of_parts == 4 and parts[1] == "album":
            return ref_models_mappers.create_tracks(
                self.backend.session.get_album_tracks(parts[3]))

        if nr_of_parts == 3 and parts[1] == "artist":
            top_10_tracks = self.backend.session.get_artist_top_tracks(parts[2])[:10]
            albums = ref_models_mappers.create_albums(
                self.backend.session.get_artist_albums(parts[2]))
            return albums + ref_models_mappers.create_tracks(top_10_tracks)

        if nr_of_parts == 3 and parts[1] == "playlist":
            return ref_models_mappers.create_tracks(
                self.backend.session.get_playlist_tracks(parts[2]))

        if nr_of_parts == 3 and parts[1] == "mood":
            return ref_models_mappers.create_playlists(
                self.backend.session.get_mood_playlists(parts[2]))

        if nr_of_parts == 3 and parts[1] == "genre":
            return ref_models_mappers.create_playlists(
                self.backend.session.get_genre_items(parts[2], 'playlists'))

        logger.error('Unknown uri for browse request: %s', uri)
        return []

    def search(self, query=None, uris=None, exact=False):
        try:
            artists, albums, tracks = tidal_search(
                self.backend.session,
                query=query,
                exact=exact)
            return SearchResult(
                artists=artists,
                albums=albums,
                tracks=tracks)
        except Exception as ex:
            logger.critical("%r", ex)

    def get_images(self, uris):
        logger.debug("Searching Tidal for images for %r" % uris)
        return {uri: self._get_images(uri) for uri in uris}

    def _get_images(self, uri):
        parts = uri.split(':')
        if parts[1] == 'track':
            uri = '{0}:album:{2}:{3}'.format(*parts)
            parts = uri.split(':')
        uri_image = image_cache.hit(uri)
        if uri_image is None and self.backend.image_search:
            logger.info('CACHE HIT MISS: %s', uri)
            if parts[1] == 'artist':
                uri_image = self.backend.session.get_artist(artist_id=parts[2]).image
            elif parts[1] == 'album':
                uri_image = self.backend.session.get_album(album_id=parts[3]).image
            logger.info("Setting image cache (%s) with %s = %s", len(image_cache), uri, uri_image)
            image_cache[uri] = uri_image
        return [Image(uri=uri_image, width=512, height=512)] if uri_image else ()

    def lookup(self, uris=None):
        logger.debug("Lookup uris %r", uris)
        if isinstance(uris, str):
            uris = [uris]
        if not hasattr(uris, '__iter__'):
            uris = [uris]
        return [t for tracks in (self._lookup(uri) for uri in uris) for t in tracks]

    @with_cache
    def _lookup(self, uri):
        parts = uri.split(':')
        if uri.startswith('tidal:track:'):
            return self._lookup_track(track_id=parts[4])
        elif uri.startswith('tidal:album:'):
            return self._lookup_album(album_id=parts[3])
        elif uri.startswith('tidal:artist:'):
            return self._lookup_artist(artist_id=parts[2])

    def _lookup_track(self, track_id):
        track = self.backend.session.get_track(track_id)
        return [full_models_mappers.create_mopidy_track(track)]

    def _lookup_album(self, album_id):
        logger.info("Looking up album ID: %s", album_id)
        tracks = self.backend.session.get_album_tracks(album_id)
        return full_models_mappers.create_mopidy_tracks(tracks)

    def _lookup_artist(self, artist_id):
        logger.info("Looking up artist ID: %s", artist_id)
        tracks = self.backend.session.get_artist_top_tracks(artist_id)
        return full_models_mappers.create_mopidy_tracks(tracks)
