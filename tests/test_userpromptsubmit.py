"""Tests for hooks/userpromptsubmit.py — the UserPromptSubmit cancel hook."""
import io
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.userpromptsubmit import main


class TestUserPromptSubmit:
    """Tests for the notification cancellation hook."""

    def test_invalid_stdin_returns_empty(self, capsys):
        """Should return {} on invalid JSON stdin."""
        with patch("sys.stdin", io.StringIO("not json")):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_deletes_pending_file(self, capsys):
        """Should delete the pending file for the session."""
        session_id = "test-delete-pending"
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        # Create a pending file
        with open(pending_path, "w") as f:
            json.dump({"seq": 123, "sound": True}, f)

        try:
            stdin_data = json.dumps({"session_id": session_id})
            with patch("sys.stdin", io.StringIO(stdin_data)):
                main()

            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_handles_missing_pending_file(self, capsys):
        """Should not error when pending file doesn't exist."""
        session_id = "test-no-pending-file"
        pending_path = f"/tmp/notifyme-{session_id}.pending"
        # Ensure file doesn't exist
        if os.path.exists(pending_path):
            os.remove(pending_path)

        stdin_data = json.dumps({"session_id": session_id})
        with patch("sys.stdin", io.StringIO(stdin_data)):
            main()

        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_uses_unknown_for_missing_session_id(self, capsys):
        """Should use 'unknown' session_id when not provided."""
        pending_path = "/tmp/notifyme-unknown.pending"
        with open(pending_path, "w") as f:
            f.write("{}")

        try:
            stdin_data = json.dumps({})
            with patch("sys.stdin", io.StringIO(stdin_data)):
                main()

            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_always_outputs_empty_json(self, capsys):
        """Should always print {} regardless of outcome."""
        stdin_data = json.dumps({"session_id": "test-output"})
        with patch("sys.stdin", io.StringIO(stdin_data)):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}


class TestStopAndCancelIntegration:
    """Integration tests: stop creates pending, userpromptsubmit cancels it."""

    def test_cancel_removes_pending_created_by_stop(self, tmp_config, write_config, capsys):
        """Full flow: stop creates pending file, userpromptsubmit removes it."""
        from hooks.stop import main as stop_main

        write_config({"notifications_enabled": True, "delay_seconds": 999})
        session_id = "test-integration"
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            # Step 1: Stop hook creates pending file
            stdin_data = json.dumps({"session_id": session_id})
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"):
                stop_main()
            capsys.readouterr()  # clear output

            assert os.path.exists(pending_path)

            # Step 2: UserPromptSubmit hook cancels it
            stdin_data = json.dumps({"session_id": session_id})
            with patch("sys.stdin", io.StringIO(stdin_data)):
                main()

            assert not os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)
