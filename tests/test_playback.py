from mopidy_tidal.playback import TidalPlaybackProvider


def test_playback_new_api(mocker):
    uniq = object()
    session = mocker.Mock(spec=["track"])
    session.mock_add_spec(["track"])
    track = mocker.Mock()
    track.get_url.return_value = uniq
    session.track.return_value = track
    backend = mocker.Mock(_session=session)
    audio = mocker.Mock()
    tpp = TidalPlaybackProvider(audio, backend)
    assert tpp.translate_uri("tidal:track:1:2:3") is uniq
    session.track.assert_called_once_with(3)
    track.get_url.assert_called_once()
