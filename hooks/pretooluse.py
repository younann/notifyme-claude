#!/usr/bin/env python3
"""PreToolUse hook: auto-approve tool permissions based on config."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_config

ALLOW_RESPONSE = {
    "hookSpecificOutput": {"permissionDecision": "allow"}
}


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    config = load_config()
    auto_approve = config.get("auto_approve", "off")

    if auto_approve == "off":
        print(json.dumps({}))
        return

    tool_name = input_data.get("tool_name", "")

    if auto_approve == "all":
        print(json.dumps(ALLOW_RESPONSE))
        return

    if auto_approve == "bash" and tool_name == "Bash":
        print(json.dumps(ALLOW_RESPONSE))
        return

    print(json.dumps({}))


if __name__ == "__main__":
    main()
