from enum import unique, Enum
from typing import NamedTuple, Optional, Any

from mopidy_tidal import Extension


@unique
class URIType(Enum):
    TRACK = "track"
    ALBUM = "album"
    ARTIST = "artist"
    PLAYLIST = "playlist"
    MIX = "mix"
    PAGE = "page"
    FUTURE = "future"
    DIRECTORY = "directory"

    def __str__(self):
        return str(self.value)


class URIData(NamedTuple):
    uri: str
    type: Any
    id: Optional[str] = None


class URI:
    _ext = Extension.ext_name
    _sep = ":"

    def __init__(self, _type, _id: str = None):
        uri = self._sep.join(map(str, filter(bool, (self._ext, _type, _id))))
        self._data = URIData(uri, _type, _id)

    @classmethod
    def from_string(cls, uri):
        _ext, _type, *_id = uri.split(cls._sep, 2)
        if _ext != URI._ext:
            return None
        try:
            _type = URIType(_type)
        except ValueError:
            pass
        return cls(_type, *_id)

    @property
    def track(self):
        if self.type == URIType.TRACK and self.id:
            return self.id
        raise AttributeError

    @property
    def playlist(self):
        if self.type == URIType.PLAYLIST and self.id:
            return self.id
        raise AttributeError

    @property
    def mix(self):
        if self.type == URIType.MIX and self.id:
            return self.id
        raise AttributeError

    @property
    def album(self):
        if self.type == URIType.ALBUM and self.id:
            return self.id
        raise AttributeError

    @property
    def artist(self):
        if self.type == URIType.ARTIST and self.id:
            return self.id
        raise AttributeError

    @property
    def page(self):
        if self.type == URIType.PAGE and self.id:
            return self.id
        raise AttributeError

    @property
    def future(self):
        if self.type == URIType.FUTURE and self.id:
            return self.id
        raise AttributeError

    def __getattr__(self, item):
        return getattr(self._data, item)

    def __str__(self):
        return self.uri
