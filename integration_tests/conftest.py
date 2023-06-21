import sys
from contextlib import contextmanager
from pathlib import Path

import pexpect
import pytest


class AssertiveChild:
    def __init__(self, child):
        self.child = child

    def expect(self, msg, timeout=3):
        try:
            self.child.expect(msg, timeout=timeout)
        except pexpect.TIMEOUT as e:
            raise AssertionError(f"Did not recieve '{msg}' within {timeout} S.") from e


@pytest.fixture
def spawn():
    @contextmanager
    def _spawn(*args, **kwargs):
        kwargs["encoding"] = kwargs.get("encoding", "utf8")
        child = pexpect.spawn(*args, **kwargs)
        child.logfile = sys.stdout
        yield AssertiveChild(child)
        assert child.terminate(force=True), "Failed to kill process"

    return _spawn


@pytest.fixture
def config_dir():
    return Path(__file__).parent / "config"


# import pytest

# @pytest.fixture
# def mopidy()
