from __future__ import unicode_literals

import logging
import multiprocessing
from typing import List, Tuple

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
from mopidy_tidal.workers import get_items


logger = logging.getLogger(__name__)


class ImagesGetter:
    def __init__(self, session):
        self._session = session
        self._image_cache = LruCache(directory='image')

    @staticmethod
    def _log_image_not_found(obj):
        logger.debug('No images available for %s "%s"', type(obj).__name__, obj.name)

    @classmethod
    def _get_image_uri(cls, obj):
        method, tidal_lt_0_7 = None, False

        # tidalapi >= 0.7.0
        if hasattr(obj, 'image'):
            # Handle artists with missing images
            if hasattr(obj, 'picture') and getattr(obj, 'picture', None) is None:
                cls._log_image_not_found(obj)
                return

            method = obj.image

        # tidalapi < 0.7.0
        else:
            method = obj.picture
            tidal_lt_0_7 = True

        dimensions = (750, 640, 480)
        for dim in dimensions:
            args = (dim, dim) if tidal_lt_0_7 else (dim,)
            try:
                return method(*args)
            except ValueError:
                pass

        cls._log_image_not_found(obj)

    def _get_api_getter(self, item_type: str):
        tidal_lt_0_7_getter_name = f'get_{item_type}'
        return (
            # tidalapi < 0.7.0
            getattr(self._session, tidal_lt_0_7_getter_name)
            if hasattr(self._session, tidal_lt_0_7_getter_name)
            # tidalapi >= 0.7.0
            else getattr(self._session, item_type)
        )

    def _get_images(self, uri) -> List[Image]:
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
        getter = self._get_api_getter(item_type)
        if not getter:
            logger.warning(
                'The API item type %s has no session getters',
                item_type
            )
            return []

        item = getter(item_id)
        if not item:
            logger.debug('%r is not available on the backend', uri)
            return []

        img_uri = self._get_image_uri(item)
        if not img_uri:
            logger.debug('%r has no associated images', uri)
            return []

        logger.debug('Image URL for %r: %r', uri, img_uri)
        return [Image(uri=img_uri, width=320, height=320)]

    def __call__(self, uri: str) -> Tuple[str, List[Image]]:
        try:
            return uri, self._get_images(uri)
        except (AssertionError, AttributeError, HTTPError) as err:
            logger.error(
                "%s when processing URI %r: %s",
                type(err), uri, err)
            return uri, []

    def cache_update(self, images):
        self._image_cache.update(images)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(uri='tidal:directory', name='Tidal')

    def __init__(self, *args, **kwargs):
        super(TidalLibraryProvider, self).__init__(*args, **kwargs)
        self._artist_cache = LruCache()
        self._album_cache = LruCache()
        self._track_cache = LruCache()
        self._playlist_cache = PlaylistCache()

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
                    get_items(session.user.favorites.artists))
        elif uri == "tidal:my_albums":
            return ref_models_mappers.create_albums(
                    get_items(session.user.favorites.albums))
        elif uri == "tidal:my_playlists":
            return ref_models_mappers.create_playlists(
                {
                    pl.id: pl
                    for pl in [
                        *session.user.playlists(),
                        *get_items(session.user.favorites.playlists),
                    ]
                }.values()
            )
        elif uri == "tidal:my_tracks":
            return ref_models_mappers.create_tracks(
                    get_items(session.user.favorites.tracks))
        elif uri == "tidal:moods":
            return ref_models_mappers.create_moods(
                    session.get_moods())
        elif uri == "tidal:genres":
            if hasattr(session, 'get_genres'):
                # tidalapi < 0.7.0
                getter = getattr(session, 'get_genres')
            else:
                # tidalapi >= 0.7.0
                getter = getattr(session, 'genre').get_genres

            return ref_models_mappers.create_genres(getter())

        # details

        parts = uri.split(':')
        nr_of_parts = len(parts)

        if nr_of_parts == 3 and parts[1] == "album":
            return ref_models_mappers.create_tracks(
                    session.get_album_tracks(parts[2]))

        if nr_of_parts == 3 and parts[1] == "artist":
            top_10_tracks = self._get_artist_top_tracks(session, parts[2])[:10]
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
            if hasattr(session, 'get_genre_items'):
                # tidalapi < 0.7.0
                items = session.get_genre_items(parts[2], 'playlists')
            else:
                # tidalapi >= 0.7.0
                from tidalapi.playlist import Playlist

                filtered_genres = [g for g in session.genre.get_genres() if parts[2] == g.path]
                if filtered_genres:
                    items = filtered_genres[0].items(Playlist)
                else:
                    items = []

            return ref_models_mappers.create_playlists(items)

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

    def get_images(self, uris):
        logger.info("Searching Tidal for images for %r" % uris)
        images_getter = ImagesGetter(self._session)

        with multiprocessing.Pool(4) as pool:
            pool_res = pool.map(images_getter, uris)

        images = {
            uri: item_images
            for uri, item_images in pool_res
        }

        images_getter.cache_update(images)
        return images

    def lookup(self, uris=None):
        logger.info("Lookup uris %r", uris)
        if isinstance(uris, str):
            uris = [uris]
        if not hasattr(uris, '__iter__'):
            uris = [uris]

        tracks = []
        cache_updates = {}

        for uri in (uris or []):
            data = []
            try:
                parts = uri.split(':')
                item_type = parts[1]
                cache_name = f'_{parts[1]}_cache'
                cache_miss = True

                try:
                    data = getattr(self, cache_name)[uri]
                    cache_miss = not bool(data)
                except (AttributeError, KeyError):
                    pass

                if cache_miss:
                    try:
                        lookup = getattr(self, f'_lookup_{parts[1]}')
                    except AttributeError:
                        continue

                    data = cache_data = lookup(self._session, parts)
                    cache_updates[cache_name] = cache_updates.get(cache_name, {})
                    if item_type == 'playlist':
                        # Playlists should be persisted on the cache as objects,
                        # not as lists of tracks. Therefore, _lookup_playlist
                        # returns a tuple that we need to unpack
                        data, cache_data = data

                    cache_updates[cache_name][uri] = cache_data

                if item_type == 'playlist' and not cache_miss:
                    tracks += data.tracks
                else:
                    tracks += data if hasattr(data, '__iter__') else [data]
            except HTTPError as err:
                logger.error("%s when processing URI %r: %s", type(err), uri, err)

        for cache_name, new_data in cache_updates.items():
            getattr(self, cache_name).update(new_data)

        self._track_cache.update({track.uri:track for track in tracks})
        logger.info("Returning %d tracks", len(tracks))
        return tracks

    @staticmethod
    def _get_playlist(session, playlist_id):
        if hasattr(session, 'get_playlist'):
            # tidalapi < 0.7.0
            return session.get_playlist(playlist_id)

        # tidalapi >= 0.7.0
        return session.playlist(playlist_id)

    @classmethod
    def _get_playlist_tracks(cls, session, playlist_id):
        if hasattr(session, 'get_playlist_tracks'):
            # tidalapi < 0.7.0
            getter = session.get_playlist_tracks
            getter_args = (playlist_id,)
        else:
            # tidalapi >= 0.7.0
            pl = cls._get_playlist(session, playlist_id)
            getter = pl.tracks
            getter_args = tuple()

        return get_items(getter, *getter_args)

    def _lookup_playlist(self, session, parts):
        playlist_uri = ':'.join(parts)
        playlist_id = parts[2]
        playlist = self._playlist_cache.get(playlist_uri)
        if playlist:
            return playlist.tracks

        tidal_playlist = self._get_playlist(session, playlist_id)
        tidal_tracks = self._get_playlist_tracks(session, playlist_id)
        pl_tracks = full_models_mappers.create_mopidy_tracks(tidal_tracks)
        pl = full_models_mappers.create_mopidy_playlist(tidal_playlist, pl_tracks)
        # We need both the list of tracks and the mapped playlist object for
        # caching purposes
        return pl_tracks, pl

    @staticmethod
    def _get_album_tracks(session, album_id):
        if hasattr(session, 'get_album_tracks'):
            # tidalapi < 0.7.0
            return session.get_album_tracks(album_id)

        # tidalapi >= 0.7.0
        album = session.album(album_id)
        if not album:
            logger.warning('No such album: %s', album_id)
            return []

        return album.tracks()

    def _lookup_track(self, session, parts):
        album_id = parts[3]
        album_uri = ':'.join(['tidal', 'album', album_id])

        tracks = self._album_cache.get(album_uri)
        if tracks is None:
            tracks = self._get_album_tracks(session, album_id)

        track = [t for t in tracks if t.id == int(parts[4])][0]
        artist = full_models_mappers.create_mopidy_artist(track.artist)
        album = full_models_mappers.create_mopidy_album(track.album, artist)
        return [full_models_mappers.create_mopidy_track(artist, album, track)]

    def _lookup_album(self, session, parts):
        album_id = parts[2]
        album_uri = ':'.join(parts)

        tracks = self._album_cache.get(album_uri)
        if tracks is None:
            tracks = self._get_album_tracks(session, album_id)

        return full_models_mappers.create_mopidy_tracks(tracks)

    @staticmethod
    def _get_artist_top_tracks(session, artist_id):
        if hasattr(session, 'get_artist_top_tracks'):
            # tidalapi < 0.7.0
            return session.get_artist_top_tracks(artist_id)

        # tidalapi >= 0.7.0
        return session.artist(artist_id).get_top_tracks()

    def _lookup_artist(self, session, parts):
        artist_id = parts[2]
        artist_uri = ':'.join(parts)

        tracks = self._artist_cache.get(artist_uri)
        if tracks is None:
            tracks = self._get_artist_top_tracks(session, artist_id)

        return full_models_mappers.create_mopidy_tracks(tracks)
