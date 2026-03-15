"""Tests for hooks/hooks.json — hook registration structure."""
import json
import os

import pytest

HOOKS_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "hooks",
    "hooks.json",
)


class TestHooksJson:
    """Tests for the hooks registration file."""

    @pytest.fixture(autouse=True)
    def load_hooks(self):
        with open(HOOKS_JSON_PATH) as f:
            self.hooks = json.load(f)

    def test_is_valid_json(self):
        """hooks.json should be valid JSON."""
        assert isinstance(self.hooks, dict)

    def test_has_required_hook_types(self):
        """Should register Stop, UserPromptSubmit, and PreToolUse hooks."""
        assert "Stop" in self.hooks["hooks"]
        assert "UserPromptSubmit" in self.hooks["hooks"]
        assert "PreToolUse" in self.hooks["hooks"]

    def test_each_hook_has_command(self):
        """Each hook should have a command with python3 and the correct script."""
        expected = {
            "Stop": "stop.py",
            "UserPromptSubmit": "userpromptsubmit.py",
            "PreToolUse": "pretooluse.py",
        }
        for hook_type, script in expected.items():
            entries = self.hooks["hooks"][hook_type]
            assert len(entries) > 0
            hook = entries[0]["hooks"][0]
            assert hook["type"] == "command"
            assert "python3" in hook["command"]
            assert script in hook["command"]

    def test_hooks_use_plugin_root_variable(self):
        """All hooks should use ${CLAUDE_PLUGIN_ROOT} for paths."""
        for hook_type, entries in self.hooks["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    assert "${CLAUDE_PLUGIN_ROOT}" in hook["command"]

    def test_hooks_have_timeout(self):
        """All hooks should have a timeout configured."""
        for hook_type, entries in self.hooks["hooks"].items():
            for entry in entries:
                for hook in entry["hooks"]:
                    assert "timeout" in hook
                    assert hook["timeout"] > 0

    def test_has_description(self):
        """hooks.json should have a description field."""
        assert "description" in self.hooks
        assert len(self.hooks["description"]) > 0
