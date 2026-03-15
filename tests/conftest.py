"""Shared fixtures for notifyme tests."""
import json
import os
import tempfile

import pytest


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Redirect CONFIG_PATH to a temp file so tests never touch ~/.claude/."""
    config_path = str(tmp_path / "notifyme.json")
    import core.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_PATH", config_path)
    return config_path


@pytest.fixture
def write_config(tmp_config):
    """Helper to write a config dict to the temp config path."""

    def _write(data):
        os.makedirs(os.path.dirname(tmp_config), exist_ok=True)
        with open(tmp_config, "w") as f:
            json.dump(data, f)

    return _write


@pytest.fixture
def tmp_pending(tmp_path):
    """Provide a temp directory for pending files instead of /tmp."""
    return tmp_path


@pytest.fixture
def make_stdin():
    """Create a StringIO that mimics stdin with JSON data."""
    import io

    def _make(data):
        return io.StringIO(json.dumps(data))

    return _make
