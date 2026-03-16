"""Tests for hooks/notifier.sh — the background notification script."""
import json
import os
import subprocess
import time

import pytest

NOTIFIER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hooks",
    "notifier.sh",
)


class TestNotifierScript:
    """Tests for the bash notifier script."""

    def test_script_is_executable(self):
        """notifier.sh should have execute permission."""
        assert os.access(NOTIFIER_PATH, os.X_OK)

    def test_exits_when_pending_file_missing(self):
        """Should exit cleanly when no pending file exists."""
        result = subprocess.run(
            [NOTIFIER_PATH, "0", "nonexistent-session-xyz", "12345"],
            capture_output=True,
            timeout=5,
        )
        assert result.returncode == 0

    def test_exits_on_seq_mismatch(self):
        """Should exit when pending file seq doesn't match argument."""
        session_id = "test-seq-mismatch"
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": 999, "sound": True, "renotify_interval": 0, "app": "", "title": "Claude is waiting", "message": ""}, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, "000"],
                capture_output=True,
                timeout=5,
            )
            assert result.returncode == 0
            assert os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_sends_notification_on_seq_match(self):
        """Should attempt notification and clean up when seq matches."""
        session_id = "test-seq-match"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 42

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False, "renotify_interval": 0, "app": "", "title": "Claude is waiting", "message": ""}, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_respects_delay(self):
        """Notifier should sleep for the delay period."""
        session_id = "test-delay"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 100

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False, "renotify_interval": 0, "app": "", "title": "Claude is waiting", "message": ""}, f)

            start = time.time()
            subprocess.run(
                [NOTIFIER_PATH, "1", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            elapsed = time.time() - start
            assert elapsed >= 0.9
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_cancel_during_delay(self):
        """Removing pending file during delay should prevent notification."""
        session_id = "test-cancel-during-delay"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 200

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False, "renotify_interval": 0, "app": "", "title": "Claude is waiting", "message": ""}, f)

            proc = subprocess.Popen(
                [NOTIFIER_PATH, "2", session_id, str(seq)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            time.sleep(0.5)
            if os.path.exists(pending_path):
                os.remove(pending_path)

            proc.wait(timeout=5)
            assert proc.returncode == 0
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)


class TestNotifierSessionContext:
    """Tests for session-aware notifications (app name, project)."""

    def test_parses_all_fields_from_pending(self):
        """Script should parse title, message, and app from pending file."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "NOTIF_TITLE" in content
        assert "NOTIF_MESSAGE" in content
        assert "FILE_APP" in content

    def test_notification_includes_title(self):
        """Notification should use title from pending file."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "NOTIF_TITLE" in content

    def test_notification_includes_message(self):
        """Notification should use message from pending file."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "NOTIF_MESSAGE" in content

    def test_with_app_and_project(self):
        """Should show app name in title and project in message."""
        session_id = "test-context-full"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 300

        try:
            with open(pending_path, "w") as f:
                json.dump({
                    "seq": seq, "sound": False, "renotify_interval": 0,
                    "app": "dev.warp.Warp-Stable", "title": "Claude is waiting — Warp",
                    "message": "Project: my-api"
                }, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_with_only_app_name(self):
        """Should work with app name but no project."""
        session_id = "test-context-app-only"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 301

        try:
            with open(pending_path, "w") as f:
                json.dump({
                    "seq": seq, "sound": False, "renotify_interval": 0,
                    "app": "com.apple.Terminal", "title": "Claude is waiting — Terminal",
                    "message": "Claude Code has finished and is waiting for your input."
                }, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_with_no_context(self):
        """Should still send notification with no app/project info."""
        session_id = "test-context-none"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 302

        try:
            with open(pending_path, "w") as f:
                json.dump({
                    "seq": seq, "sound": False, "renotify_interval": 0,
                    "app": "", "title": "Claude is waiting",
                    "message": "Claude Code has finished and is waiting for your input."
                }, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)


class TestNotifierPlatformDetection:
    """Tests for platform detection in notifier.sh."""

    def test_detect_platform_function_exists(self):
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "detect_platform()" in content

    def test_handles_all_platforms(self):
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        for platform in ["macos", "linux", "wsl"]:
            assert f"notify_{platform}" in content

    def test_native_activation_no_terminal_notifier(self):
        """Should use osascript activate natively, not require terminal-notifier."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        # Should NOT prefer terminal-notifier anymore
        assert "terminal-notifier" in content
        # Should use native osascript activate
        assert "activate" in content
        assert "osascript" in content
