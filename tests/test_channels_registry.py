"""Tests for core/channels/__init__.py — channel registry."""
import sys
from unittest.mock import patch, MagicMock

import pytest


class TestGetChannel:
    """Tests for get_channel() — imports channel modules by name."""

    def test_returns_none_for_unknown_channel(self, capsys):
        from core.channels import get_channel
        result = get_channel("carrier_pigeon")
        assert result is None
        assert "unknown channel" in capsys.readouterr().err

    def test_returns_none_on_import_error(self, capsys):
        from core.channels import get_channel
        with patch("importlib.import_module", side_effect=ImportError("boom")):
            result = get_channel("slack")
        assert result is None
        assert "failed to load" in capsys.readouterr().err


class TestNotifyAll:
    """Tests for notify_all() — dispatches to enabled channels."""

    def test_calls_enabled_channels(self):
        from core.channels import notify_all
        mock_desktop = MagicMock()
        mock_slack = MagicMock()

        with patch("core.channels.get_channel") as mock_get:
            mock_get.side_effect = lambda name: {
                "desktop": mock_desktop,
                "slack": mock_slack,
            }.get(name)

            config = {"channels": ["desktop", "slack"]}
            context = {"session_id": "test"}
            notify_all("title", "msg", context, config)

        mock_desktop.send.assert_called_once_with("title", "msg", context, config)
        mock_slack.send.assert_called_once_with("title", "msg", context, config)

    def test_skips_unknown_channels(self):
        from core.channels import notify_all
        mock_desktop = MagicMock()

        with patch("core.channels.get_channel") as mock_get:
            mock_get.side_effect = lambda name: mock_desktop if name == "desktop" else None

            config = {"channels": ["desktop", "nonexistent"]}
            notify_all("t", "m", {}, config)

        mock_desktop.send.assert_called_once()

    def test_failing_channel_does_not_block_others(self, capsys):
        from core.channels import notify_all
        mock_bad = MagicMock()
        mock_bad.send.side_effect = RuntimeError("network error")
        mock_good = MagicMock()

        with patch("core.channels.get_channel") as mock_get:
            mock_get.side_effect = lambda name: {
                "slack": mock_bad,
                "desktop": mock_good,
            }.get(name)

            config = {"channels": ["slack", "desktop"]}
            notify_all("t", "m", {}, config)

        mock_good.send.assert_called_once()
        assert "error" in capsys.readouterr().err

    def test_defaults_to_desktop_only(self):
        from core.channels import notify_all
        mock_desktop = MagicMock()

        with patch("core.channels.get_channel") as mock_get:
            mock_get.return_value = mock_desktop

            notify_all("t", "m", {}, {})  # no channels key

        mock_get.assert_called_once_with("desktop")
