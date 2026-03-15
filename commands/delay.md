---
description: Set notification delay in seconds (e.g. /notifyme:delay 60)
argument-hint: <seconds>
allowed-tools: ["Bash"]
---

The user's argument is: $ARGUMENTS

Run a Python script to validate and save the delay:

```bash
NOTIFYME_ARG="$ARGUMENTS" python3 -c "
import os, sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from core.config import load_config, save_config

arg = os.environ.get('NOTIFYME_ARG', '').strip()
if not arg:
    print('Usage: /notifyme:delay <seconds>')
    sys.exit(0)

try:
    seconds = int(arg)
except ValueError:
    print(f'Error: \"{arg}\" is not a valid integer.')
    sys.exit(0)

if seconds < 1 or seconds > 3600:
    print('Error: delay must be between 1 and 3600 seconds.')
    sys.exit(0)

cfg = load_config()
cfg['delay_seconds'] = seconds
save_config(cfg)
print(f'Notification delay set to {seconds}s.')
"
```

Show the output to the user.
