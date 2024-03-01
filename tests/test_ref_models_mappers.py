from mopidy_tidal import ref_models_mappers as rmm


def test_root_contains_entries_for_eachfield():
    root = rmm.create_root()

    uri_map = {
        "tidal:genres": "Genres",
        "tidal:moods": "Moods",
        "tidal:mixes": "My Mixes",
        "tidal:my_artists": "My Artists",
        "tidal:my_albums": "My Albums",
        "tidal:my_playlists": "My Playlists",
        "tidal:my_tracks": "My Tracks",
    }
    for uri, name in uri_map.items():
        ref = next(x for x in root if x.uri == uri)
        assert ref.name == name
