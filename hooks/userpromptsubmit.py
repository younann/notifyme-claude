#!/usr/bin/env python3
"""UserPromptSubmit hook: cancels pending notification when user responds."""
import json
import os
import sys


def main():
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    session_id = input_data.get("session_id", "unknown")
    pending_path = f"/tmp/notifyme-{session_id}.pending"

    try:
        os.remove(pending_path)
    except FileNotFoundError:
        pass

    print(json.dumps({}))


if __name__ == "__main__":
    main()
