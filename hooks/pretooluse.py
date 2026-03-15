#!/usr/bin/env python3
"""PreToolUse hook: auto-approve tool permissions and notify on approval prompts."""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_config

ALLOW_RESPONSE = {
    "hookSpecificOutput": {"permissionDecision": "allow"}
}


def get_seq():
    return int(time.time() * 1000)


def detect_frontmost_app():
    """Detect the bundle ID of the frontmost app (the terminal/IDE running Claude)."""
    try:
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to get bundle identifier '
                'of first process whose frontmost is true',
            ],
            capture_output=True, text=True, timeout=2,
        )
        bundle_id = result.stdout.strip()
        if bundle_id:
            return bundle_id
    except Exception:
        pass
    return ""


def spawn_notification(session_id, config):
    """Spawn a delayed notification for when user needs to approve a tool."""
    delay = config.get("delay_seconds", 30)
    sound = config.get("sound", True)
    seq = get_seq()
    app_bundle = detect_frontmost_app()

    # Write pending file atomically
    pending_path = f"/tmp/notifyme-{session_id}.pending"
    pending_data = json.dumps({"seq": seq, "sound": sound, "app": app_bundle})
    fd, tmp_path = tempfile.mkstemp(dir="/tmp", suffix=".pending.tmp")
    with os.fdopen(fd, "w") as f:
        f.write(pending_data)
    os.replace(tmp_path, pending_path)

    # Spawn notifier.sh as detached background process
    hooks_dir = os.path.dirname(os.path.abspath(__file__))
    notifier_path = os.path.join(hooks_dir, "notifier.sh")

    subprocess.Popen(
        [notifier_path, str(delay), session_id, str(seq)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


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
        spawn_notification(session_id, config)

    # Return the appropriate response
    if will_auto_approve:
        print(json.dumps(ALLOW_RESPONSE))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
