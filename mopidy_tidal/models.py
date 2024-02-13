__all__ = (
    "Track",
    "Album",
    "Artist",
    "Playlist",
    "Mix",
    "Page",
    "lookup_uri",
    "model_factory",
    "model_factory_map",
)

import logging

import mopidy.models as mm
import tidalapi as tdl

from mopidy_tidal.cache import cache_by_uri, cached_by_uri, cached_items, cache_future, cached_future
from mopidy_tidal.helpers import to_timestamp, return_none
from mopidy_tidal.uri import URI, URIType
from mopidy_tidal.workers import paginated

DEFAULT_IMAGE = "https://tidal.com/browse/assets/images/defaultImages/default{0.__class__.__name__}Image.png".format
IMAGE_SIZE = 320

logger = logging.getLogger(__name__)


class Model:
    def __init__(self, *, ref, api, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.ref = ref
        self.api = api
        self._full = None

    @classmethod
    def from_api(cls, api):
        raise NotImplementedError

    @classmethod
    def from_uri(cls, session: tdl.Session, /, *, uri: str):
        raise NotImplementedError

    @property
    def uri(self):
        return self.ref.uri

    @property
    def name(self):
        return self.ref.name

    @property
    def full(self):
        if self._full is None:
            self._full = self.build()
        return self._full

    @property
    def last_modified(self):
        return to_timestamp("today")

    def build(self):
        raise NotImplementedError

    def items(self):
        raise NotImplementedError

    def tracks(self):
        raise NotImplementedError

    @property
    def images(self):
        raise NotImplementedError


class Track(Model):
    artists = []
    album = None

    @classmethod
    @cache_by_uri
    def from_api(cls, track: tdl.Track):
        uri = URI(URIType.TRACK, track.id)
        return cls(
            ref=mm.Ref.track(uri=str(uri), name=track),
            api=track,
            artists=[Artist.from_api(artist) for artist in track.artists],
            album=Album.from_api(track.album) if track.album else None,
        )

    @classmethod
    @cached_by_uri
    def from_uri(cls, session: tdl.Session, /, *, uri):
        uri = URI.from_string(uri)
        if uri.type != URIType.TRACK:
            raise ValueError("Not a valid uri for Track: %s", uri)
        track = session.track(uri.track)
        return cls(
            ref=mm.Ref.track(uri=str(uri), name=track),
            api=track,
            artists=[Artist.from_api(artist) for artist in track.artists],
            album=Album.from_api(track.album) if track.album else None,
        )

    def items(self):
        raise AttributeError

    def tracks(self):
        return [self]

    def radio(self):
        return [
            Track.from_api(t)
            for t in self.api.radio().items()
            if isinstance(t, tdl.Track)
        ]

    def build(self):
        return mm.Track(
            uri=self.uri,
            name=self.name,
            track_no=self.api.track_num,
            artists=[artist.full for artist in self.artists],
            album=self.album.full if self.album else None,
            length=self.api.duration * 1000,
            date=str(self.api.album.year) if self.api.album.year else None,
            disc_no=self.api.volume_num,
            genre=self.api.audio_quality.value,
            comment=' '.join(map(str, self.api.media_metadata_tags)),
        )

    @property
    def images(self):
        images = [*self.album.images, *(img for artist in self.artists for img in artist.images)]
        if all("/defaultImages/" in img.uri for img in images):
            images = [mm.Image(uri=DEFAULT_IMAGE(self), width=IMAGE_SIZE, height=IMAGE_SIZE)]
        return images


class Album(Model):
    artists = []

    @classmethod
    def from_api(cls, album: tdl.Album):
        uri = URI(URIType.ALBUM, album.id)
        return cls(
            ref=mm.Ref.album(uri=str(uri), name=album.name),
            api=album,
            artists=[Artist.from_api(artist) for artist in album.artists],
        )

    @classmethod
    def from_uri(cls, session: tdl.Session, uri: str):
        uri = URI.from_string(uri)
        if uri.type != URIType.ALBUM:
            raise ValueError("Not a valid uri for Album: %s", uri)
        album = session.album(uri.album)
        return cls(
            ref=mm.Ref.album(uri=str(uri), name=album.name),
            api=album,
            artists=[Artist.from_api(artist) for artist in album.artists],
        )

    def build(self):
        return mm.Album(
            uri=self.uri,
            name=self.name,
            artists=[artist.full for artist in self.artists],
            num_tracks=self.api.num_tracks,
            num_discs=self.api.num_volumes,
            date=str(self.api.year) if self.api.year else None,
        )

    def items(self):
        return [
            Future.from_api(self.api.page, ref_type=mm.Ref.DIRECTORY, title=f"Page: {self.name}"),
            *self.tracks()
        ]

    def tracks(self):
        return [Track.from_api(t) for t in self.api.tracks()]

    @property
    def images(self):
        image_uri = self.api.image(IMAGE_SIZE) if self.api.cover else DEFAULT_IMAGE(self)
        return [mm.Image(uri=image_uri, width=IMAGE_SIZE, height=IMAGE_SIZE)]


class Artist(Model):
    @classmethod
    def from_api(cls, artist: tdl.Artist):
        uri = URI(URIType.ARTIST, artist.id)
        return cls(
            ref=mm.Ref.artist(uri=str(uri), name=artist.name),
            api=artist,
        )

    @classmethod
    def from_uri(cls, session: tdl.Session, uri: str):
        uri = URI.from_string(uri)
        if uri.type != URIType.ARTIST:
            raise ValueError("Not a valid uri for Artist: %s", uri)
        artist = session.artist(uri.artist)
        return cls(
            ref=mm.Ref.artist(uri=str(uri), name=artist.name),
            api=artist,
        )

    def build(self):
        return mm.Artist(
            uri=self.uri,
            name=self.name,
            # sortname=self.api.name,
        )

    def items(self):
        return [
            Future.from_api(self.api.page, ref_type=mm.Ref.DIRECTORY, title=f"Page: {self.name}"),
            Future.from_api(self.api.get_radio, ref_type=mm.Ref.PLAYLIST, title=f"Radio: {self.name}"),
            *self.tracks(),
            *(Album.from_api(album) for album in self.api.get_albums()),
        ]

    def tracks(self, limit=10):
        return [Track.from_api(track) for track in self.api.get_top_tracks(limit=limit)]

    @property
    def images(self):
        image_uri = self.api.image(IMAGE_SIZE) if self.api.picture else DEFAULT_IMAGE(self)
        return [mm.Image(uri=image_uri, width=IMAGE_SIZE, height=IMAGE_SIZE)]


class Playlist(Model):
    @classmethod
    def from_api(cls, playlist: tdl.Playlist):
        uri = URI(URIType.PLAYLIST, playlist.id)
        return cls(
            ref=mm.Ref.playlist(uri=str(uri), name=playlist.name),
            api=playlist,
        )

    @classmethod
    def from_uri(cls, session, uri):
        uri = URI.from_string(uri)
        if uri.type != URIType.PLAYLIST:
            raise ValueError("Not a valid uri for Playlist: %s", uri)
        playlist = session.playlist(uri.playlist)
        return cls(
            ref=mm.Ref.playlist(uri=str(uri), name=playlist.name),
            api=playlist,
        )

    @property
    def last_modified(self):
        return to_timestamp(self.api.last_updated)

    def build(self):
        return mm.Playlist(
            uri=self.uri,
            name=self.name,
            tracks=[t.full for t in self.items()],
            last_modified=self.last_modified,
        )

    def items(self):
        return self.tracks()

    @cached_items
    def tracks(self):
        return [
            Track.from_api(item)
            for page in paginated(self.api.tracks, total=self.api.num_tracks)
            for item in page
            if isinstance(item, tdl.Track)
        ]

    @property
    def images(self):
        image_uri = self.api.image(IMAGE_SIZE) if self.api.square_picture else DEFAULT_IMAGE(self)
        return [mm.Image(uri=image_uri, width=IMAGE_SIZE, height=IMAGE_SIZE)]


class PlaylistAsAlbum(Playlist):
    def build(self):
        return mm.Album(
            uri=self.uri,
            name=self.name,
            artists=[Artist.from_api(artist).full for artist in self.api.promoted_artists or []],
            num_tracks=self.api.num_tracks,
            num_discs=1,
            date=str(self.api.created.year) if self.api.created else None,
        )


class Mix(Model):
    @classmethod
    def from_api(cls, mix: tdl.Mix):
        uri = URI(URIType.MIX, mix.id)
        return cls(
            ref=mm.Ref.playlist(uri=str(uri), name=f"{mix.title} ({mix.sub_title})"),
            api=mix,
        )

    @classmethod
    def from_uri(cls, session: tdl.Session, /, *, uri: str):
        uri = URI.from_string(uri)
        if uri.type != URIType.MIX:
            raise ValueError("Not a valid uri for Mix: %s", uri)
        mix = session.mix(uri.mix)
        return cls(
            ref=mm.Ref.playlist(uri=str(uri), name=f"{mix.title} ({mix.sub_title})"),
            api=mix,
        )

    @property
    def last_modified(self):
        return to_timestamp(self.api.updated)

    def build(self):
        return mm.Playlist(
            uri=self.uri,
            name=self.name,
            tracks=[t.full for t in self.items()],
            last_modified=self.last_modified,
        )

    def items(self):
        return self.tracks()

    def tracks(self):
        return [
            Track.from_api(item)
            for item in self.api.items()
            if isinstance(item, tdl.Track)
        ]

    @property
    def images(self):
        return None


class Page(Model):
    api_path = None

    @classmethod
    def from_api(cls, page: tdl.Page):
        uri = URI(URIType.PAGE)
        return cls(
            ref=mm.Ref.directory(uri=str(uri), name=page.title),
            api=page,
        )

    @classmethod
    def from_uri(cls, session, uri: str):
        uri = URI.from_string(uri)
        if uri.type != URIType.PAGE:
            raise ValueError("Not a valid uri for Page: %s", uri)
        page = session.page.get(uri.page)
        return cls(
            ref=mm.Ref.directory(uri=str(uri), name=page.title),
            api=page,
            api_path=uri.page
        )

    @property
    def last_modified(self):
        return to_timestamp("today")

    def build(self):
        return self.ref

    def items(self):
        return list(model_factory_map(self.api))

    def tracks(self):
        raise AttributeError

    @property
    def images(self):
        return None


class PageLink:
    def __init__(self, title, api_path):
        self.ref = mm.Ref.directory(uri=str(URI(URIType.PAGE, api_path)), name=title)

    @classmethod
    def from_api(cls, page_link: tdl.page.PageLink):
        return cls(page_link.title, page_link.api_path)


class PageItem(Model):
    URI_REF_MAP = {
        URIType.TRACK: mm.Ref.TRACK,
        URIType.ALBUM: mm.Ref.ALBUM,
        URIType.ARTIST: mm.Ref.ARTIST,
        URIType.PLAYLIST: mm.Ref.PLAYLIST,
        URIType.MIX: mm.Ref.PLAYLIST,
        URIType.PAGE: mm.Ref.DIRECTORY,
    }

    @classmethod
    def from_api(cls, item: tdl.page.PageItem):
        try:
            uri_type = URIType[item.type]
        except KeyError:
            logger.error(f"Future return type unknown: {item.type!s}")
            return None
        try:
            ref_type = cls.URI_REF_MAP[uri_type]
        except KeyError:
            logger.error(f"Future return type not supported: {uri_type!s}")
            return None
        uri = URI(uri_type, item.artifact_id)
        ref = mm.Ref(type=ref_type, uri=str(uri), name=item.header)
        return cls(ref=ref, api=item)

    def build(self):
        return model_factory(self.api.get())


class ItemList(Model):
    @classmethod
    def from_api(cls, items: list):
        return cls(
            ref=mm.Ref.playlist(uri=str(URI(URIType.PLAYLIST)), name=None),
            api=items
        )

    def items(self):
        return list(model_factory_map(self.api))

    def tracks(self):
        return self.items()

    def build(self):
        return mm.Playlist(
            uri=self.uri,
            name=self.name,
            tracks=[t.full for t in self.items()],
            last_modified=to_timestamp("today"),
        )


class Future(Model):
    @classmethod
    @cache_future
    def from_api(cls, future, /, *, ref_type: mm.Ref, title: str):
        uri = URI(URIType.FUTURE, str(hash(future)))
        return cls(
            ref=mm.Ref(type=ref_type, uri=str(uri), name=title),
            api=future,
        )

    @classmethod
    @cached_future
    def from_cache(cls, session: tdl.Session, /, *, uri: str):
        return  # None if cache decorator fails

    @classmethod
    def from_uri(cls, session: tdl.Session, /, *, uri: str):
        future = cls.from_cache(session, uri=uri)
        if future:
            return model_factory(future.api())


def model_factory(api_item):
    try:
        tdl_api = next(k for k in _model_map.keys() if isinstance(api_item, k))
    except StopIteration:
        raise ValueError(f"Not valid value to model: {api_item.__class__.__name__} {api_item!r}")
    else:
        return _model_map[tdl_api](api_item)


def model_factory_map(iterable):
    for i in iterable:
        try:
            model = model_factory(i)
            if model:
                yield model
        except ValueError as e:
            logger.error(e)


_model_map = {
    tdl.Track: Track.from_api,
    tdl.Video: return_none,
    tdl.Album: Album.from_api,
    tdl.Artist: Artist.from_api,
    tdl.Playlist: Playlist.from_api,
    tdl.Mix: Mix.from_api,
    tdl.Page: Page.from_api,
    tdl.page.PageLink: PageLink.from_api,
    tdl.page.PageItem: PageItem.from_api,
    list: ItemList.from_api
}


def lookup_uri(session, uri):
    uri = str(uri)
    model_class = _uri_type_map.get(URI.from_string(uri).type)
    if model_class is None:
        raise ValueError(f"Not valid value as uri: {uri!s}")
    return model_class(session, uri=uri)


_uri_type_map = {
    URIType.TRACK: Track.from_uri,
    URIType.ALBUM: Album.from_uri,
    URIType.ARTIST: Artist.from_uri,
    URIType.PLAYLIST: Playlist.from_uri,
    URIType.MIX: Mix.from_uri,
    URIType.PAGE: Page.from_uri,
    URIType.FUTURE: Future.from_uri,
}
