"""Tests for hooks/stop.py — the Stop hook."""
import io
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.stop import main


class TestStopHook:
    """Tests for the main stop hook logic."""

    def test_outputs_empty_json_on_invalid_stdin(self, capsys):
        """Should gracefully handle invalid stdin."""
        with patch("sys.stdin", io.StringIO("not json")):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_outputs_empty_json_when_disabled(self, tmp_config, write_config, capsys):
        """Should return {} when notifications are disabled."""
        write_config({"notifications_enabled": False})
        stdin_data = json.dumps({"session_id": "test-123"})
        with patch("sys.stdin", io.StringIO(stdin_data)):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_does_not_spawn_when_disabled(self, tmp_config, write_config, capsys):
        """Should not spawn notification when notifications disabled."""
        write_config({"notifications_enabled": False})
        stdin_data = json.dumps({"session_id": "test-123"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.stop.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_not_called()

    def test_spawns_notification_when_enabled(self, tmp_config, write_config, capsys):
        """Should spawn notification when notifications are enabled."""
        write_config({"notifications_enabled": True, "delay_seconds": 5})
        session_id = "test-spawn"
        stdin_data = json.dumps({"session_id": session_id, "cwd": "/my/project"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.stop.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_called_once()
        args = mock_spawn.call_args[0]
        assert args[0] == session_id  # session_id
        assert args[1]["delay_seconds"] == 5  # config
        assert args[2]["cwd"] == "/my/project"  # input_data

    def test_uses_default_session_id(self, tmp_config, write_config, capsys):
        """Should use 'unknown' when session_id is missing."""
        write_config({"notifications_enabled": True})
        stdin_data = json.dumps({})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.stop.spawn_notification") as mock_spawn:
            main()
        assert mock_spawn.call_args[0][0] == "unknown"

    def test_always_outputs_empty_json(self, tmp_config, write_config, capsys):
        """Should always print {} on success."""
        write_config({"notifications_enabled": True})
        stdin_data = json.dumps({"session_id": "test-output"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.stop.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_passes_full_input_data(self, tmp_config, write_config, capsys):
        """Should pass the full input_data dict to spawn_notification."""
        write_config({"notifications_enabled": True})
        input_data = {"session_id": "test", "cwd": "/path", "extra": "field"}
        with patch("sys.stdin", io.StringIO(json.dumps(input_data))), \
             patch("hooks.stop.spawn_notification") as mock_spawn:
            main()
        passed_input = mock_spawn.call_args[0][2]
        assert passed_input["cwd"] == "/path"
        assert passed_input["extra"] == "field"
