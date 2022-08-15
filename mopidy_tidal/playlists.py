from __future__ import unicode_literals

import logging
import operator
import os
import pathlib
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Timer
from typing import Collection, List, Optional, Tuple, Union

try:
    # tidalapi >= 0.7.0
    from tidalapi.playlist import Playlist as TidalPlaylist
except ImportError:
    # tidalapi < 0.7.0
    from tidalapi.models import Playlist as TidalPlaylist

from mopidy.models import Playlist as MopidyPlaylist
from mopidy.models import Ref

from mopidy import backend
from mopidy_tidal import full_models_mappers
from mopidy_tidal.helpers import to_timestamp
from mopidy_tidal.lru_cache import LruCache
from mopidy_tidal.utils import mock_track
from mopidy_tidal.workers import get_items

logger = logging.getLogger(__name__)


class PlaylistCache(LruCache):
    def __getitem__(
        self, key: Union[str, TidalPlaylist], *args, **kwargs
    ) -> MopidyPlaylist:
        uri = key.id if isinstance(key, TidalPlaylist) else key
        assert uri
        uri = f"tidal:playlist:{uri}" if not uri.startswith("tidal:playlist:") else uri

        playlist = super().__getitem__(uri, *args, **kwargs)
        if (
            playlist
            and isinstance(key, TidalPlaylist)
            and to_timestamp(key.last_updated) > to_timestamp(playlist.last_modified)
        ):
            # The playlist has been updated since last time:
            # we should refresh the associated cache entry
            logger.info('The playlist "%s" has been updated: refresh forced', key.name)
            raise KeyError(uri)

        return playlist


class PlaylistMetadataCache(PlaylistCache):
    def _cache_filename(self, key: str) -> str:
        parts = key.split(":")
        assert len(parts) > 2, f"Invalid TIDAL ID: {key}"
        parts[1] += "_metadata"
        cache_dir = os.path.join(self._cache_dir, parts[1], parts[2][:2])
        pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)
        return os.path.join(cache_dir, f"{key}.cache")


