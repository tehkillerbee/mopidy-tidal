from functools import wraps
from cachetools import LRUCache, cached
from cachetools.keys import hashkey


_by_uri_cache = LRUCache(maxsize=16*1024)
_items_cache = LRUCache(maxsize=16*1024)
_futures_cache = LRUCache(maxsize=16*1024)

cached_by_uri = cached(
    _by_uri_cache,
    key=lambda *args, uri, **kwargs: hash(uri),
)
cached_items = cached(
    _items_cache,
    key=lambda item, *args, **kwargs: hashkey(item.uri, item.last_modified),
)
cached_future = cached(
    _futures_cache,
    key=lambda *args, uri, **kwargs: hash(uri),
)


def cache_by_uri(_callable):
    @wraps(_callable)
    def wrapper(*args, **kwargs):
        item = _callable(*args, **kwargs)
        _by_uri_cache[hash(item.ref.uri)] = item
        return item
    return wrapper


def cache_future(_callable):
    @wraps(_callable)
    def wrapper(*args, **kwargs):
        item = _callable(*args, **kwargs)
        if item:
            _futures_cache[hash(item.ref.uri)] = item
        return item
    return wrapper
