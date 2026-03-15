"""Tests for hooks/pretooluse.py — the PreToolUse auto-approve hook."""
import io
import json
import os
import sys
from unittest.mock import patch

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
        stdin_data = json.dumps({"tool_name": "Bash"})
        with patch("sys.stdin", io.StringIO(stdin_data)):
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
            with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": tool}))):
                main()
            output = json.loads(capsys.readouterr().out)
            assert output == {}, f"Should block tool: {tool}"

    def test_auto_approve_bash_case_sensitive(self, tmp_config, write_config, capsys):
        """Tool name matching should be case-sensitive ('bash' != 'Bash')."""
        write_config({"auto_approve": "bash"})
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "bash"}))):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}  # lowercase 'bash' should not match

    def test_unknown_auto_approve_value_returns_empty(self, tmp_config, write_config, capsys):
        """Should return {} for unrecognized auto_approve values."""
        write_config({"auto_approve": "invalid"})
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash"}))):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_missing_tool_name_returns_empty(self, tmp_config, write_config, capsys):
        """Should return {} when tool_name is missing from input."""
        write_config({"auto_approve": "bash"})
        with patch("sys.stdin", io.StringIO(json.dumps({}))):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_default_config_returns_empty(self, tmp_config, capsys):
        """With default config (auto_approve=off), should always return {}."""
        with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Bash"}))):
            main()
        output = json.loads(capsys.readouterr().out)
        assert output == {}

    def test_allow_response_structure(self):
        """ALLOW_RESPONSE should have the correct Claude hook format."""
        assert "hookSpecificOutput" in ALLOW_RESPONSE
        assert ALLOW_RESPONSE["hookSpecificOutput"]["permissionDecision"] == "allow"
