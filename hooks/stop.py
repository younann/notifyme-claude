#!/usr/bin/env python3
"""Stop hook: spawns delayed notification when Claude is waiting for input."""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_config


def get_seq():
    return int(time.time() * 1000)


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    config = load_config()

    if not config.get("notifications_enabled", True):
        print(json.dumps({}))
        return

    session_id = input_data.get("session_id", "unknown")
    delay = config.get("delay_seconds", 30)
    sound = config.get("sound", True)
    seq = get_seq()

    # Write pending file atomically
    pending_path = f"/tmp/notifyme-{session_id}.pending"
    pending_data = json.dumps({"seq": seq, "sound": sound})
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

    print(json.dumps({}))


if __name__ == "__main__":
    main()
