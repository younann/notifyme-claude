#!/usr/bin/env python3
"""PreToolUse hook: auto-approve tool permissions and notify on approval prompts."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_config
from core.notify import spawn_notification

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
    tool_name = input_data.get("tool_name", "")

    # Check if this tool will be auto-approved
    will_auto_approve = False
    if auto_approve == "all":
        will_auto_approve = True
    elif auto_approve == "bash" and tool_name == "Bash":
        will_auto_approve = True

    # If NOT auto-approving, user will be prompted — spawn notification
    if not will_auto_approve and config.get("notifications_enabled", True):
        session_id = input_data.get("session_id", "unknown")
        spawn_notification(session_id, config, input_data)

    # Return the appropriate response
    if will_auto_approve:
        print(json.dumps(ALLOW_RESPONSE))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
