"""Tests for core/config.py — load_config and save_config."""
import json
import os

import pytest

from core.config import DEFAULTS, load_config, save_config


class TestLoadConfig:
    """Tests for load_config()."""

    def test_returns_defaults_when_file_missing(self, tmp_config):
        """Should return default values when config file doesn't exist."""
        config = load_config()
        assert config == DEFAULTS

    def test_returns_defaults_copy_not_reference(self, tmp_config):
        """Returned dict should be a copy, not the DEFAULTS object itself."""
        config = load_config()
        assert config is not DEFAULTS

    def test_loads_existing_config(self, tmp_config, write_config):
        """Should load values from existing config file."""
        write_config({"notifications_enabled": False, "delay_seconds": 60})
        config = load_config()
        assert config["notifications_enabled"] is False
        assert config["delay_seconds"] == 60

    def test_merges_with_defaults(self, tmp_config, write_config):
        """Should fill in missing keys from DEFAULTS."""
        write_config({"delay_seconds": 10})
        config = load_config()
        assert config["delay_seconds"] == 10
        assert config["notifications_enabled"] is True  # from defaults
        assert config["auto_approve"] == "off"  # from defaults
        assert config["sound"] is True  # from defaults

    def test_user_values_override_defaults(self, tmp_config, write_config):
        """User-supplied values should override defaults."""
        write_config({"auto_approve": "all", "sound": False})
        config = load_config()
        assert config["auto_approve"] == "all"
        assert config["sound"] is False

    def test_handles_invalid_json(self, tmp_config):
        """Should return defaults when file contains invalid JSON."""
        with open(tmp_config, "w") as f:
            f.write("{not valid json!!}")
        config = load_config()
        assert config == DEFAULTS

    def test_handles_empty_file(self, tmp_config):
        """Should return defaults when file is empty."""
        with open(tmp_config, "w") as f:
            f.write("")
        config = load_config()
        assert config == DEFAULTS

    def test_extra_keys_preserved(self, tmp_config, write_config):
        """Unknown keys in config file should be preserved."""
        write_config({"custom_key": "custom_value"})
        config = load_config()
        assert config["custom_key"] == "custom_value"


class TestSaveConfig:
    """Tests for save_config()."""

    def test_saves_and_loads_roundtrip(self, tmp_config):
        """Saved config should be loadable and match."""
        data = {"notifications_enabled": False, "delay_seconds": 45, "auto_approve": "bash", "sound": False}
        save_config(data)
        loaded = load_config()
        assert loaded == {**DEFAULTS, **data}

    def test_creates_parent_directory(self, tmp_path, monkeypatch):
        """Should create parent directories if they don't exist."""
        import core.config as cfg

        nested_path = str(tmp_path / "sub" / "dir" / "notifyme.json")
        monkeypatch.setattr(cfg, "CONFIG_PATH", nested_path)
        save_config({"delay_seconds": 5})
        assert os.path.exists(nested_path)

    def test_writes_valid_json(self, tmp_config):
        """Output file should contain valid, indented JSON."""
        save_config({"notifications_enabled": True})
        with open(tmp_config, "r") as f:
            content = f.read()
        assert content.endswith("\n")
        parsed = json.loads(content)
        assert parsed["notifications_enabled"] is True

    def test_atomic_write_no_partial_on_success(self, tmp_config):
        """After save, no .tmp files should remain."""
        save_config({"delay_seconds": 10})
        parent = os.path.dirname(tmp_config)
        tmp_files = [f for f in os.listdir(parent) if f.endswith(".tmp")]
        assert tmp_files == []

    def test_overwrites_existing_config(self, tmp_config, write_config):
        """Saving should overwrite previous config completely."""
        write_config({"delay_seconds": 10, "auto_approve": "all"})
        save_config({"delay_seconds": 60})
        with open(tmp_config, "r") as f:
            data = json.load(f)
        assert data["delay_seconds"] == 60
        assert "auto_approve" not in data  # overwritten, not merged
