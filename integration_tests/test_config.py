from contextlib import contextmanager
from pathlib import Path

import pexpect
import pytest


class AssertiveChild:
    def __init__(self, child):
        self.child = child

    def expect(self, msg, timeout=1):
        try:
            self.child.expect(msg, timeout=timeout)
        except pexpect.TIMEOUT as e:
            raise AssertionError(f"Did not recieve '{msg}' within {timeout} S.") from e


@contextmanager
def spawn(*args, **kwargs):
    child = pexpect.spawn(*args, **kwargs)
    yield AssertiveChild(child)
    assert child.terminate(force=True), "Failed to kill process"


config_dir = Path(__file__).parent / "config"


def test_basic_config_loads_tidal_extension():
    config = config_dir / "basic.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        child.expect("Visit link.tidal.com/.* to log in")


def test_lazy_config_no_connect_to_tidal():
    config = config_dir / "lazy.conf"
    with spawn(f"mopidy --config {config.resolve()}") as child:
        child.expect("Connecting to TIDAL... Quality = LOSSLESS")
        with pytest.raises(AssertionError):
            child.expect("Visit link.tidal.com/.* to log in")