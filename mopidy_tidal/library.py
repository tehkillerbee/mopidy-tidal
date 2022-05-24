from __future__ import unicode_literals

import logging

from requests.exceptions import HTTPError

from mopidy import backend, models

from mopidy.models import Image, Playlist, SearchResult

from mopidy_tidal import full_models_mappers, ref_models_mappers

from mopidy_tidal.lru_cache import LruCache

from mopidy_tidal.helpers import to_timestamp

from mopidy_tidal.playlists import PlaylistCache

from mopidy_tidal.utils import apply_watermark


logger = logging.getLogger(__name__)


class TidalLibraryProvider(backend.LibraryProvider):
    root_directory = models.Ref.directory(uri='tidal:directory', name='Tidal')

    def __init__(self, *args, **kwargs):
        super(TidalLibraryProvider, self).__init__(*args, **kwargs)
        self.lru_album_tracks = LruCache(max_size=10)
        self.lru_artist_img = LruCache(persist=False)
        self.lru_album_img = LruCache(persist=False)
        self.lru_playlist_img = LruCache(persist=False)
        self.lru_artist_tracks = LruCache(persist=False)
        self.track_cache = LruCache()
        self.playlist_cache = PlaylistCache()

    def get_distinct(self, field, query=None):
        from mopidy_tidal.search import tidal_search

        logger.debug("Browsing distinct %s with query %r", field, query)
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
                tidal_search(self.backend._session,
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

    def get_images(self, uris):
        logger.info("Searching Tidal for images for %r" % uris)
        session = self.backend._session
        images = {}
        for uri in uris:
            try:
                uri_images = None
                if uri.startswith('tidal:'):
                    parts = uri.split(':')
                    if parts[1] == 'artist':
                        artist_id = parts[2]
                        img_uri = self.lru_artist_img.get(artist_id)
                        if img_uri is None:
                            artist = session.get_artist(artist_id)
                            img_uri = self._get_image_uri(artist)
                            if img_uri:
                                self.lru_artist_img[artist.id] = img_uri

                        uri_images = [Image(uri=img_uri, width=512, height=512)]
                    elif parts[1] == 'album':
                        album_id = parts[2]
                        img_uri = self.lru_album_img.get(uri)

                        if img_uri is None:
                            album = session.get_album(album_id)
                            img_uri = self._get_image_uri(album)
                            if img_uri:
                                self.lru_album_img[album_id] = img_uri

                        uri_images = [Image(uri=img_uri, width=512, height=512)]
                    elif parts[1] == 'playlist':
                        playlist_id = parts[2]
                        img_uri = self.lru_playlist_img.get(uri)
                        if img_uri is None:
                            playlist = session.get_playlist(playlist_id)
                            img_uri = self._get_image_uri(playlist)
                            if img_uri:
                                self.lru_playlist_img[playlist_id] = img_uri

                        uri_images = [Image(uri=img_uri, width=512, height=512)]
                    elif parts[1] == 'track':
                        album_id = parts[3]
                        img_uri = self.lru_album_img.get(uri)

                        if img_uri is None:
                            album = session.get_album(album_id)
                            img_uri = self._get_image_uri(album)
                            if img_uri:
                                self.lru_album_img[album_id] = img_uri

                        uri_images = [Image(uri=img_uri, width=512, height=512)]

                images[uri] = uri_images or ()
            except AttributeError as err:
                logger.error("AttributeError when processing URI %r: %s", uri, err)
            except HTTPError as err:
                logger.error("HTTPError when processing URI %r: %s", uri, err)

        return images

    def lookup(self, uris=None):
        logger.info("Lookup uris %r", uris)
        session = self.backend._session
        if isinstance(uris, str):
            uris = [uris]
        if not hasattr(uris, '__iter__'):
            uris = [uris]

        tracks = []
        for uri in uris:
            try:
                parts = uri.split(':')
                cache = None
                lookup = None

                if uri.startswith('tidal:track:'):
                    cache = self.track_cache
                    lookup = self._lookup_track
                elif uri.startswith('tidal:album'):
                    cache = self.lru_album_tracks
                    lookup = self._lookup_album
                elif uri.startswith('tidal:artist'):
                    cache = self.lru_artist_tracks
                    lookup = self._lookup_artist
                elif uri.startswith('tidal:playlist'):
                    cache = self.playlist_cache
                    lookup = self._lookup_playlist

                if cache is not None and lookup:
                    try:
                        tracks.append(cache[uri])
                    except KeyError:
                        tracks += lookup(session, parts)
                else:
                    logger.debug('Unknown URI type: %s', uri)
            except AttributeError as err:
                logger.error("AttributeError when processing URI %r: %s" % uri, err)
            except HTTPError as err:
                logger.error("HTTPError when processing URI %r: %s", uri, err)

        logger.info("Returning %d tracks", len(tracks))
        self.track_cache.update({track.uri:track for track in tracks})
        return tracks

    def _lookup_playlist(self, session, parts):
        playlist_uri = ':'.join(parts)
        tracks = self.playlist_cache.get(playlist_uri)

        if tracks is None:
            pl = session.get_playlist(playlist_uri)
            tracks = session.get_playlist_tracks(parts[2])
            self.playlist_cache[playlist_uri] = Playlist(
                uri=playlist_uri,
                name=pl.name,
                tracks=tracks,
                last_modified=to_timestamp(pl.last_updated),
            )

        return full_models_mappers.create_mopidy_tracks(tracks)

    def _lookup_track(self, session, parts):
        album_id = parts[3]
        album_uri = ':'.join(parts)

        tracks = self.lru_album_tracks.get(album_uri)
        if tracks is None:
            tracks = session.get_album_tracks(album_id)
            self.lru_album_tracks[album_uri] = tracks

        track = [t for t in tracks if t.id == int(parts[4])][0]
        artist = full_models_mappers.create_mopidy_artist(track.artist)
        album = full_models_mappers.create_mopidy_album(track.album, artist)
        return [full_models_mappers.create_mopidy_track(artist, album, track)]

    def _lookup_album(self, session, parts):
        album_id = parts[2]
        album_uri = ':'.join(parts)

        tracks = self.lru_album_tracks.get(album_uri)
        if tracks is None:
            tracks = session.get_album_tracks(album_id)
            self.lru_album_tracks[album_uri] = tracks

        return full_models_mappers.create_mopidy_tracks(tracks)

    def _lookup_artist(self, session, parts):
        artist_id = parts[2]
        artist_uri = ':'.join(parts)

        tracks = self.playlist_cache.get(artist_uri)
        if tracks is None:
            tracks = session.get_artist_top_tracks(artist_id)
            self.lru_artist_tracks[artist_uri] = tracks

        return full_models_mappers.create_mopidy_tracks(tracks)
