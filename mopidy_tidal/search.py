from __future__ import unicode_literals

import logging

from threading import Thread

from mopidy_tidal.full_models_mappers import create_mopidy_albums, \
    create_mopidy_artists, create_mopidy_tracks

from mopidy_tidal.utils import remove_watermark

logger = logging.getLogger(__name__)


def tidal_search(session, query, exact, map_to_mopidy_models=True):
    logger.info('Searching Tidal for: %s %r', "Exact" if exact else "", query)
    for (field, values) in query.iteritems():
        if not hasattr(values, '__iter__'):
            values = [values]

        search_val = remove_watermark(values[0])
        if field in ['track_name', 'album', 'artist', 'albumartist', 'any']:
            if exact:
                exact_search = TidalExactSearchThread(session, search_val,
                                                      field)
                exact_search.start()
                exact_search.join()
                results = exact_search.results
            else:
                artist_search = TidalSearchThread(session, search_val,
                                                  "artist")
                artist_search.start()
                album_search = TidalSearchThread(session, search_val,
                                                 "album")
                album_search.start()
                track_search = TidalSearchThread(session, search_val,
                                                 "track")
                track_search.start()
                artist_search.join()
                album_search.join()
                track_search.join()
                results = artist_search.results, \
                    album_search.results, \
                    track_search.results

            if map_to_mopidy_models:
                results = create_mopidy_artists(results[0]), \
                          create_mopidy_albums(results[1]), \
                          create_mopidy_tracks(results[2])

            return results

        return [], [], []


class TidalSearchThread(Thread):
    def __init__(self, session, keyword, kind):
        super(TidalSearchThread, self).__init__()
        self.results = []
        self.session = session
        self.keyword = keyword
        self.kind = kind

    def run(self):
        if self.kind == "artist":
            self.results = self.session.search("artist", self.keyword).artists
        elif self.kind == "album":
            self.results = self.session.search("album", self.keyword).albums
        elif self.kind == "track":
            self.results = self.session.search("track", self.keyword).tracks


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
        res = self.session.search("album", self.keyword).albums
        album = next((a for a in res
                      if a.name.lower() == self.keyword.lower()), None)
        logger.info("Album not found" if album is None else "Album found OK")
        if album:
            self.albums = [album]
            self.tracks = self.session.get_album_tracks(album.id)
            logger.info("Found %d tracks for album", len(self.tracks))

    def search_artist(self):
        res = self.session.search("artist", self.keyword).artists
        logger.info("Found %d artists", len(res))
        for artist in res:
            if artist.name.lower() == self.keyword.lower():
                logger.info("Artist match OK")
                self.artists = [artist]
                break
