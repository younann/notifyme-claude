import json
import os
import tempfile

CONFIG_PATH = os.path.expanduser("~/.claude/notifyme.json")

DEFAULTS = {
    "notifications_enabled": True,
    "delay_seconds": 30,
    "renotify_interval": 60,
    "auto_approve": "off",
    "sound": True,
    "channels": ["desktop"],
}


def load_config():
    """Load config from ~/.claude/notifyme.json, returning defaults if missing."""
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        merged = {**DEFAULTS, **data}
        return merged
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save_config(data):
    """Atomically write config to ~/.claude/notifyme.json."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(CONFIG_PATH), suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        os.unlink(tmp_path)
        raise
