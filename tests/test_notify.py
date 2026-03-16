"""Tests for core/notify.py — shared notification logic."""
import json
import os
import subprocess
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.notify import (
    get_seq,
    detect_frontmost_app,
    detect_project_name,
    build_notification_text,
    spawn_notification,
)


class TestGetSeq:
    """Tests for sequence number generation."""

    def test_returns_integer(self):
        assert isinstance(get_seq(), int)

    def test_monotonically_increasing(self):
        a = get_seq()
        b = get_seq()
        assert b >= a

    def test_millisecond_precision(self):
        import time
        seq = get_seq()
        expected = int(time.time() * 1000)
        assert abs(seq - expected) < 1000


class TestDetectFrontmostApp:
    """Tests for frontmost app detection (returns bundle_id, app_name)."""

    def test_returns_tuple(self):
        result = detect_frontmost_app()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_strings(self):
        bundle_id, app_name = detect_frontmost_app()
        assert isinstance(bundle_id, str)
        assert isinstance(app_name, str)

    def test_returns_bundle_and_name_on_macos(self):
        bundle_id, app_name = detect_frontmost_app()
        if sys.platform == "darwin":
            # Should get something like ("com.apple.Terminal", "Terminal")
            assert "." in bundle_id or bundle_id == ""
            # app_name should be non-empty if bundle_id is
            if bundle_id:
                assert len(app_name) > 0

    def test_handles_osascript_failure(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            bundle_id, app_name = detect_frontmost_app()
        assert bundle_id == ""
        assert app_name == ""

    def test_handles_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 2)):
            bundle_id, app_name = detect_frontmost_app()
        assert bundle_id == ""
        assert app_name == ""

    def test_handles_malformed_output(self):
        mock_result = MagicMock()
        mock_result.stdout = "no-pipe-separator"
        with patch("subprocess.run", return_value=mock_result):
            bundle_id, app_name = detect_frontmost_app()
        assert bundle_id == ""
        assert app_name == ""

    def test_parses_pipe_separated_output(self):
        mock_result = MagicMock()
        mock_result.stdout = "com.apple.Terminal|Terminal\n"
        with patch("subprocess.run", return_value=mock_result):
            bundle_id, app_name = detect_frontmost_app()
        assert bundle_id == "com.apple.Terminal"
        assert app_name == "Terminal"

    def test_handles_app_name_with_spaces(self):
        mock_result = MagicMock()
        mock_result.stdout = "com.microsoft.VSCode|Visual Studio Code\n"
        with patch("subprocess.run", return_value=mock_result):
            bundle_id, app_name = detect_frontmost_app()
        assert bundle_id == "com.microsoft.VSCode"
        assert app_name == "Visual Studio Code"


class TestDetectProjectName:
    """Tests for project name detection."""

    def test_uses_cwd_from_input(self):
        result = detect_project_name({"cwd": "/Users/me/projects/my-api"})
        assert result == "my-api"

    def test_extracts_basename(self):
        result = detect_project_name({"cwd": "/a/b/c/deep-project"})
        assert result == "deep-project"

    def test_falls_back_to_env_claude_project_dir(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/Users/me/code/backend")
        result = detect_project_name({})
        assert result == "backend"

    def test_falls_back_to_env_pwd(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setenv("PWD", "/Users/me/work/frontend")
        result = detect_project_name({})
        assert result == "frontend"

    def test_returns_empty_when_nothing_available(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("PWD", raising=False)
        result = detect_project_name({})
        assert result == ""

    def test_input_cwd_takes_priority_over_env(self, monkeypatch):
        monkeypatch.setenv("PWD", "/env/path")
        result = detect_project_name({"cwd": "/input/path/project-a"})
        assert result == "project-a"


class TestBuildNotificationText:
    """Tests for build_notification_text()."""

    def test_app_and_project(self):
        from core.notify import build_notification_text
        title, msg = build_notification_text("Warp", "my-api")
        assert "Warp" in title
        assert "my-api" in msg

    def test_app_only(self):
        from core.notify import build_notification_text
        title, msg = build_notification_text("Terminal", "")
        assert "Terminal" in title
        assert "waiting for your input" in msg

    def test_project_only(self):
        from core.notify import build_notification_text
        title, msg = build_notification_text("", "backend")
        assert title == "Claude is waiting"
        assert "backend" in msg

    def test_no_context(self):
        from core.notify import build_notification_text
        title, msg = build_notification_text("", "")
        assert title == "Claude is waiting"
        assert "waiting for your input" in msg


class TestSpawnNotification:
    """Tests for the spawn_notification function."""

    def test_calls_notify_all_with_title_and_message(self):
        with patch("core.notify.notify_all") as mock_notify, \
             patch("core.notify.detect_frontmost_app", return_value=("com.test.App", "TestApp")):
            spawn_notification("sess-1", {"delay_seconds": 10, "sound": True}, {"cwd": "/my/project"})

        mock_notify.assert_called_once()
        title, message, context, config = mock_notify.call_args[0]
        assert "TestApp" in title
        assert "project" in message
        assert context["session_id"] == "sess-1"
        assert context["app_bundle"] == "com.test.App"
        assert context["sound"] is True
        assert context["delay"] == 10

    def test_context_contains_all_fields(self):
        with patch("core.notify.notify_all") as mock_notify, \
             patch("core.notify.detect_frontmost_app", return_value=("", "")):
            spawn_notification("sess-2", {"delay_seconds": 5, "sound": False, "renotify_interval": 90})

        context = mock_notify.call_args[0][2]
        assert set(context.keys()) == {"session_id", "app_bundle", "sound", "delay", "renotify_interval", "seq"}
        assert context["session_id"] == "sess-2"
        assert context["sound"] is False
        assert context["delay"] == 5
        assert context["renotify_interval"] == 90

    def test_works_without_input_data(self):
        with patch("core.notify.notify_all") as mock_notify, \
             patch("core.notify.detect_frontmost_app", return_value=("", "")):
            spawn_notification("sess-3", {"delay_seconds": 1, "sound": True})

        mock_notify.assert_called_once()

    def test_different_sessions_produce_different_context(self):
        contexts = []
        with patch("core.notify.notify_all") as mock_notify, \
             patch("core.notify.detect_frontmost_app", return_value=("", "")):
            for sid in ["a", "b", "c"]:
                spawn_notification(sid, {"delay_seconds": 1, "sound": True})
                contexts.append(mock_notify.call_args[0][2])

        session_ids = [c["session_id"] for c in contexts]
        assert session_ids == ["a", "b", "c"]

    def test_multi_channel_dispatch(self):
        """spawn_notification with multiple channels calls all of them."""
        with patch("core.notify.notify_all") as mock_notify, \
             patch("core.notify.detect_frontmost_app", return_value=("com.app.Test", "Test")):
            config = {"delay_seconds": 10, "sound": True, "channels": ["desktop", "slack"]}
            spawn_notification("sess-multi", config, {"cwd": "/my/project"})

        mock_notify.assert_called_once()
        _, _, _, passed_config = mock_notify.call_args[0]
        assert passed_config["channels"] == ["desktop", "slack"]
