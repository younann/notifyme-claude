---
description: Set auto-approve mode (on/off/bash/all)
argument-hint: <on|off|bash|all>
allowed-tools: ["Bash"]
---

The user's argument is: $ARGUMENTS

Run a Python script to validate and save the auto-approve mode:

```bash
NOTIFYME_ARG="$ARGUMENTS" python3 -c "
import os, sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from core.config import load_config, save_config

arg = os.environ.get('NOTIFYME_ARG', '').strip().lower()
if not arg:
    print('Usage: /notifyme:auto-approve <on|off|bash|all>')
    sys.exit(0)

# Normalize 'on' to 'all'
if arg == 'on':
    arg = 'all'

valid = ('off', 'bash', 'all')
if arg not in valid:
    print(f'Error: invalid mode \"{arg}\". Use: on, off, bash, all')
    sys.exit(0)

if arg == 'all':
    print('Warning: This will auto-approve all tool uses including file edits and deletes. Use with caution.')

cfg = load_config()
cfg['auto_approve'] = arg
save_config(cfg)
print(f'Auto-approve set to {arg}.')
"
```

Show the output to the user.
