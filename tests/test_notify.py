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


class TestSpawnNotification:
    """Tests for the spawn_notification function."""

    def test_creates_pending_file(self):
        session_id = "test-spawn-shared"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        config = {"delay_seconds": 10, "sound": True}

        try:
            with patch("subprocess.Popen") as mock_popen, \
                 patch("core.notify.detect_frontmost_app", return_value=("com.test.App", "TestApp")):
                spawn_notification(session_id, config, {"cwd": "/my/project"})

            assert os.path.exists(pending_path)
            with open(pending_path) as f:
                data = json.load(f)
            assert "seq" in data
            assert data["sound"] is True
            assert data["app"] == "com.test.App"
            assert data["app_name"] == "TestApp"
            assert data["project"] == "project"
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_pending_file_contains_all_fields(self):
        session_id = "test-all-fields"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        config = {"delay_seconds": 5, "sound": False}

        try:
            with patch("subprocess.Popen"), \
                 patch("core.notify.detect_frontmost_app", return_value=("dev.warp.Warp", "Warp")):
                spawn_notification(session_id, config, {"cwd": "/Users/me/notifyme"})

            with open(pending_path) as f:
                data = json.load(f)
            assert set(data.keys()) == {"seq", "sound", "app", "app_name", "project"}
            assert data["app"] == "dev.warp.Warp"
            assert data["app_name"] == "Warp"
            assert data["project"] == "notifyme"
            assert data["sound"] is False
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_spawns_notifier_with_correct_args(self):
        session_id = "test-notifier-args"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        config = {"delay_seconds": 42, "sound": True}

        try:
            with patch("subprocess.Popen") as mock_popen, \
                 patch("core.notify.detect_frontmost_app", return_value=("", "")):
                spawn_notification(session_id, config)

            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0].endswith("notifier.sh")
            assert cmd[1] == "42"
            assert cmd[2] == session_id
            assert cmd[3].isdigit()
            assert mock_popen.call_args[1]["start_new_session"] is True
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_works_without_input_data(self):
        session_id = "test-no-input"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        config = {"delay_seconds": 1, "sound": True}

        try:
            with patch("subprocess.Popen"), \
                 patch("core.notify.detect_frontmost_app", return_value=("", "")):
                spawn_notification(session_id, config)  # no input_data arg

            assert os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_different_sessions_get_different_files(self):
        config = {"delay_seconds": 1, "sound": True}
        paths = []

        try:
            for sid in ["session-a", "session-b", "session-c"]:
                path = f"/tmp/notifyme-{sid}.pending"
                paths.append(path)
                with patch("subprocess.Popen"), \
                     patch("core.notify.detect_frontmost_app", return_value=("", "")):
                    spawn_notification(sid, config)

            # All three should exist independently
            for path in paths:
                assert os.path.exists(path)
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)
