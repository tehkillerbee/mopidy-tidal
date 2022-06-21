from __future__ import unicode_literals

import logging

from threading import Thread

from lru_cache import SearchCache

from tidalapi.album import Album
from tidalapi.artist import Artist
from tidalapi.media import Track

import mopidy_tidal.full_models_mappers as mappers
from mopidy_tidal.full_models_mappers import create_mopidy_albums, \
    create_mopidy_artists, create_mopidy_tracks

from mopidy_tidal.utils import remove_watermark

logger = logging.getLogger(__name__)


@SearchCache
def tidal_search(session, query, exact):
    logger.info('Searching Tidal for: %s %r', "Exact" if exact else "", query)
    for (field, values) in query.items():
        if not hasattr(values, '__iter__'):
            values = [values]

        search_val = remove_watermark(values[0])
        if field in ['track_name', 'album', 'artist', 'albumartist', 'any']:
            if exact:
                exact_search = TidalExactSearchThread(session, search_val, field)
                exact_search.start()
                exact_search.join()
                results = exact_search.results
            else:
                search = TidalSearchThread(session, search_val)
                search.start()
                search.join()
                results = search.results

            return results

        return [], [], []


class TidalSearchThread(Thread):
    def __init__(self, session, keyword, kind='any'):
        super(TidalSearchThread, self).__init__()
        self.results = []
        self.session = session
        self.keyword = keyword
        self.kind = kind

    def run(self):
        if self.kind == "any":
            results = self.session.search(self.keyword)
            for field in ('artists', 'albums', 'tracks'):
                field_results = []
                if results.get(field):
                    builder = getattr(mappers, 'create_mopidy_' + field)
                    field_results = builder(results[field])

                self.results.append(field_results)
        elif self.kind == "artist":
            artists = self.session.search(self.keyword, models=[Artist]).get('artists', [])
            self.results = create_mopidy_artists(artists)
        elif self.kind == "album":
            albums = self.session.search(self.keyword, models=[Album]).get('albums', [])
            self.results = create_mopidy_albums(albums)
        elif self.kind == "track":
            tracks = self.session.search(self.keyword, models=[Track]).get('tracks', [])
            self.results = create_mopidy_tracks(tracks)


class TidalExactSearchThread(TidalSearchThread):
    def __init__(self, session, keyword, kind):
        super(TidalExactSearchThread, self).__init__(session, keyword, kind)
        self.artists = []
        self.albums = []
        self.tracks = []
        self.results = [], [], []

    def run(self):
        if self.kind == "album":
            self.search_album()
        elif self.kind == "artist":
            self.search_artist()

        self.results = self.artists, self.albums, self.tracks

    def search_album(self):
        res = self.session.search(self.keyword, models=[Album]).get('albums', [])
        album = next((a for a in res
                      if a.name.lower() == self.keyword.lower()), None)
        logger.info("Album not found" if album is None else "Album found OK")
        if album:
            self.albums = create_mopidy_albums([album])
            tracks = self.session.get_album_tracks(album.id)
            self.tracks = create_mopidy_tracks(tracks)
            logger.info("Found %d tracks for album", len(self.tracks))

    def search_artist(self):
        res = self.session.search(self.keyword, models=[Artist]).get('artists', [])
        logger.info("Found %d artists", len(res))
        for artist in res:
            if artist.name.lower() == self.keyword.lower():
                logger.info("Artist match OK")
                self.artists = create_mopidy_artists([artist])
                break
