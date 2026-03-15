# 🔔 NotifyMe — Claude Code Plugin

**Never miss when Claude is done.** Get desktop notifications when Claude Code finishes a task and is waiting for your input — plus configurable auto-approve to skip permission prompts.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-brightgreen.svg)](#platform-support)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-purple.svg)](https://claude.ai)

---

## The Problem

You kick off a long task in Claude Code, switch to another window, and... forget about it. Minutes (or hours) later, you come back to find Claude has been patiently waiting for your input the whole time.

**NotifyMe fixes this.** It watches for when Claude stops and waits, then pings you with a desktop notification after a configurable delay — so you only get notified when you're actually away, not during active back-and-forth.

---

## Features

### Smart Delayed Notifications

NotifyMe doesn't spam you. It uses a **smart delay system** — you only get notified if you haven't responded within a configurable time window (default: 30 seconds).

```
┌─────────────────────────────────────────────────────────────┐
│                    How Notifications Work                     │
│                                                               │
│  Claude stops ──► Timer starts (30s) ──► Still waiting? ──► 🔔│
│                         │                                     │
│                    You respond?                               │
│                         │                                     │
│                    Timer cancelled ──► No notification         │
└─────────────────────────────────────────────────────────────┘
```

### Auto-Approve Tool Permissions

Tired of approving every Bash command? NotifyMe lets you auto-approve tool permissions at different levels:

| Mode | What Gets Auto-Approved |
|------|------------------------|
| `off` | Nothing — normal permission flow (default) |
| `bash` | Only Bash/shell commands |
| `all` | Everything — Bash, file edits, writes, etc. |

### Cross-Platform Desktop Notifications

| Platform | Method | Sound |
|----------|--------|-------|
| **macOS** | Native osascript (built-in, zero deps) | 🔊 Glass |
| **Linux** | notify-send (libnotify) | 🔊 paplay/aplay |
| **Windows WSL** | BurntToast / balloon fallback | 🔊 System default |

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

### `/notifyme` — View Status

Shows your current configuration at a glance.

```
NotifyMe Status
───────────────
Notifications: ON
Delay:         30s
Auto-approve:  off
Sound:         ON
```

### `/notifyme:on` — Enable Notifications

```
> /notifyme:on
Notifications enabled.
```

### `/notifyme:off` — Disable Notifications

```
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

```
> /notifyme:auto-approve bash
Auto-approve set to bash.

> /notifyme:auto-approve all
⚠️ Warning: This will auto-approve all tool uses including file edits and deletes. Use with caution.
Auto-approve set to all.

> /notifyme:auto-approve off
Auto-approve set to off.
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

You can edit this file directly or use the slash commands above.

---

## How It Works

NotifyMe uses three Claude Code hooks that work together:

```
                          Claude Code Session
                          ═══════════════════

  ┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
  │   Stop Hook  │     │ UserPromptSubmit  │     │  PreToolUse Hook │
  │              │     │      Hook          │     │                  │
  │ Claude done  │     │ User responds     │     │ Tool permission  │
  │ → start      │     │ → cancel timer    │     │ → auto-approve   │
  │   timer      │     │                    │     │   if configured  │
  └──────┬───────┘     └────────┬───────────┘     └──────────────────┘
         │                      │
         ▼                      ▼
  ┌──────────────┐     ┌───────────────────┐
  │ notifier.sh  │     │  Delete pending   │
  │              │     │  file → cancel    │
  │ sleep(delay) │     └───────────────────┘
  │ check file   │
  │ send notif   │
  └──────────────┘
```

### Detailed Flow

1. **Claude finishes its turn** → `Stop` hook fires
2. **Stop hook** writes a pending file to `/tmp/notifyme-<session>.pending` and spawns `notifier.sh` in the background
3. **notifier.sh** sleeps for the configured delay
4. **Meanwhile, if you respond** → `UserPromptSubmit` hook deletes the pending file
5. **After delay, notifier.sh wakes up:**
   - Pending file exists? → Send notification 🔔
   - Pending file gone? → You already responded, exit silently
6. **Race condition protection:** Each pending file contains a sequence number. Only the latest notifier can fire — older ones detect the mismatch and exit.

### Auto-Approve Flow

When you use a tool (Bash, Edit, Write, etc.):

1. **PreToolUse hook** fires before the tool executes
2. Reads your `auto_approve` setting
3. Returns `allow` for matching tools, or defers to normal permission flow

---

## Platform Support

### macOS (Recommended)

Works out of the box — uses the native `osascript` command. Notifications appear in macOS Notification Center with the Glass sound.

**Requirements:** None (osascript is built into macOS)

### Linux

Uses `notify-send` from libnotify for visual notifications and `paplay`/`aplay` for sound.

**Requirements:**
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

**Optional (for rich notifications):**
```powershell
Install-Module -Name BurntToast -Force
```

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
  🔔 Desktop notification: "Claude is waiting"
         ↓
  You switch back and continue the conversation
```

### Scenario 2: Active Conversation

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

### Scenario 3: Auto-Approve Bash

```
You: /notifyme:auto-approve bash
     "Run the test suite and fix any failures"
         ↓
Claude: [runs pytest — auto-approved ✓]
Claude: [edits test file — prompts for permission as usual]
Claude: [runs pytest again — auto-approved ✓]
```

---

## Troubleshooting

### Notifications not appearing?

1. **Check if enabled:** Run `/notifyme` to see status
2. **macOS:** Go to System Settings → Notifications → Terminal (or your terminal app) → ensure notifications are allowed
3. **Linux:** Verify `notify-send` is installed: `which notify-send`
4. **WSL:** Verify `powershell.exe` is accessible from WSL

### Auto-approve not working?

1. Run `/notifyme` to check the current mode
2. Make sure you're using the right mode (`bash` only approves Bash commands, not file edits)

### Want to change settings manually?

Edit `~/.claude/notifyme.json` directly — changes take effect on the next hook invocation (no restart needed).

---

## Project Structure

```
notifyme/
├── .claude-plugin/
│   └── plugin.json              # Plugin metadata
├── hooks/
│   ├── hooks.json               # Hook registrations
│   ├── stop.py                  # Stop hook — spawns delayed notifier
│   ├── pretooluse.py            # PreToolUse hook — auto-approve logic
│   ├── userpromptsubmit.py      # UserPromptSubmit hook — cancel notifications
│   └── notifier.sh              # Background notification script
├── core/
│   ├── __init__.py
│   └── config.py                # Config load/save with atomic writes
├── commands/
│   ├── notifyme.md              # /notifyme — show status
│   ├── on.md                    # /notifyme:on
│   ├── off.md                   # /notifyme:off
│   ├── delay.md                 # /notifyme:delay <seconds>
│   └── auto-approve.md          # /notifyme:auto-approve <mode>
├── README.md
└── LICENSE
```

---

## Contributing

Contributions are welcome! Feel free to:

- Report bugs or request features via [Issues](https://github.com/younann/notifyme-claude/issues)
- Submit pull requests for improvements
- Add support for additional notification backends

---

## License

[MIT](LICENSE) — Younan Nwesre
