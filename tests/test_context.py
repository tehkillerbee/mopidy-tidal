"""Test context, which is used to manage config."""
import pytest

from mopidy_tidal import context


@pytest.fixture(autouse=True)
def config():
    """Override fixture which sets up config: here we want to do it manually."""


def test_get_config_raises_until_set():
    config = {"k": "v"}

    with pytest.raises(ValueError, match="Extension configuration not set."):
        context.get_config()

    context.set_config(config)

    assert context.get_config() == config
