"""Tests for hooks/pretooluse.py — the PreToolUse auto-approve hook."""
import io
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from hooks.pretooluse import main, ALLOW_RESPONSE


class TestPreToolUse:
    """Tests for the auto-approve hook."""

    def test_invalid_stdin_returns_empty(self, capsys):
        """Should return {} on invalid JSON stdin."""
        with patch("sys.stdin", io.StringIO("bad json")):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_auto_approve_off_returns_empty(self, tmp_config, write_config, capsys):
        """Should return {} when auto_approve is off."""
        write_config({"auto_approve": "off"})
        stdin_data = json.dumps({"tool_name": "Bash", "session_id": "test"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_auto_approve_all_allows_any_tool(self, tmp_config, write_config, capsys):
        """Should allow any tool when auto_approve is 'all'."""
        write_config({"auto_approve": "all"})
        for tool in ["Bash", "Write", "Edit", "Read", "Glob"]:
            with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": tool}))):
                main()
            output = json.loads(capsys.readouterr().out)
            assert output == ALLOW_RESPONSE, f"Failed for tool: {tool}"

    def test_auto_approve_bash_allows_bash(self, tmp_config, write_config, capsys):
        """Should allow Bash tool when auto_approve is 'bash'."""
        write_config({"auto_approve": "bash"})
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash"}))):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == ALLOW_RESPONSE

    def test_auto_approve_bash_blocks_non_bash(self, tmp_config, write_config, capsys):
        """Should return {} for non-Bash tools when auto_approve is 'bash'."""
        write_config({"auto_approve": "bash"})
        for tool in ["Write", "Edit", "Read", "Glob", "Agent"]:
            with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": tool, "session_id": "test"}))), \
                 patch("hooks.pretooluse.spawn_notification"):
                main()
            output = json.loads(capsys.readouterr().out)
            assert output == {}, f"Should block tool: {tool}"

    def test_auto_approve_bash_case_sensitive(self, tmp_config, write_config, capsys):
        """Tool name matching should be case-sensitive ('bash' != 'Bash')."""
        write_config({"auto_approve": "bash"})
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "bash", "session_id": "test"}))), \
             patch("hooks.pretooluse.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}  # lowercase 'bash' should not match

    def test_unknown_auto_approve_value_returns_empty(self, tmp_config, write_config, capsys):
        """Should return {} for unrecognized auto_approve values."""
        write_config({"auto_approve": "invalid"})
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash", "session_id": "test"}))), \
             patch("hooks.pretooluse.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_missing_tool_name_returns_empty(self, tmp_config, write_config, capsys):
        """Should return {} when tool_name is missing from input."""
        write_config({"auto_approve": "bash"})
        with patch("sys.stdin", io.StringIO(json.dumps({"session_id": "test"}))), \
             patch("hooks.pretooluse.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_default_config_returns_empty(self, tmp_config, capsys):
        """With default config (auto_approve=off), should always return {}."""
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash", "session_id": "test"}))), \
             patch("hooks.pretooluse.spawn_notification"):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_allow_response_structure(self):
        """ALLOW_RESPONSE should have the correct Claude hook format."""
        assert "hookSpecificOutput" in ALLOW_RESPONSE
        assert ALLOW_RESPONSE["hookSpecificOutput"]["permissionDecision"] == "allow"


class TestPreToolUseNotification:
    """Tests for notification spawning when tool approval is needed."""

    def test_spawns_notification_when_not_auto_approving(self, tmp_config, write_config, capsys):
        """Should spawn notification when user will be prompted for approval."""
        write_config({"auto_approve": "off", "notifications_enabled": True})
        stdin_data = json.dumps({"tool_name": "Bash", "session_id": "test-notify"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_called_once_with("test-notify", mock_spawn.call_args[0][1])

    def test_no_notification_when_auto_approving_all(self, tmp_config, write_config, capsys):
        """Should NOT spawn notification when auto-approving."""
        write_config({"auto_approve": "all", "notifications_enabled": True})
        stdin_data = json.dumps({"tool_name": "Bash", "session_id": "test"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_not_called()

    def test_no_notification_when_auto_approving_bash(self, tmp_config, write_config, capsys):
        """Should NOT spawn notification when Bash is auto-approved."""
        write_config({"auto_approve": "bash", "notifications_enabled": True})
        stdin_data = json.dumps({"tool_name": "Bash", "session_id": "test"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_not_called()

    def test_notification_for_non_bash_in_bash_mode(self, tmp_config, write_config, capsys):
        """Should spawn notification for non-Bash tools in bash auto-approve mode."""
        write_config({"auto_approve": "bash", "notifications_enabled": True})
        stdin_data = json.dumps({"tool_name": "Write", "session_id": "test-write"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_called_once()

    def test_no_notification_when_notifications_disabled(self, tmp_config, write_config, capsys):
        """Should NOT spawn notification when notifications are disabled."""
        write_config({"auto_approve": "off", "notifications_enabled": False})
        stdin_data = json.dumps({"tool_name": "Bash", "session_id": "test"})
        with patch("sys.stdin", io.StringIO(stdin_data)), \
             patch("hooks.pretooluse.spawn_notification") as mock_spawn:
            main()
        mock_spawn.assert_not_called()

    def test_spawn_notification_creates_pending_file(self, tmp_config, write_config, capsys):
        """spawn_notification should create a pending file and spawn notifier."""
        from hooks.pretooluse import spawn_notification

        write_config({"delay_seconds": 10, "sound": True})
        config = {"delay_seconds": 10, "sound": True}
        session_id = "test-spawn-pretool"
        pending_path = f"/tmp/notifyme-{session_id}.pending"

        try:
            with patch("subprocess.Popen") as mock_popen, \
                 patch("hooks.pretooluse.detect_frontmost_app", return_value="com.test.IDE"):
                spawn_notification(session_id, config)

            assert os.path.exists(pending_path)
            with open(pending_path) as f:
                data = json.load(f)
            assert "seq" in data
            assert data["sound"] is True
            assert data["app"] == "com.test.IDE"

            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert cmd[0].endswith("notifier.sh")
            assert cmd[1] == "10"
            assert cmd[2] == session_id
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)

    def test_uses_default_session_id(self, tmp_config, write_config, capsys):
        """Should use 'unknown' when session_id is missing."""
        write_config({"auto_approve": "off", "notifications_enabled": True})
        stdin_data = json.dumps({"tool_name": "Bash"})
        pending_path = "/tmp/notifyme-unknown.pending"

        try:
            with patch("sys.stdin", io.StringIO(stdin_data)), \
                 patch("subprocess.Popen"), \
                 patch("hooks.pretooluse.detect_frontmost_app", return_value=""):
                main()

            assert os.path.exists(pending_path)
        finally:
            if os.path.exists(pending_path):
                os.remove(pending_path)
