# NotifyMe — Claude Code Plugin

**Never miss when Claude is done.** Get desktop notifications when Claude Code finishes a task or is waiting for tool approval — with session-aware context that tells you exactly which app and project needs attention. No extra installs needed. Your terminal/IDE automatically comes to focus.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-brightgreen.svg)](#platform-support)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-purple.svg)](https://claude.ai)
[![Tests](https://img.shields.io/badge/Tests-85%20passed-success.svg)](#testing)

---

## The Problem

You kick off a long task in Claude Code, switch to another window, and... forget about it. Minutes (or hours) later, you come back to find Claude has been patiently waiting for your input the whole time. Even worse — Claude might be waiting for you to approve a Bash command, and you don't even know it.

**NotifyMe fixes this.** It notifies you when Claude is:
- **Done processing** and waiting for your next message
- **Waiting for tool approval** (e.g., "Allow Bash command?")

Notifications are session-aware — if you have 3 Claude sessions open across Warp and Cursor, you'll know exactly which one needs attention.

---

## Desktop Notification

When Claude finishes and you're away, you'll see a native desktop notification that identifies the session:

<p align="center">
  <img src="assets/notification.png" alt="NotifyMe desktop notification" width="500">
</p>

### Session-Aware Notifications

Running multiple Claude sessions? Each notification tells you exactly where to look:

| Session | Notification Title | Message |
|---|---|---|
| Warp — working on my-api | `Claude is waiting — Warp` | `Project: my-api` |
| Cursor — editing frontend | `Claude is waiting — Cursor` | `Project: frontend` |
| Terminal — running scripts | `Claude is waiting — Terminal` | `Project: scripts` |

Your terminal/IDE **automatically comes to focus** when the notification fires — no clicking required, no extra tools to install.

---

## How It Works

NotifyMe uses three Claude Code hooks that coordinate through the filesystem:

<p align="center">
  <img src="assets/how-it-works.png" alt="How NotifyMe works — flow diagram" width="700">
</p>

### Detailed Flow

1. **Claude finishes its turn** — `Stop` hook fires, detects the frontmost app (name + bundle ID) and project directory, writes a pending file to `/tmp/notifyme-<session>.pending`, and spawns `notifier.sh` in the background
2. **Claude needs tool approval** — `PreToolUse` hook fires when a tool isn't auto-approved, also spawns a notification timer (so you get notified for approval prompts too)
3. **notifier.sh** sleeps for the configured delay (default: 30s)
4. **Meanwhile, if you respond** — `UserPromptSubmit` hook deletes the pending file, cancelling the notification
5. **After delay, notifier.sh wakes up:**
   - Pending file exists? — Send notification with app/project context, bring your app to focus
   - Pending file gone? — You already responded, exit silently
6. **Race condition protection:** Each pending file contains a sequence number. Only the latest notifier can fire — older ones detect the mismatch and exit

### What Triggers Notifications

| Event | Notifies? | Why |
|---|---|---|
| Claude finishes processing | Yes | Stop hook fires |
| Claude waits for tool approval | Yes | PreToolUse hook fires when not auto-approved |
| You're actively typing | No | UserPromptSubmit cancels the timer |
| Auto-approved tool runs | No | No approval needed, no notification |

### Auto-Approve Flow

When a tool is invoked (Bash, Edit, Write, etc.):

1. **PreToolUse hook** fires before the tool executes
2. Reads your `auto_approve` setting
3. If auto-approved → tool runs, no notification
4. If not auto-approved → starts notification timer, defers to normal permission flow

---

## Platform Support

NotifyMe works across all major platforms with native focus-activation — zero extra installs:

<p align="center">
  <img src="assets/platforms.png" alt="Supported platforms — macOS, Linux, WSL" width="600">
</p>

### macOS (Recommended)

Works out of the box. Uses native `osascript` for notifications and `tell application to activate` to bring your terminal/IDE to focus. **No extra installs needed.**

**Notification Center:** Go to System Settings → Notifications → Terminal (or your terminal app) → ensure notifications are allowed.

### Linux

Uses `notify-send` from libnotify for visual notifications and `paplay`/`aplay` for sound. Window focus via `wmctrl` or `xdotool`.

```bash
# Debian/Ubuntu
sudo apt install libnotify-bin

# Fedora
sudo dnf install libnotify

# Arch
sudo pacman -S libnotify
```

### Windows (WSL)

Uses PowerShell's `BurntToast` module for rich notifications, with a balloon tooltip fallback.

```powershell
# Optional — for rich notifications
Install-Module -Name BurntToast -Force
```

---

## Installation

### From GitHub

```bash
# In your Claude Code settings, add this plugin:
# Settings > Plugins > Add from GitHub
# Repository: younann/notifyme-claude
```

### Manual Installation

```bash
git clone https://github.com/younann/notifyme-claude.git ~/.claude/plugins/notifyme
```

Then enable it in Claude Code settings:
```json
{
  "enabledPlugins": {
    "notifyme": true
  }
}
```

---

## Commands

All configuration is done through slash commands inside Claude Code:

<p align="center">
  <img src="assets/commands.png" alt="NotifyMe commands" width="600">
</p>

### `/notifyme` — View Status

Shows your current configuration at a glance.

<p align="center">
  <img src="assets/status.png" alt="NotifyMe status output" width="500">
</p>

### `/notifyme:on` / `/notifyme:off` — Toggle Notifications

```
> /notifyme:on
Notifications enabled.

> /notifyme:off
Notifications disabled.
```

### `/notifyme:delay <seconds>` — Set Delay

Set how long Claude waits before notifying you (1–3600 seconds).

```
> /notifyme:delay 60
Notification delay set to 60s.
```

### `/notifyme:auto-approve <mode>` — Set Auto-Approve

| Mode | What Gets Auto-Approved |
|------|------------------------|
| `off` | Nothing — normal permission flow (default) |
| `bash` | Only Bash/shell commands |
| `all` | Everything — Bash, file edits, writes, etc. |

```
> /notifyme:auto-approve bash
Auto-approve set to bash.

> /notifyme:auto-approve all
⚠️ Auto-approve set to all — use with caution.
```

---

## Configuration

All settings persist across sessions in `~/.claude/notifyme.json`:

```json
{
  "notifications_enabled": true,
  "delay_seconds": 30,
  "auto_approve": "off",
  "sound": true
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `notifications_enabled` | boolean | `true` | Master switch for notifications |
| `delay_seconds` | integer | `30` | Seconds to wait before notifying (1–3600) |
| `auto_approve` | string | `"off"` | Auto-approve mode: `off`, `bash`, or `all` |
| `sound` | boolean | `true` | Play sound with notification |

You can edit this file directly — changes take effect on the next hook invocation (no restart needed).

---

## Examples

### Scenario 1: Long-Running Task

```
You: "Refactor the entire auth module to use JWT tokens"
Claude: [works for 5 minutes...]
Claude: [stops, waiting for input]
         ↓
  [30 seconds pass, you're in another app]
         ↓
  🔔 "Claude is waiting — Warp"  •  "Project: my-api"
  → Warp automatically comes to focus
```

### Scenario 2: Tool Approval While Away

```
You: "Run the migration and deploy"
Claude: [runs migration — auto-approved ✓]
Claude: [wants to run deploy script — needs approval]
         ↓
  [You switched to Slack, 30 seconds pass]
         ↓
  🔔 "Claude is waiting — Cursor"  •  "Project: backend"
  → Cursor comes to focus, you see the approval prompt
```

### Scenario 3: Multiple Sessions

```
Session 1 (Warp):   Working on "my-api"     → 🔔 "Claude is waiting — Warp"    Project: my-api
Session 2 (Warp):   Working on "frontend"   → 🔔 "Claude is waiting — Warp"    Project: frontend
Session 3 (Cursor): Working on "mobile-app" → 🔔 "Claude is waiting — Cursor"  Project: mobile-app
```

### Scenario 4: Active Conversation

```
You: "What does this function do?"
Claude: "This function handles..."
         ↓
  [Timer starts, but you're already typing]
         ↓
You: "Can you add error handling?"
         ↓
  [Timer cancelled — no notification]
```

### Scenario 5: Auto-Approve Bash

```
You: /notifyme:auto-approve bash
     "Run the test suite and fix any failures"
         ↓
Claude: [runs pytest — auto-approved ✓, no notification]
Claude: [edits test file — needs approval → notification timer starts]
Claude: [runs pytest again — auto-approved ✓, no notification]
```

---

## Testing

NotifyMe includes a comprehensive test suite with **85 tests** covering all components:

```bash
python3 -m pytest tests/ -v
```

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_config.py` | 13 | Config load/save, defaults, merge, atomic writes, error handling |
| `test_notify.py` | 22 | App detection (bundle ID + name), project detection, spawn logic |
| `test_stop.py` | 7 | Stop hook delegation, disabled state, input forwarding |
| `test_pretooluse.py` | 16 | Auto-approve modes, notification on approval prompts |
| `test_userpromptsubmit.py` | 6 | Pending file deletion, integration with stop hook |
| `test_notifier.py` | 15 | Shell script, delay, seq matching, session context, platform detection |
| `test_hooks_json.py` | 6 | Hook registration structure validation |

---

## Architecture

```
notifyme/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── hooks/
│   ├── hooks.json               # Hook registrations (Stop, PreToolUse, UserPromptSubmit)
│   ├── stop.py                  # Stop hook — triggers notification on Claude idle
│   ├── pretooluse.py            # PreToolUse hook — auto-approve + notify on approval prompts
│   ├── userpromptsubmit.py      # UserPromptSubmit hook — cancel pending notifications
│   └── notifier.sh              # Background notifier — session-aware, native focus activation
├── core/
│   ├── __init__.py
│   ├── config.py                # Config load/save with atomic writes
│   └── notify.py                # Shared: app detection, project detection, spawn logic
├── commands/
│   ├── notifyme.md              # /notifyme — show status
│   ├── on.md                    # /notifyme:on
│   ├── off.md                   # /notifyme:off
│   ├── delay.md                 # /notifyme:delay <seconds>
│   └── auto-approve.md          # /notifyme:auto-approve <mode>
├── tests/                       # 85 tests covering all components
├── assets/                      # Screenshots
├── README.md
└── LICENSE
```

### Key Design Decisions

- **Session-aware context:** Each notification includes the app name (Warp, Cursor, Terminal, etc.) and project directory — so you know exactly which session needs attention
- **Native focus activation:** Uses `osascript tell application to activate` on macOS — no extra dependencies like `terminal-notifier` required
- **Tool approval notifications:** PreToolUse hook also triggers notifications when auto-approve is off, so you're notified when Claude is waiting for permission, not just when it's done
- **Shared notify module:** `core/notify.py` centralizes app detection, project detection, and notification spawning — used by both `stop.py` and `pretooluse.py`
- **Atomic file operations:** Config and pending files use temp-file-then-rename pattern to prevent corruption
- **Sequence numbers:** Millisecond-precision seq prevents race conditions when multiple notifiers are spawned

---

## Troubleshooting

### Notifications not appearing?

1. **Check if enabled:** Run `/notifyme` to see status
2. **macOS:** System Settings → Notifications → your terminal app → ensure allowed
3. **Linux:** Verify `notify-send` is installed: `which notify-send`
4. **WSL:** Verify `powershell.exe` is accessible from WSL

### Not getting notified for tool approvals?

This was fixed in v1.1. The PreToolUse hook now spawns a notification when it doesn't auto-approve a tool — so you'll get notified when Claude is waiting for Bash/Edit/Write permission too.

### Notification doesn't show my project name?

The project name is detected from the working directory. If it shows empty, your terminal may not be setting `PWD`. You can verify by running `echo $PWD` in your terminal.

### Wrong app gets focused?

NotifyMe detects the frontmost app when the hook fires. If you switch apps very quickly after Claude stops, it may capture the wrong window. The delay gives you time to respond before the app switch happens.

### Auto-approve not working?

1. Run `/notifyme` to check the current mode
2. `bash` mode only approves Bash commands — file edits still require permission

---

## Contributing

Contributions are welcome! Feel free to:

- Report bugs or request features via [Issues](https://github.com/younann/notifyme-claude/issues)
- Submit pull requests for improvements
- Add support for additional notification backends

---

## License

[MIT](LICENSE) — Younan Nwesre
