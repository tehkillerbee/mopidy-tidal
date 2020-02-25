from __future__ import unicode_literals

import logging

from mopidy.models import Album, Artist, Track


logger = logging.getLogger(__name__)


def create_mopidy_artists(tidal_artists):
    return [create_mopidy_artist(a) for a in tidal_artists]


def create_mopidy_artist(tidal_artist):
    if tidal_artist is None:
        return None

    return Artist(uri="tidal:artist:" + str(tidal_artist.id),
                  name=tidal_artist.name)


def create_mopidy_albums(tidal_albums):
    return [create_mopidy_album(a, None) for a in tidal_albums]


def create_mopidy_album(tidal_album, artist):
    if artist is None:
        artist = create_mopidy_artist(tidal_album.artist)

    return Album(uri="tidal:album:" + str(tidal_album.id),
                 name=tidal_album.name,
                 artists=[artist])


def create_mopidy_tracks(tidal_tracks):
    return [create_mopidy_track(None, None, t) for t in tidal_tracks]


def create_mopidy_track(artist, album, tidal_track):
    uri = "tidal:track:{0}:{1}:{2}".format(tidal_track.artist.id,
                                           tidal_track.album.id,
                                           tidal_track.id)
    if artist is None:
        artist = create_mopidy_artist(tidal_track.artist)
    if album is None:
        album = create_mopidy_album(tidal_track.album, artist)

    track_len = tidal_track.duration * 1000
    return Track(uri=uri,
                 name=tidal_track.name,
                 track_no=tidal_track.track_num,
                 artists=[artist],
                 album=album,
                 length=track_len,
                 disc_no=tidal_track.disc_num)
