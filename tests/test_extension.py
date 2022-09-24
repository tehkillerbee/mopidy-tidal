from __future__ import unicode_literals

import pytest

from mopidy_tidal import Extension
from mopidy_tidal.backend import TidalBackend


def test_get_default_config():
    ext = Extension()

    config = ext.get_default_config()

    assert "[tidal]" in config
    assert "enabled = true" in config


def test_get_config_schema():
    ext = Extension()

    schema = ext.get_config_schema()

    # Test the content of your config schema
    assert "quality" in schema
    assert "client_id" in schema
    assert "client_secret"


@pytest.mark.gt_3_7
def test_setup(mocker):
    ext = Extension()
    registry = mocker.Mock()
    ext.setup(registry)
    registry.add.assert_called_once()
    args = registry.add.mock_calls[0].args
    assert args[0] == "backend"
    assert type(args[1]) is type(TidalBackend)
