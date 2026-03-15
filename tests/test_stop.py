"""Tests for hooks/stop.py — the Stop hook."""
import io
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.stop import main, get_seq, detect_frontmost_app


class TestGetSeq:
    """Tests for sequence number generation."""

    def test_returns_integer(self):
        assert isinstance(get_seq(), int)

    def test_monotonically_increasing(self):
        a = get_seq()
        b = get_seq()
        assert b >= a

    def test_millisecond_precision(self):
        """Seq should be in milliseconds (roughly current epoch * 1000)."""
        import time
        seq = get_seq()
        expected = int(time.time() * 1000)
        assert abs(seq - expected) < 1000  # within 1 second


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
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("subprocess.Popen"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_does_not_spawn_notifier_when_disabled(self, tmp_config, write_config, capsys):
        """Should not spawn notifier.sh when notifications disabled."""
        write_config({"notifications_enabled": False})
        stdin_data = json.dumps({"session_id": "test-123"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("subprocess.Popen") as mock_popen:
            main()
        mock_popen.assert_not_called()

    def test_creates_pending_file(self, tmp_config, write_config, capsys):
        """Should create a pending file in /tmp."""
        write_config({"notifications_enabled": True, "delay_seconds": 5})
        session_id = "test-session-abc"
        stdin_data = json.dumps({"session_id": session_id})
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"):
                main()

            assert os.path.exists(pending_path)
            with open(pending_path) as f:
                data = json.load(f)
            assert "seq" in data
            assert "sound" in data
            assert isinstance(data["seq"], int)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_pending_file_has_sound_from_config(self, tmp_config, write_config, capsys):
        """Pending file should reflect sound setting from config."""
        write_config({"notifications_enabled": True, "sound": False})
        session_id = "test-sound-off"
        stdin_data = json.dumps({"session_id": session_id})
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"):
                main()

            with open(pending_path) as f:
                data = json.load(f)
            assert data["sound"] is False
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_spawns_notifier_with_correct_args(self, tmp_config, write_config, capsys):
        """Should spawn notifier.sh with delay, session_id, and seq."""
        write_config({"notifications_enabled": True, "delay_seconds": 42})
        session_id = "test-spawn"
        stdin_data = json.dumps({"session_id": session_id})
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen") as mock_popen, \
                 patch("hooks.stop.detect_frontmost_app", return_value="com.test.App"):
                main()

            mock_popen.assert_called_once()
            args = mock_popen.call_args
            cmd = args[0][0]

            assert cmd[0].endswith("notifier.sh")
            assert cmd[1] == "42"  # delay
            assert cmd[2] == session_id
            assert cmd[3].isdigit()  # seq

            # Check detached process flags
            assert args[1]["start_new_session"] is True
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_uses_default_session_id_for_missing(self, tmp_config, write_config, capsys):
        """Should use 'unknown' when session_id is missing."""
        write_config({"notifications_enabled": True})
        stdin_data = json.dumps({})
        pending_path = "/tmp/notifyme-unknown.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"):
                main()

            assert os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_always_outputs_empty_json(self, tmp_config, write_config, capsys):
        """Should always print {} on success."""
        write_config({"notifications_enabled": True})
        stdin_data = json.dumps({"session_id": "test-output"})
        pending_path = "/tmp/notifyme-test-output.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"):
                main()
            output = json.loads(capsys.readouterr().out)
            assert output == {}
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_pending_file_includes_app_bundle(self, tmp_config, write_config, capsys):
        """Pending file should include detected app bundle ID."""
        write_config({"notifications_enabled": True})
        session_id = "test-app-bundle"
        stdin_data = json.dumps({"session_id": session_id})
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"), \
                 patch("hooks.stop.detect_frontmost_app", return_value="com.apple.Terminal"):
                main()

            with open(pending_path) as f:
                data = json.load(f)
            assert data["app"] == "com.apple.Terminal"
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_pending_file_app_empty_on_detection_failure(self, tmp_config, write_config, capsys):
        """Pending file should have empty app when detection fails."""
        write_config({"notifications_enabled": True})
        session_id = "test-app-empty"
        stdin_data = json.dumps({"session_id": session_id})
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"), \
                 patch("hooks.stop.detect_frontmost_app", return_value=""):
                main()

            with open(pending_path) as f:
                data = json.load(f)
            assert data["app"] == ""
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)


class TestDetectFrontmostApp:
    """Tests for frontmost app detection."""

    def test_returns_string(self):
        """Should always return a string."""
        result = detect_frontmost_app()
        assert isinstance(result, str)

    def test_returns_bundle_id_on_macos(self):
        """On macOS, should return a bundle ID like com.xxx.yyy."""
        result = detect_frontmost_app()
        if sys.platform == "darwin":
            assert "." in result or result == ""
        else:
            assert result == ""

    def test_handles_osascript_failure(self):
        """Should return empty string when osascript fails."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = detect_frontmost_app()
        assert result == ""

    def test_handles_timeout(self):
        """Should return empty string on timeout."""
        import subprocess as sp
        with patch("subprocess.run", side_effect=sp.TimeoutExpired("osascript", 2)):
            result = detect_frontmost_app()
        assert result == ""
