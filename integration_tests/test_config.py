import pytest


def test_basic_config_loads_tidal_generates_auth_url(spawn, config_dir):
    config = config_dir / "basic.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        child.expect("Visit https://link.tidal.com/.* to log in")


def test_lazy_config_no_connect_to_tidal(spawn, config_dir):
    config = config_dir / "lazy.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        with pytest.raises(AssertionError):
            child.expect("Visit https://link.tidal.com/.* to log in")


def test_lazy_config_generates_auth_url_on_access(spawn, config_dir):
    config = config_dir / "lazy.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        with pytest.raises(AssertionError):
            child.expect("Visit https://link.tidal.com/.* to log in")
        with spawn("mpc list artist"):
            child.expect("Visit https://link.tidal.com/.* to log in")
