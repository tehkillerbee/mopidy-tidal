"""Test context, which is used to manage config."""
# TODO: why?

import pytest

from mopidy_tidal import context


def test_context():
    config = {"k": "v"}
    with pytest.raises(ValueError, match="Extension configuration not set."):
        context.get_config()
    context.set_config(config)
    assert context.get_config() == config
