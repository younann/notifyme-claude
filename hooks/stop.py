#!/usr/bin/env python3
"""Stop hook: spawns delayed notification when Claude is waiting for input."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import load_config
from core.notify import spawn_notification


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
    spawn_notification(session_id, config, input_data)

    print(json.dumps({}))


if __name__ == "__main__":
    main()
