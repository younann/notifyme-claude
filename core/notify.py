"""Shared notification logic — detect session context and spawn notifier."""
import json
import os
import subprocess
import sys
import tempfile
import time


def get_seq():
    return int(time.time() * 1000)


def detect_frontmost_app():
    """Detect the bundle ID and display name of the frontmost app.

    Returns (bundle_id, app_name) tuple. Falls back to ("", "") on failure.
    """
    try:
        # Get both bundle ID and display name in one osascript call
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events"\n'
                '  set frontProc to first process whose frontmost is true\n'
                '  set appName to name of frontProc\n'
                '  set bundleId to bundle identifier of frontProc\n'
                '  return bundleId & "|" & appName\n'
                'end tell',
            ],
            capture_output=True, text=True, timeout=2,
        )
        parts = result.stdout.strip().split("|", 1)
        if len(parts) == 2 and parts[0]:
            return parts[0], parts[1]
    except Exception:
        pass
    return "", ""


def detect_project_name(input_data):
    """Detect the project/directory name for the current Claude session.

    Tries multiple sources: hook input cwd, environment variables, fallback.
    """
    # Try cwd from hook input data
    cwd = input_data.get("cwd", "")

    # Try environment variables that Claude Code might set
    if not cwd:
        cwd = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not cwd:
        cwd = os.environ.get("PWD", "")

    if cwd:
        return os.path.basename(cwd)
    return ""


def spawn_notification(session_id, config, input_data=None):
    """Write pending file and spawn background notifier.

    The pending file contains session context (app, project) so the
    notification can identify which Claude session is waiting.
    """
    if input_data is None:
        input_data = {}

    delay = config.get("delay_seconds", 30)
    sound = config.get("sound", True)
    seq = get_seq()
    app_bundle, app_name = detect_frontmost_app()
    project = detect_project_name(input_data)

    # Write pending file atomically
    pending_path = f"/tmp/notifyme-{session_id}.pending"
    pending_data = json.dumps({
        "seq": seq,
        "sound": sound,
        "app": app_bundle,
        "app_name": app_name,
        "project": project,
    })
    fd, tmp_path = tempfile.mkstemp(dir="/tmp", suffix=".pending.tmp")
    with os.fdopen(fd, "w") as f:
        f.write(pending_data)
    os.replace(tmp_path, pending_path)

    # Spawn notifier.sh as detached background process
    hooks_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks"
    )
    notifier_path = os.path.join(hooks_dir, "notifier.sh")

    subprocess.Popen(
        [notifier_path, str(delay), session_id, str(seq)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
