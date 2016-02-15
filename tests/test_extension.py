from __future__ import unicode_literals

from mopidy_tidal import Extension


def test_get_default_config():
    ext = Extension()

    config = ext.get_default_config()

    assert '[tidal]' in config
    assert 'enabled = true' in config


def test_get_config_schema():
    ext = Extension()

    schema = ext.get_config_schema()

    # Test the content of your config schema
    assert 'username' in schema
    assert 'password' in schema
    assert 'quality' in schema
