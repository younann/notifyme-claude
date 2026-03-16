---
description: Configure Slack bot credentials (e.g. /notifyme:slack bot_token xoxb-...)
argument-hint: <bot_token|user_id> <value>
allowed-tools: ["Bash"]
---

The user's argument is: $ARGUMENTS

Run a Python script to set Slack credentials:

```bash
NOTIFYME_ARG="$ARGUMENTS" python3 -c "
import os, sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from core.config import load_config, save_config

arg = os.environ.get('NOTIFYME_ARG', '').strip()
parts = arg.split(None, 1)

if len(parts) < 2 or parts[0] not in ('bot_token', 'user_id'):
    print('Usage: /notifyme:slack <bot_token|user_id> <value>')
    print('  /notifyme:slack bot_token xoxb-...')
    print('  /notifyme:slack user_id U0123ABC456')
    sys.exit(0)

key = parts[0]
value = parts[1].strip()

if not value:
    print(f'Error: {key} cannot be empty.')
    sys.exit(0)

cfg = load_config()
slack = cfg.get('slack', {})
slack[key] = value
cfg['slack'] = slack
save_config(cfg)

# Check if fully configured
has_token = bool(slack.get('bot_token', ''))
has_user = bool(slack.get('user_id', ''))
if has_token and has_user:
    print(f'Slack {key} set. Slack is now fully configured.')
else:
    missing = 'user_id' if has_token else 'bot_token'
    print(f'Slack {key} set. Still need: {missing}')

print('Note: credentials are stored in ~/.claude/notifyme.json in plaintext.')
"
```

Show the output to the user.
