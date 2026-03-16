"""Shared notification logic — detect session context and dispatch to channels."""
import json
import os
import subprocess
import sys
import tempfile
import time

from core.channels import notify_all


def get_seq():
    return int(time.time() * 1000)


def detect_frontmost_app():
    """Detect the bundle ID and display name of the frontmost app.

    Returns (bundle_id, app_name) tuple. Falls back to ("", "") on failure.
    """
    try:
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
    cwd = input_data.get("cwd", "")
    if not cwd:
        cwd = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not cwd:
        cwd = os.environ.get("PWD", "")
    if cwd:
        return os.path.basename(cwd)
    return ""


def build_notification_text(app_name, project):
    """Build title and message strings from session context."""
    if app_name and project:
        title = f"Claude is waiting \u2014 {app_name}"
        message = f"Project: {project}"
    elif app_name:
        title = f"Claude is waiting \u2014 {app_name}"
        message = "Claude Code has finished and is waiting for your input."
    elif project:
        title = "Claude is waiting"
        message = f"Project: {project}"
    else:
        title = "Claude is waiting"
        message = "Claude Code has finished and is waiting for your input."
    return title, message


def spawn_notification(session_id, config, input_data=None):
    """Detect context, build notification text, and dispatch to all channels."""
    if input_data is None:
        input_data = {}

    app_bundle, app_name = detect_frontmost_app()
    project = detect_project_name(input_data)
    title, message = build_notification_text(app_name, project)

    context = {
        "session_id": session_id,
        "app_bundle": app_bundle,
        "sound": config.get("sound", True),
        "delay": config.get("delay_seconds", 30),
        "renotify_interval": config.get("renotify_interval", 60),
        "seq": get_seq(),
    }

    notify_all(title, message, context, config)
