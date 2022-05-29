from __future__ import unicode_literals

import logging
from typing import Optional, List

from requests.exceptions import HTTPError

from mopidy import backend, models

from mopidy.models import Image, SearchResult

from mopidy_tidal import (
    full_models_mappers,
    ref_models_mappers,
)

from mopidy_tidal.lru_cache import LruCache

from mopidy_tidal.playlists import PlaylistCache

from mopidy_tidal.utils import apply_watermark


logger = logging.getLogger(__name__)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(uri='tidal:directory', name='Tidal')

    def __init__(self, *args, **kwargs):
        super(TidalLibraryProvider, self).__init__(*args, **kwargs)
        self._artist_cache = LruCache()
        self._album_cache = LruCache()
        self._track_cache = LruCache()
        self._playlist_cache = PlaylistCache()
        self._image_cache = LruCache(directory='image')

    @property
    def _session(self):
        return self.backend._session   # type: ignore

    def get_distinct(self, field, query=None):
        from mopidy_tidal.search import tidal_search

        logger.debug("Browsing distinct %s with query %r", field, query)
        session = self._session

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
                                             query=query,
                                             exact=True)
                if len(artists) > 0:
                    artist = artists[0]
                    artist_id = artist.uri.split(":")[2]
                    return [apply_watermark(a.name) for a in
                            session.get_artist_albums(artist_id)]
            elif field == "track":
                return [apply_watermark(t.name) for t in
                        session.user.favorites.tracks()]
            pass

        return []

    def browse(self, uri):
        logger.info("Browsing uri %s", uri)
        if not uri or not uri.startswith("tidal:"):
            return []

        session = self._session

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
        elif uri == "tidal:my_tracks":
            return ref_models_mappers.create_tracks(
                    session.user.favorites.tracks())
        elif uri == "tidal:moods":
            return ref_models_mappers.create_moods(
                    session.get_moods())
        elif uri == "tidal:genres":
            return ref_models_mappers.create_genres(
                    session.get_genres())

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

        if nr_of_parts == 3 and parts[1] == "playlist":
            return ref_models_mappers.create_tracks(
                session.get_playlist_tracks(parts[2]))

        if nr_of_parts == 3 and parts[1] == "mood":
            return ref_models_mappers.create_playlists(
                session.get_mood_playlists(parts[2]))

        if nr_of_parts == 3 and parts[1] == "genre":
            return ref_models_mappers.create_playlists(
                session.get_genre_items(parts[2], 'playlists'))

        logger.debug('Unknown uri for browse request: %s', uri)
        return []

    def search(self, query=None, uris=None, exact=False):
        from mopidy_tidal.search import tidal_search

        try:
            artists, albums, tracks = \
                tidal_search(self._session,
                             query=query,
                             exact=exact)
            return SearchResult(artists=artists,
                                albums=albums,
                                tracks=tracks)
        except Exception as ex:
            logger.info("EX")
            logger.info("%r", ex)

    @staticmethod
    def _get_image_uri(obj):
        try:
            return obj.image
        except AttributeError:
            pass

    def _get_image(self, uri) -> Optional[List[Image]]:
        assert uri.startswith('tidal:'), f'Invalid TIDAL URI: {uri}'

        parts = uri.split(':')
        item_type = parts[1]
        if item_type == 'track':
            # For tracks, retrieve the artwork of the associated album
            item_type = 'album'
            item_id = parts[3]
            uri = ':'.join([parts[0], 'album', parts[3]])
        else:
            item_id = parts[2]

        if uri in self._image_cache:
            # Cache hit
            return self._image_cache[uri]

        logger.debug('Retrieving %r from the API', uri)
        getter_name = f'get_{item_type}'
        getter = getattr(self._session, getter_name, None)
        assert getter, f'No such session method: {getter_name}'

        item = getter(item_id)
        if not item:
            logger.debug('%r is not available on the backend', uri)
            return None

        img_uri = self._get_image_uri(item)
        if not img_uri:
            return None

        return [Image(uri=img_uri, width=320, height=320)]

    def get_images(self, uris):
        logger.info("Searching Tidal for images for %r" % uris)
        images = {}

        for uri in uris:
            try:
                images[uri] = self._get_image(uri)
            except (AssertionError, AttributeError, HTTPError) as err:
                logger.error(
                    "%s when processing URI %r: %s",
                    type(err), uri, err)

        self._image_cache.update(images)
        return images

    def lookup(self, uris=None):
        logger.info("Lookup uris %r", uris)
        if isinstance(uris, str):
            uris = [uris]
        if not hasattr(uris, '__iter__'):
            uris = [uris]

        tracks = []
        for uri in (uris or []):
            data = []
            try:
                parts = uri.split(':')
                cache = getattr(self, f'_{parts[1]}_cache')
                lookup = getattr(self, f'_lookup_{parts[1]}')

                try:
                    data = cache[uri]
                except KeyError:
                    data = lookup(self._session, parts)

                tracks += data if hasattr(data, '__iter__') else [data]
            except (AttributeError, HTTPError) as err:
                logger.error("%s when processing URI %r: %s", type(err), uri, err)

        logger.info("Returning %d tracks", len(tracks))
        self._track_cache.update({track.uri:track for track in tracks})
        return tracks

    def _lookup_playlist(self, session, parts):
        playlist_uri = ':'.join(parts)
        playlist = self._playlist_cache.get(playlist_uri)

        if playlist is None:
            pl = session.get_playlist(playlist_uri)
            tracks = session.get_playlist_tracks(parts[2])
            playlist = self._playlist_cache[playlist_uri] = (
                full_models_mappers.create_mopidy_playlist(pl, tracks)
            )

        return full_models_mappers.create_mopidy_tracks(playlist.tracks)

    def _lookup_track(self, session, parts):
        album_id = parts[3]
        album_uri = ':'.join(['tidal', 'album', album_id])

        tracks = self._album_cache.get(album_uri)
        if tracks is None:
            tracks = session.get_album_tracks(album_id)

        track = [t for t in tracks if t.id == int(parts[4])][0]
        artist = full_models_mappers.create_mopidy_artist(track.artist)
        album = full_models_mappers.create_mopidy_album(track.album, artist)
        return [full_models_mappers.create_mopidy_track(artist, album, track)]

    def _lookup_album(self, session, parts):
        album_id = parts[2]
        album_uri = ':'.join(parts)

        tracks = self._album_cache.get(album_uri)
        if tracks is None:
            tracks = session.get_album_tracks(album_id)

        self._album_cache[album_uri] = full_models_mappers.create_mopidy_tracks(tracks)
        return self._album_cache[album_uri]

    def _lookup_artist(self, session, parts):
        artist_id = parts[2]
        artist_uri = ':'.join(parts)

        tracks = self._artist_cache.get(artist_uri)
        if tracks is None:
            tracks = session.get_artist_top_tracks(artist_id)

        self._artist_cache[artist_uri] = full_models_mappers.create_mopidy_tracks(tracks)
        return self._artist_cache[artist_uri]