class TidalPlaylistsProvider(backend.PlaylistsProvider):
    def __init__(self, *args, **kwargs):
        super(TidalPlaylistsProvider, self).__init__(*args, **kwargs)
        self._playlists_metadata = PlaylistMetadataCache()
        self._playlists = PlaylistCache()
        self._current_tidal_playlists = []
        self._playlists_loaded_event = Event()

    def _calculate_added_and_removed_playlist_ids(
        self,
    ) -> Tuple[Collection[str], Collection[str]]:
        logger.info("Calculating playlist updates..")
        session = self.backend._session  # type: ignore
        updated_playlists = []

        with ThreadPoolExecutor(
            2, thread_name_prefix="mopidy-tidal-playlists-refresh-"
        ) as pool:
            pool_res = pool.map(
                lambda func: get_items(func)
                if func == session.user.favorites.playlists
                else func(),
                [
                    session.user.favorites.playlists,
                    session.user.playlists,
                ],
            )

            for playlists in pool_res:
                updated_playlists += playlists

        self._current_tidal_playlists = updated_playlists
        updated_ids = set(pl.id for pl in updated_playlists)
        if not self._playlists_metadata:
            return updated_ids, set()

        current_ids = set(uri.split(":")[-1] for uri in self._playlists_metadata.keys())
        added_ids = updated_ids.difference(current_ids)
        removed_ids = current_ids.difference(updated_ids)
        self._playlists_metadata.prune(
            *[
                uri
                for uri in self._playlists_metadata.keys()
                if uri.split(":")[-1] in removed_ids
            ]
        )

        return added_ids, removed_ids

    def _has_changes(self, playlist: MopidyPlaylist):
        pl_getter = (
            self.backend._session.get_playlist
            if hasattr(self.backend._session, "get_playlist")
            else self.backend._session.playlist
        )

        upstream_playlist = pl_getter(playlist.uri.split(":")[-1])
        if not upstream_playlist:
            return True

        upstream_last_updated_at = to_timestamp(
            getattr(upstream_playlist, "last_updated", None)
        )
        local_last_updated_at = to_timestamp(playlist.last_modified)

        if not upstream_last_updated_at:
            logger.warning(
                "You are using a version of python-tidal that does not "
                "support last_updated on playlist objects"
            )
            return True

        if upstream_last_updated_at > local_last_updated_at:
            logger.info(
                'The playlist "%s" has been updated: refresh forced', playlist.name
            )
            return True

        return False

    def as_list(self):
        if not self._playlists_loaded_event.is_set():
            added_ids, _ = self._calculate_added_and_removed_playlist_ids()
            if added_ids:
                self.refresh(include_items=False)

        logger.debug("Listing TIDAL playlists..")
        refs = [
            Ref.playlist(uri=pl.uri, name=pl.name)
            for pl in self._playlists_metadata.values()
        ]

        return sorted(refs, key=operator.attrgetter("name"))

    def _lookup_mix(self, uri):
        mix_id = uri.split(":")[-1]
        session = self.backend._session
        return session.mix(mix_id)

    def _get_or_refresh_playlist(self, uri) -> Optional[MopidyPlaylist]:
        parts = uri.split(":")
        if parts[1] == "mix":
            mix = self._lookup_mix(uri)
            return full_models_mappers.create_mopidy_mix_playlist(mix)

        playlist = self._playlists.get(uri)
        if (playlist is None) or (playlist and self._has_changes(playlist)):
            self.refresh(uri, include_items=True)
        return self._playlists.get(uri)

    def create(self, name):
        pass  # TODO

    def delete(self, uri):
        pass  # TODO

    def lookup(self, uri):
        return self._get_or_refresh_playlist(uri)

    def refresh(self, *uris, include_items: bool = True):
        if uris:
            logger.info("Looking up playlists: %r", uris)
        else:
            logger.info("Refreshing TIDAL playlists..")

        session = self.backend._session
        plists = self._current_tidal_playlists
        mapped_playlists = {}
        playlist_cache = self._playlists if include_items else self._playlists_metadata

        for pl in plists:
            uri = "tidal:playlist:" + pl.id
            # Skip or cache hit case
            if (uris and uri not in uris) or pl in playlist_cache:
                continue

            # Cache miss case
            if include_items:
                pl_tracks = self._retrieve_api_tracks(session, pl)
                tracks = full_models_mappers.create_mopidy_tracks(pl_tracks)
            else:
                # Create as many mock tracks as the number of items in the playlist.
                # Playlist metadata is concerned only with the number of tracks, not
                # the actual list.
                tracks = [mock_track] * pl.num_tracks

            mapped_playlists[uri] = MopidyPlaylist(
                uri=uri,
                name=pl.name,
                tracks=tracks,
                last_modified=to_timestamp(pl.last_updated),
            )

        # When we trigger a playlists_loaded event the backend may call as_list
        # again. Set an event for 5 minutes to ensure that we don't perform
        # another playlist sync.
        self._playlists_loaded_event.set()
        Timer(300, lambda: self._playlists_loaded_event.clear()).start()

        # Update the right playlist cache and send the playlists_loaded event.
        playlist_cache.update(mapped_playlists)
        backend.BackendListener.send("playlists_loaded")
        logger.info("TIDAL playlists refreshed")

    def get_items(self, uri) -> Optional[List[Ref]]:
        playlist = self._get_or_refresh_playlist(uri)
        if not playlist:
            return

        return [Ref.track(uri=t.uri, name=t.name) for t in playlist.tracks]

    def _retrieve_api_tracks(self, session, playlist):
        if hasattr(session, "get_playlist_tracks"):
            # tidalapi < 0.7.0
            getter = session.get_playlist_tracks
            getter_args = (playlist.id,)
        else:
            # tidalapi >= 0.7.0
            getter = playlist.tracks
            getter_args = tuple()

        return get_items(getter, *getter_args)

    def save(self, playlist):
        pass  # TODO
