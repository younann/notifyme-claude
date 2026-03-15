---
description: Enable desktop notifications
allowed-tools: ["Bash"]
---

Run a Python one-liner to enable notifications:

```bash
python3 -c "
import sys; sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from core.config import load_config, save_config
cfg = load_config()
cfg['notifications_enabled'] = True
save_config(cfg)
print('Notifications enabled.')
"
```

Show the output to the user.
