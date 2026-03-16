---
description: Add or remove notification channels (e.g. /notifyme:channel add slack)
argument-hint: <add|remove|list> [channel]
allowed-tools: ["Bash"]
---

The user's argument is: $ARGUMENTS

Run a Python script to manage channels:

```bash
NOTIFYME_ARG="$ARGUMENTS" python3 -c "
import os, sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from core.config import load_config, save_config

arg = os.environ.get('NOTIFYME_ARG', '').strip()
parts = arg.split()

if not parts or parts[0] not in ('add', 'remove', 'list'):
    print('Usage: /notifyme:channel <add|remove|list> [channel]')
    print('Channels: desktop, slack, email')
    sys.exit(0)

cfg = load_config()
channels = cfg.get('channels', ['desktop'])
action = parts[0]

if action == 'list':
    print(f'Active channels: {\", \".join(channels)}')
    sys.exit(0)

if len(parts) < 2:
    print(f'Usage: /notifyme:channel {action} <channel>')
    sys.exit(0)

channel = parts[1].lower()
valid = ('desktop', 'slack', 'email')
if channel not in valid:
    print(f'Error: unknown channel \"{channel}\". Valid: {\", \".join(valid)}')
    sys.exit(0)

if action == 'add':
    if channel in channels:
        print(f'Channel \"{channel}\" is already active.')
    else:
        channels.append(channel)
        cfg['channels'] = channels
        save_config(cfg)
        print(f'Channel \"{channel}\" added. Active: {\", \".join(channels)}')
elif action == 'remove':
    if channel not in channels:
        print(f'Channel \"{channel}\" is not active.')
    else:
        channels.remove(channel)
        cfg['channels'] = channels
        save_config(cfg)
        print(f'Channel \"{channel}\" removed. Active: {\", \".join(channels)}')
"
```

Show the output to the user.
