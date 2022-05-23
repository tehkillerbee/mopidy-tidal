from __future__ import unicode_literals

import logging
import operator
import os
import pathlib
import pickle
from typing import Optional, Union

from mopidy import backend
from mopidy.models import Playlist as MopidyPlaylist, Ref

from mopidy_tidal import full_models_mappers, Extension
from tidalapi.models import Playlist as TidalPlaylist

logger = logging.getLogger(__name__)


class TidalPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, *args, **kwargs):
        super(TidalPlaylistsProvider, self).__init__(*args, **kwargs)
        self._playlists = None

    def as_list(self):
        if self._playlists is None:
            self.refresh()

        logger.debug("Listing TIDAL playlists..")
        refs = [
            Ref.playlist(uri=pl.uri, name=pl.name)
            for pl in self._playlists.values()]
        return sorted(refs, key=operator.attrgetter('name'))

    def get_items(self, uri):
        if self._playlists is None:
            self.refresh()

        playlist = self._playlists.get(uri)
        if playlist is None:
            return None
        return [Ref.track(uri=t.uri, name=t.name) for t in playlist.tracks]

    def create(self, name):
        pass  # TODO

    def delete(self, uri):
        pass  # TODO

    def lookup(self, uri):
        return self._playlists.get(uri)

    def refresh(self):
        logger.info("Refreshing TIDAL playlists..")
        playlists = {}
        session = self.backend._session

        plists = session.user.favorites.playlists()
        for pl in plists:
            pl.name = "* " + pl.name
        # Append favourites to end to keep the tagged name if there are
        # duplicates
        plists = session.user.playlists() + plists

        for pl in plists:
            uri = "tidal:playlist:" + pl.id
            try:
                cached_playlist = self._get_cached_playlist(pl)
                if cached_playlist:
                    playlists[uri] = cached_playlist
                    continue
            except Exception as e:
                logger.warning(f'Could not load cached playlist {pl.id}: {e}')

            pl_tracks = session.get_playlist_tracks(pl.id)
            tracks = full_models_mappers.create_mopidy_tracks(pl_tracks)
            playlists[uri] = MopidyPlaylist(uri=uri,
                                      name=pl.name,
                                      tracks=tracks,
                                      last_modified=pl.last_updated)
            self._cache_playlist(pl.id, playlists[uri])

        self._playlists = playlists
        backend.BackendListener.send('playlists_loaded')

    def save(self, playlist):
        pass  # TODO

    @property
    def _cache_dir(self) -> str:
        cache_dir = os.path.join(self.backend.cache_dir, 'playlists')
        pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)
        return cache_dir

    def _get_cached_playlist(self, playlist: TidalPlaylist) -> Optional[MopidyPlaylist]:
        playlist_cache = os.path.join(self._cache_dir, f'{playlist.id}.cache')
        if not os.path.isfile(playlist_cache):
            return

        with open(playlist_cache, 'rb') as f:
            cached_playlist: MopidyPlaylist = pickle.load(f)

        if (playlist.last_updated or 0) > (cached_playlist.last_modified or 0):
            # The playlist has been updated since last time:
            # we should refresh the cache
            return

        return cached_playlist

    def _cache_playlist(self, tidal_id: Union[str, int], playlist: MopidyPlaylist):
        playlist_cache = os.path.join(self._cache_dir, f'{tidal_id}.cache')
        with open(playlist_cache, 'wb') as f:
            pickle.dump(playlist, f)

