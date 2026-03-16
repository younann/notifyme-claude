"""Channel registry — dispatches notifications to enabled channels."""
import importlib
import sys

CHANNEL_MAP = {
    "desktop": "core.channels.desktop",
    "slack": "core.channels.slack",
    "email": "core.channels.email",
}


def get_channel(name):
    """Import and return a channel module. Returns None on failure."""
    module_path = CHANNEL_MAP.get(name)
    if not module_path:
        print(f"notifyme: unknown channel '{name}'", file=sys.stderr)
        return None
    try:
        return importlib.import_module(module_path)
    except Exception as e:
        print(f"notifyme: failed to load channel '{name}': {e}", file=sys.stderr)
        return None


def notify_all(title, message, context, config):
    """Send notification to all enabled channels."""
    for channel_name in config.get("channels", ["desktop"]):
        module = get_channel(channel_name)
        if module:
            try:
                module.send(title, message, context, config)
            except Exception as e:
                print(f"notifyme: channel '{channel_name}' error: {e}", file=sys.stderr)
