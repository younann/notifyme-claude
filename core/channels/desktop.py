"""Desktop notification channel — pending file + notifier.sh."""
import json
import os
import subprocess
import tempfile


def send(title, message, context, config):
    """Write pending file and spawn notifier.sh as a background process."""
    session_id = context.get("session_id", "unknown")
    seq = context.get("seq", 0)
    delay = context.get("delay", 30)

    # Write pending file atomically
    pending_path = f"/tmp/notifyme-{session_id}.pending"
    pending_data = json.dumps({
        "seq": seq,
        "sound": context.get("sound", True),
        "renotify_interval": context.get("renotify_interval", 0),
        "app": context.get("app_bundle", ""),
        "title": title,
        "message": message,
    })
    fd, tmp_path = tempfile.mkstemp(dir="/tmp", suffix=".pending.tmp")
    with os.fdopen(fd, "w") as f:
        f.write(pending_data)
    os.replace(tmp_path, pending_path)

    # Go up 3 levels: desktop.py -> channels/ -> core/ -> project root
    hooks_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "hooks",
    )
    notifier_path = os.path.join(hooks_dir, "notifier.sh")

    subprocess.Popen(
        [notifier_path, str(delay), session_id, str(seq)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
