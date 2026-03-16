"""Slack notification channel — DM via Bot token."""
import json
import sys
import urllib.request
from urllib.error import URLError, HTTPError

SLACK_API = "https://slack.com/api"
TIMEOUT = 5


def send(title, message, context, config):
    """Send a DM to the user via Slack Bot API."""
    slack_config = config.get("slack", {})
    bot_token = slack_config.get("bot_token", "")
    user_id = slack_config.get("user_id", "")

    if not bot_token or not user_id:
        print("notifyme: slack channel not configured (need bot_token and user_id)", file=sys.stderr)
        return

    try:
        channel_id = _open_conversation(bot_token, user_id)
        if not channel_id:
            return
        text = f"*{title}*\n{message}" if message else f"*{title}*"
        _post_message(bot_token, channel_id, text)
    except (URLError, HTTPError, OSError, ValueError) as e:
        print(f"notifyme: slack error: {e}", file=sys.stderr)


def _open_conversation(bot_token, user_id):
    """Call conversations.open to get a DM channel ID."""
    data = json.dumps({"users": user_id}).encode()
    req = urllib.request.Request(
        f"{SLACK_API}/conversations.open",
        data=data,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        print(f"notifyme: slack conversations.open failed: {result.get('error', 'unknown')}", file=sys.stderr)
        return None
    return result.get("channel", {}).get("id")


def _post_message(bot_token, channel_id, text):
    """Call chat.postMessage to send the notification."""
    data = json.dumps({"channel": channel_id, "text": text}).encode()
    req = urllib.request.Request(
        f"{SLACK_API}/chat.postMessage",
        data=data,
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        print(f"notifyme: slack chat.postMessage failed: {result.get('error', 'unknown')}", file=sys.stderr)
