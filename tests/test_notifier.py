"""Tests for hooks/notifier.sh — the background notification script."""
import json
import os
import subprocess
import tempfile

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
                json.dump({"seq": 999, "sound": True}, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, "000"],  # seq mismatch
                capture_output=True,
                timeout=5,
            )
            assert result.returncode == 0
            # Pending file should NOT be cleaned up on seq mismatch
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
                json.dump({"seq": seq, "sound": False}, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            # On macOS this should succeed (osascript available)
            # On CI/headless it may fail but should still clean up
            assert not os.path.exists(pending_path), "Pending file should be cleaned up"
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_respects_delay(self):
        """Notifier should sleep for the delay period."""
        import time

        session_id = "test-delay"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 100

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False}, f)

            start = time.time()
            result = subprocess.run(
                [NOTIFIER_PATH, "1", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            elapsed = time.time() - start
            assert elapsed >= 0.9, f"Should sleep at least ~1 second, took {elapsed:.2f}s"
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_cancel_during_delay(self):
        """Removing pending file during delay should prevent notification."""
        import threading
        import time

        session_id = "test-cancel-during-delay"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 200

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False}, f)

            # Start notifier with 2s delay
            proc = subprocess.Popen(
                [NOTIFIER_PATH, "2", session_id, str(seq)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Remove pending file after 0.5s (simulating user response)
            time.sleep(0.5)
            if os.path.exists(pending_path):
                os.remove(pending_path)

            proc.wait(timeout=5)
            assert proc.returncode == 0
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)


class TestNotifierPlatformDetection:
    """Tests for platform detection in notifier.sh."""

    def test_detect_platform_function_exists(self):
        """The script should contain a detect_platform function."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "detect_platform()" in content

    def test_handles_all_platforms(self):
        """Script should handle macos, linux, wsl, and unknown platforms."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        for platform in ["macos", "linux", "wsl"]:
            assert f"notify_{platform}" in content

    def test_parses_app_bundle_from_pending(self):
        """Script should read the app field from pending file."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "FILE_APP" in content
        assert "'app'" in content or '"app"' in content


class TestNotifierClickToActivate:
    """Tests for click-to-activate functionality."""

    def test_macos_prefers_terminal_notifier(self):
        """notify_macos should try terminal-notifier first."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "terminal-notifier" in content
        assert "-activate" in content

    def test_macos_falls_back_to_osascript(self):
        """notify_macos should fall back to osascript + activate."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        assert "osascript" in content
        assert "activate" in content

    def test_notification_passes_app_bundle(self):
        """Notification functions should receive app_bundle parameter."""
        with open(NOTIFIER_PATH) as f:
            content = f.read()
        # Each notify function should accept app_bundle as $2
        assert 'notify_macos "$FILE_SOUND" "$FILE_APP"' in content
        assert 'notify_linux "$FILE_SOUND" "$FILE_APP"' in content
        assert 'notify_wsl "$FILE_SOUND" "$FILE_APP"' in content

    def test_seq_match_with_app_field(self):
        """Should work correctly when pending file includes app field."""
        session_id = "test-app-activate"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        seq = 555

        try:
            with open(pending_path, "w") as f:
                json.dump({"seq": seq, "sound": False, "app": "com.apple.Terminal"}, f)

            result = subprocess.run(
                [NOTIFIER_PATH, "0", session_id, str(seq)],
                capture_output=True,
                timeout=10,
            )
            # Should process and clean up
            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)
