# NotifyMe — Claude Code Plugin

**Never miss when Claude is done.** Get notifications when Claude Code finishes a task or is waiting for tool approval — via desktop, Slack DM, or email. Session-aware context tells you exactly which app and project needs attention. Works locally and on remote/cloud sessions.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20WSL-brightgreen.svg)](#platform-support)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Plugin-purple.svg)](https://claude.ai)
[![Tests](https://img.shields.io/badge/Tests-113%20passed-success.svg)](#testing)

---

## The Problem

You kick off a long task in Claude Code, switch to another window, and... forget about it. Minutes (or hours) later, you come back to find Claude has been patiently waiting for your input the whole time. Even worse — Claude might be waiting for you to approve a Bash command, and you don't even know it.

**Running Claude remotely?** Desktop notifications are useless on a cloud VM or SSH session.

**NotifyMe fixes this.** It notifies you when Claude is:
- **Done processing** and waiting for your next message
- **Waiting for tool approval** (e.g., "Allow Bash command?")

Through **multiple channels** — desktop, Slack DM, or email — so it works whether you're local or remote.

---

## Notification Channels

NotifyMe supports multiple notification channels that can be used simultaneously:

| Channel | Status | Use Case | Delay |
|---------|--------|----------|-------|
| **Desktop** | Stable | Local development — terminal/IDE comes to focus | Configurable (default 30s) |
| **Slack** | Stable | Remote/cloud sessions — DM via Slack Bot | Immediate |
| **Email** | Placeholder | Coming soon | — |

### Why Multiple Channels?

- **Desktop** uses a configurable delay — if you respond within 30s, no notification fires. Great when you're already at your machine.
- **Slack** fires immediately — when you're remote, you want to know right away. Fire-and-forget, can't be cancelled.
- Use both at once: Slack notifies you immediately, desktop pops up later if you still haven't responded.

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

### Re-notification

If you still haven't responded after the first notification, NotifyMe will **re-notify** you at a configurable interval (default: 60s). The title changes to **"Claude is still waiting"** so you know it's a reminder. Re-notification stops when you respond.

---

## Slack Notifications

For remote/cloud sessions where desktop notifications can't reach you, NotifyMe sends a **Slack DM** via a Bot token:

### Setup

1. **Create a Slack App** at [api.slack.com/apps](https://api.slack.com/apps)
2. Add the `chat:write` and `im:write` Bot Token Scopes under OAuth & Permissions
3. Install the app to your workspace and copy the Bot User OAuth Token (`xoxb-...`)
4. Find your Slack User ID (click your profile → three dots → "Copy member ID")
5. Configure in Claude Code:

```
/notifyme:slack bot_token xoxb-your-bot-token-here
/notifyme:slack user_id U0123ABC456
/notifyme:channel add slack
```

### What You'll Receive

A Slack DM with the same session-aware context:

```
*Claude is waiting — Warp*
Project: my-api
```

Slack notifications fire **immediately** — no delay. They're fire-and-forget; if you respond to Claude before seeing the Slack message, it's already sent (and that's fine).

---

## How It Works

NotifyMe uses three Claude Code hooks that coordinate through the filesystem:

<p align="center">
  <img src="assets/how-it-works.png" alt="How NotifyMe works — flow diagram" width="700">
</p>

### Detailed Flow

1. **Claude finishes its turn** — `Stop` hook fires, detects the frontmost app and project directory, builds the notification title/message, and dispatches to all enabled channels
2. **Claude needs tool approval** — `PreToolUse` hook fires when a tool isn't auto-approved, also dispatches notifications
3. **Desktop channel** writes a pending file to `/tmp/notifyme-<session>.pending` and spawns `notifier.sh` in the background, which sleeps for the configured delay
4. **Slack channel** immediately POSTs to the Slack API — no delay
5. **Meanwhile, if you respond** — `UserPromptSubmit` hook deletes the pending file, cancelling the desktop notification (Slack is already sent)
6. **After delay, notifier.sh wakes up:**
   - Pending file exists? — Send desktop notification, bring your app to focus, then re-notify at interval
   - Pending file gone? — You already responded, exit silently
7. **Race condition protection:** Each pending file contains a sequence number. Only the latest notifier can fire — older ones detect the mismatch and exit

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

For better notification click behavior, install [terminal-notifier](https://github.com/julienXX/terminal-notifier):
```bash
brew install terminal-notifier
```

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

Shows your current configuration at a glance, including active channels and their status.

```
NotifyMe Status
───────────────
Notifications: ON
Delay:         30s
Renotify:      60s
Auto-approve:  off
Sound:         ON
Channels:      desktop, slack
Slack:         configured ✓
Email:         not configured
```

### `/notifyme:on` / `/notifyme:off` — Toggle Notifications

```
> /notifyme:on
Notifications enabled.

> /notifyme:off
Notifications disabled.
```

### `/notifyme:delay <seconds>` — Set Delay

Set how long Claude waits before sending a desktop notification (1–3600 seconds). Only applies to the desktop channel.

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

### `/notifyme:channel <add|remove|list>` — Manage Channels

Enable or disable notification channels. Multiple channels can be active at once.

```
> /notifyme:channel list
Active channels: desktop

> /notifyme:channel add slack
Channel "slack" added. Active: desktop, slack

> /notifyme:channel remove desktop
Channel "desktop" removed. Active: slack
```

### `/notifyme:slack <bot_token|user_id> <value>` — Configure Slack

Set your Slack Bot credentials.

```
> /notifyme:slack bot_token xoxb-your-token-here
Slack bot_token set. Still need: user_id

> /notifyme:slack user_id U0123ABC456
Slack user_id set. Slack is now fully configured.
```

---

## Configuration

All settings persist across sessions in `~/.claude/notifyme.json`:

```json
{
  "notifications_enabled": true,
  "delay_seconds": 30,
  "renotify_interval": 60,
  "auto_approve": "off",
  "sound": true,
  "channels": ["desktop"],
  "slack": {
    "bot_token": "xoxb-...",
    "user_id": "U0123ABC456"
  }
}
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `notifications_enabled` | boolean | `true` | Master switch for notifications |
| `delay_seconds` | integer | `30` | Seconds to wait before desktop notification (1–3600) |
| `renotify_interval` | integer | `60` | Seconds between re-notifications (0 to disable) |
| `auto_approve` | string | `"off"` | Auto-approve mode: `off`, `bash`, or `all` |
| `sound` | boolean | `true` | Play sound with desktop notification |
| `channels` | array | `["desktop"]` | Active notification channels |
| `slack.bot_token` | string | — | Slack Bot User OAuth Token |
| `slack.user_id` | string | — | Your Slack User ID for DMs |

You can edit this file directly — changes take effect on the next hook invocation (no restart needed).

**Security note:** Slack credentials are stored in plaintext in this file. This is consistent with how Claude Code itself stores configuration. Keep `~/.claude/` private.

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
         ↓
  [60 more seconds, still no response]
         ↓
  🔔 "Claude is still waiting — Warp"  •  "Project: my-api"
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

### Scenario 3: Remote Cloud Session with Slack

```
You: [SSH into cloud VM, start Claude Code]
     /notifyme:channel add slack
     "Run the full test suite and fix failures"
Claude: [works for 10 minutes...]
Claude: [stops, waiting for input]
         ↓
  [Immediately]
         ↓
  💬 Slack DM: "*Claude is waiting*  Project: backend"
  → You see it on your phone, SSH back in
```

### Scenario 4: Multiple Sessions

```
Session 1 (Warp):   Working on "my-api"     → 🔔 "Claude is waiting — Warp"    Project: my-api
Session 2 (Warp):   Working on "frontend"   → 🔔 "Claude is waiting — Warp"    Project: frontend
Session 3 (Cursor): Working on "mobile-app" → 🔔 "Claude is waiting — Cursor"  Project: mobile-app
```

### Scenario 5: Active Conversation

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

### Scenario 6: Auto-Approve Bash

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

NotifyMe includes a comprehensive test suite with **113 tests** covering all components:

```bash
python3 -m pytest tests/ -v
```

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `test_config.py` | 13 | Config load/save, defaults, merge, atomic writes, error handling |
| `test_notify.py` | 26 | App detection, project detection, notification text building, channel dispatch |
| `test_channel_desktop.py` | 4 | Desktop channel pending file, notifier.sh spawn, atomic writes |
| `test_channel_slack.py` | 11 | Slack API calls, auth headers, config validation, error handling |
| `test_channel_email.py` | 3 | Email placeholder behavior |
| `test_channels_registry.py` | 6 | Channel registry dispatch, error isolation, unknown channels |
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
│   └── notifier.sh              # Background notifier — delayed desktop notifications + renotify
├── core/
│   ├── __init__.py
│   ├── config.py                # Config load/save with atomic writes
│   ├── notify.py                # Orchestrator — context detection, text building, channel dispatch
│   └── channels/
│       ├── __init__.py          # Channel registry — get_channel(), notify_all()
│       ├── desktop.py           # Desktop channel — pending file + notifier.sh
│       ├── slack.py             # Slack channel — Bot API DM via urllib
│       └── email.py             # Email channel — placeholder
├── commands/
│   ├── notifyme.md              # /notifyme — show status
│   ├── on.md                    # /notifyme:on
│   ├── off.md                   # /notifyme:off
│   ├── delay.md                 # /notifyme:delay <seconds>
│   ├── auto-approve.md          # /notifyme:auto-approve <mode>
│   ├── channel.md               # /notifyme:channel <add|remove|list>
│   └── slack.md                 # /notifyme:slack <bot_token|user_id> <value>
├── tests/                       # 113 tests covering all components
├── assets/                      # Screenshots
├── README.md
└── LICENSE
```

### Key Design Decisions

- **Multi-channel architecture:** Channel registry dispatches to desktop, Slack, and email independently. Each channel is a standalone module with a `send(title, message, context, config)` interface. Adding new channels means adding one file.
- **Desktop delayed, remote immediate:** Desktop notifications use a configurable delay to avoid bothering you when you're already looking. Slack fires immediately because you can't glance at the terminal remotely.
- **Re-notification:** If you don't respond, desktop notifications repeat at `renotify_interval` with "Claude is still waiting" — so you never miss it.
- **Session-aware context:** Each notification includes the app name (Warp, Cursor, Terminal, etc.) and project directory — so you know exactly which session needs attention
- **Native focus activation:** Uses `osascript tell application to activate` on macOS. Optional `terminal-notifier` support for better notification click behavior.
- **Tool approval notifications:** PreToolUse hook also triggers notifications when auto-approve is off, so you're notified when Claude is waiting for permission, not just when it's done
- **Zero external dependencies:** All network calls use Python's built-in `urllib.request`. No pip installs, no node modules.
- **Fault-tolerant channels:** A failing channel (network error, bad token) never blocks other channels or crashes the hook
- **Atomic file operations:** Config and pending files use temp-file-then-rename pattern to prevent corruption
- **Sequence numbers:** Millisecond-precision seq prevents race conditions when multiple notifiers are spawned

---

## Troubleshooting

### Notifications not appearing?

1. **Check if enabled:** Run `/notifyme` to see status
2. **macOS:** System Settings → Notifications → your terminal app → ensure allowed
3. **Linux:** Verify `notify-send` is installed: `which notify-send`
4. **WSL:** Verify `powershell.exe` is accessible from WSL

### Slack notifications not working?

1. Run `/notifyme` to check if Slack shows "configured ✓"
2. Verify `slack` is in your active channels: `/notifyme:channel list`
3. Check that your Bot token has `chat:write` and `im:write` scopes
4. Verify your User ID is correct (not your display name — it starts with `U`)

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
- Add support for additional notification channels (email providers, Discord, webhooks, etc.)

---

## License

[MIT](LICENSE) — Younan Nwesre
