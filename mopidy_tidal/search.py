from __future__ import unicode_literals

import logging
import operator
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from typing import Type, Callable

import tidalapi as tdl
from cachetools import cached, LRUCache
from cachetools.keys import hashkey

from mopidy_tidal.models import Artist, Album, PlaylistAsAlbum, Track
from mopidy_tidal.workers import threaded, paginated

logger = logging.getLogger(__name__)


_search_fields = {
    "any": (tdl.Album, tdl.Artist, tdl.Track, tdl.Playlist),
    "album": (tdl.Album, ),
    "artist": (tdl.Artist, ),
    "albumartist": (tdl.Artist, ),
    "performer": (tdl.Artist, ),
    "composer": (tdl.Artist, ),
    "track_name": (tdl.Track, ),
}


@dataclass
class ResultMeta:
    from_k: str
    from_type: Type
    to_k: str
    to_make: Callable


_result_map = (
    ResultMeta("artists", tdl.Artist, "artists", Artist.from_api, ),
    ResultMeta("albums", tdl.Album, "albums", Album.from_api, ),
    ResultMeta("tracks", tdl.Track, "tracks", Track.from_api, ),
    ResultMeta("playlists", tdl.Playlist, "albums", PlaylistAsAlbum.from_api, ),
)


def to_result(key):
    return next((
        m
        for m in _result_map
        if operator.eq(key, m.from_k) or isinstance(key, m.from_type)
    ), None)


@cached(
    LRUCache(maxsize=128),
    key=lambda *args, query, total, exact: hashkey(
        hashkey(**{k: tuple(v) for k, v in query.items()}),
        total, exact
    )
)
def tidal_search(session: tdl.Session, /, *, query, total, exact=False):
    logger.info(f"Search query: {query!r}")
    queries = {
        _search_fields[k]: query.pop(k)
        # this picks in order search fields
        # and ignores further searches for same type
        for k in reversed(_search_fields)
        if k in query
    }
    if query:  # other fields not mapped will go to playlist search
        # pick first field and ignore subsequent since we can't squash keywords
        queries[(tdl.Playlist, )] = next(v for v in query.values())

    logger.info(f"Search translated query: {queries!r}")
    results = defaultdict(list)
    for thread in threaded(*(
        partial(paginated, partial(session.search, q, models=m), total=total)
        for m, q in queries.items()
    )):
        for page in thread:
            top_hit = page.pop("top_hit", None)
            if top_hit:
                meta = to_result(top_hit)
                if meta:
                    results[meta.to_k].append(meta.to_make(top_hit))
            for k, values in page.items():
                meta = to_result(k)
                if meta:
                    results[meta.to_k].extend(meta.to_make(i) for i in page[k])

    logger.info(f"Search results: {dict((k, len(v)) for k, v in results.items())!r}")
    threaded(*(i.build for items in results.values() for i in items), max_workers=10)
    logger.info(f"Search results built")
    return {k: [i.full for i in v] for k, v in results.items()}

