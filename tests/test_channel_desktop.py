"""Tests for core/channels/desktop.py — desktop notification channel."""
import json
import os
from unittest.mock import patch

import pytest


class TestDesktopSend:
    """Tests for desktop.send() — writes pending file, spawns notifier.sh."""

    def test_creates_pending_file(self):
        from core.channels.desktop import send
        session_id = "test-desktop-send"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        context = {
            "session_id": session_id,
            "app_bundle": "com.test.App",
            "sound": True,
            "delay": 10,
            "renotify_interval": 60,
            "seq": 12345,
        }
        try:
            with patch("subprocess.Popen"):
                send("Test Title", "Test Message", context, {})
            assert os.path.exists(pending_path)
            with open(pending_path) as f:
                data = json.load(f)
            assert data["title"] == "Test Title"
            assert data["message"] == "Test Message"
            assert data["seq"] == 12345
            assert data["sound"] is True
            assert data["renotify_interval"] == 60
            assert data["app"] == "com.test.App"
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_pending_file_has_all_fields(self):
        from core.channels.desktop import send
        session_id = "test-desktop-fields"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        context = {
            "session_id": session_id,
            "app_bundle": "dev.warp.Warp",
            "sound": False,
            "delay": 5,
            "renotify_interval": 0,
            "seq": 99999,
        }
        try:
            with patch("subprocess.Popen"):
                send("T", "M", context, {})
            with open(pending_path) as f:
                data = json.load(f)
            assert set(data.keys()) == {"seq", "sound", "renotify_interval", "app", "title", "message"}
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_spawns_notifier_with_correct_args(self):
        from core.channels.desktop import send
        session_id = "test-desktop-args"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        context = {
            "session_id": session_id,
            "app_bundle": "",
            "sound": True,
            "delay": 42,
            "renotify_interval": 60,
            "seq": 77777,
        }
        try:
            with patch("subprocess.Popen") as mock_popen:
                send("T", "M", context, {})
            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0].endswith("notifier.sh")
            assert cmd[1] == "42"  # delay
            assert cmd[2] == session_id
            assert cmd[3] == "77777"  # seq
            assert mock_popen.call_args[1]["start_new_session"] is True
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_atomic_write(self):
        """No .tmp files should remain after write."""
        from core.channels.desktop import send
        session_id = "test-desktop-atomic"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        context = {
            "session_id": session_id,
            "app_bundle": "",
            "sound": True,
            "delay": 1,
            "renotify_interval": 0,
            "seq": 11111,
        }
        try:
            with patch("subprocess.Popen"):
                send("T", "M", context, {})
            tmp_files = [f for f in os.listdir("/tmp") if f.startswith(f"notifyme-{session_id}") and f.endswith(".tmp")]
            assert tmp_files == []
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)
