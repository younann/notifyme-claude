---
description: Show NotifyMe plugin status and configuration
allowed-tools: ["Bash", "Read"]
---

Read the config file at `~/.claude/notifyme.json`. If it doesn't exist, the defaults are:
- notifications_enabled: true
- delay_seconds: 30
- renotify_interval: 60
- auto_approve: off
- sound: true
- channels: ["desktop"]

Display the current configuration as:

```
NotifyMe Status
───────────────
Notifications: ON/OFF
Delay:         30s
Renotify:      60s
Auto-approve:  off
Sound:         ON/OFF
Channels:      desktop, slack
Slack:         configured ✓ / not configured
Email:         not configured
```

Use ON/OFF based on boolean values. For auto_approve show the raw value (off/bash/all).

For Channels, show the list from the `channels` array joined by ", ".

For Slack status: show "configured ✓" if the `slack` object has both `bot_token` and `user_id` as non-empty strings. Otherwise show "not configured".

For Email status: show "configured ✓" if the `email` object has `provider` as a non-empty string other than "placeholder". Otherwise show "not configured".

If renotify_interval is 0, show "off" instead of the number.
