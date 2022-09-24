from __future__ import unicode_literals

import logging

from mopidy.models import Ref

logger = logging.getLogger(__name__)


def create_root():
    return [
        Ref.directory(uri="tidal:genres", name="Genres"),
        Ref.directory(uri="tidal:moods", name="Moods"),
        Ref.directory(uri="tidal:mixes", name="Mixes"),
        Ref.directory(uri="tidal:my_artists", name="My Artists"),
        Ref.directory(uri="tidal:my_albums", name="My Albums"),
        Ref.directory(uri="tidal:my_playlists", name="My Playlists"),
        Ref.directory(uri="tidal:my_tracks", name="My Tracks"),
    ]


def create_artists(tidal_artists):
    return [create_artist(a) for a in tidal_artists]


def create_artist(tidal_artist):
    return Ref.artist(
        uri="tidal:artist:" + str(tidal_artist.id), name=tidal_artist.name
    )


def create_playlists(tidal_playlists):
    return [create_playlist(p) for p in tidal_playlists]


def create_playlist(tidal_playlist):
    return Ref.playlist(
        uri="tidal:playlist:" + str(tidal_playlist.id), name=tidal_playlist.name
    )


def create_moods(tidal_moods):
    return [create_mood(m) for m in tidal_moods]


def create_mood(tidal_mood):
    mood_id = tidal_mood.api_path.split("/")[-1]
    return Ref.directory(uri="tidal:mood:" + mood_id, name=tidal_mood.title)


def create_genres(tidal_genres):
    return [create_genre(m) for m in tidal_genres]


def create_genre(tidal_genre):
    genre_id = tidal_genre.path
    return Ref.directory(uri="tidal:genre:" + genre_id, name=tidal_genre.name)


def create_mixes(tidal_mixes):
    return [create_mix(m) for m in tidal_mixes]


def create_mix(tidal_mix):
    return Ref.playlist(
        uri="tidal:mix:" + tidal_mix.id,
        name=f"{tidal_mix.title} ({tidal_mix.sub_title})",
    )


def create_albums(tidal_albums):
    return [create_album(a) for a in tidal_albums]


def create_album(tidal_album):
    return Ref.album(uri="tidal:album:" + str(tidal_album.id), name=tidal_album.name)


def create_tracks(tidal_tracks):
    return [create_track(t) for t in tidal_tracks]


def create_track(tidal_track):
    uri = "tidal:track:{0}:{1}:{2}".format(
        tidal_track.artist.id, tidal_track.album.id, tidal_track.id
    )
    return Ref.track(uri=uri, name=tidal_track.name)
