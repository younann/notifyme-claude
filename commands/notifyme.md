---
description: Show NotifyMe plugin status and configuration
allowed-tools: ["Bash", "Read"]
---

Read the config file at `~/.claude/notifyme.json`. If it doesn't exist, the defaults are:
- notifications_enabled: true
- delay_seconds: 30
- auto_approve: off
- sound: true

Display the current configuration as:

```
NotifyMe Status
───────────────
Notifications: ON/OFF
Delay:         30s
Auto-approve:  off
Sound:         ON/OFF
```

Use ON/OFF based on boolean values. For auto_approve show the raw value (off/bash/all).
