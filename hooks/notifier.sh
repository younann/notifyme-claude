#!/usr/bin/env bash
# Background notifier: sleeps for delay, then sends a session-aware
# desktop notification and brings the terminal/IDE to focus.
#
# Args: $1=delay_seconds $2=session_id $3=seq

DELAY="$1"
SESSION_ID="$2"
SEQ="$3"
PENDING_FILE="/tmp/notifyme-${SESSION_ID}.pending"

# --- Platform detection ---
detect_platform() {
  if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  elif grep -qi microsoft /proc/version 2>/dev/null; then
    echo "wsl"
  elif [[ "$OSTYPE" == "linux"* ]]; then
    echo "linux"
  else
    echo "unknown"
  fi
}

# --- Notification functions ---
notify_macos() {
  local sound="$1"
  local app_bundle="$2"
  local title="$3"
  local message="$4"

  if ! command -v osascript &>/dev/null; then return 1; fi

  # Escape double quotes for AppleScript strings
  local esc_title="${title//\"/\\\"}"
  local esc_message="${message//\"/\\\"}"

  # Send notification via terminal-notifier if available (supports click-to-activate)
  # Falls back to osascript (click opens Script Editor — an OS limitation)
  if command -v terminal-notifier &>/dev/null; then
    local tn_args=(-title "$title" -message "$message" -group "notifyme-${SESSION_ID}")
    if [ -n "$app_bundle" ]; then
      tn_args+=(-sender "$app_bundle" -activate "$app_bundle")
    fi
    if [ "$sound" = "true" ]; then
      tn_args+=(-sound Glass)
    fi
    terminal-notifier "${tn_args[@]}"
  else
    # Show notification first
    if [ "$sound" = "true" ]; then
      osascript -e "display notification \"${esc_message}\" with title \"${esc_title}\" sound name \"Glass\""
    else
      osascript -e "display notification \"${esc_message}\" with title \"${esc_title}\""
    fi
    # Then bring terminal/IDE to focus
    if [ -n "$app_bundle" ]; then
      osascript -e "tell application id \"${app_bundle}\" to activate"
    fi
  fi
}

notify_linux() {
  local sound="$1"
  local app_bundle="$2"
  local title="$3"
  local message="$4"

  if ! command -v notify-send &>/dev/null; then return 1; fi

  # Try notify-send with action (works on GNOME, KDE, etc.)
  if notify-send --help 2>&1 | grep -q "\-\-action"; then
    local action
    action=$(notify-send "$title" "$message" \
      --action="focus=Open Terminal" \
      --wait 2>/dev/null)
    if [ "$action" = "focus" ] && [ -n "$app_bundle" ]; then
      wmctrl -a "$app_bundle" 2>/dev/null || \
        xdotool search --name "$app_bundle" windowactivate 2>/dev/null
    fi
  else
    notify-send "$title" "$message"
  fi

  if [ "$sound" = "true" ]; then
    paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null ||
      aplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null
  fi
}

notify_wsl() {
  local sound="$1"
  local app_bundle="$2"
  local title="$3"
  local message="$4"

  if ! command -v powershell.exe &>/dev/null; then return 1; fi
  local sound_flag=""
  if [ "$sound" = "false" ]; then
    sound_flag="-Silent"
  fi
  powershell.exe -Command "
    if (Get-Module -ListAvailable -Name BurntToast) {
      New-BurntToastNotification -Text '$title', '$message' $sound_flag
    } else {
      [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;
      \$n = New-Object System.Windows.Forms.NotifyIcon;
      \$n.Icon = [System.Drawing.SystemIcons]::Information;
      \$n.Visible = \$true;
      \$n.ShowBalloonTip(5000, '$title', '$message', 'Info');
    }
  " 2>/dev/null
}

# --- Main ---
sleep "$DELAY"

# Check if pending file still exists
if [ ! -f "$PENDING_FILE" ]; then
  exit 0
fi

# Read pending file and verify seq
PENDING_CONTENT=$(cat "$PENDING_FILE" 2>/dev/null)
if [ -z "$PENDING_CONTENT" ]; then
  exit 0
fi

# Parse JSON fields (uses eval+shlex.quote for space-safe values)
eval "$(echo "$PENDING_CONTENT" | python3 -c "
import sys, json, shlex
d = json.load(sys.stdin)
print(f'FILE_SEQ={shlex.quote(str(d.get(\"seq\", \"\")))}')
print(f'FILE_SOUND={shlex.quote(str(d.get(\"sound\", True)).lower())}')
print(f'FILE_RENOTIFY={shlex.quote(str(d.get(\"renotify_interval\", 0)))}')
print(f'FILE_APP={shlex.quote(d.get(\"app\", \"\"))}')
print(f'NOTIF_TITLE={shlex.quote(d.get(\"title\", \"Claude is waiting\"))}')
print(f'NOTIF_MESSAGE={shlex.quote(d.get(\"message\", \"\"))}')
" 2>/dev/null)"

# Only the latest notifier should fire
if [ "$FILE_SEQ" != "$SEQ" ]; then
  exit 0
fi

# Send notification with app activation
send_notification() {
  PLATFORM=$(detect_platform)
  case "$PLATFORM" in
    macos) notify_macos "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
    linux) notify_linux "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
    wsl)   notify_wsl "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
    *)     exit 0 ;;
  esac
}

# First notification
send_notification

# Re-notify loop: keep reminding until user responds (deletes pending file)
if [ -n "$FILE_RENOTIFY" ] && [ "$FILE_RENOTIFY" -gt 0 ] 2>/dev/null; then
  while true; do
    sleep "$FILE_RENOTIFY"
    # User responded — pending file is gone
    if [ ! -f "$PENDING_FILE" ]; then
      exit 0
    fi
    # Another notifier superseded us — seq changed
    NEW_SEQ=$(echo "$(cat "$PENDING_FILE" 2>/dev/null)" | python3 -c "import sys,json; print(json.load(sys.stdin).get('seq',''))" 2>/dev/null)
    if [ "$NEW_SEQ" != "$SEQ" ]; then
      exit 0
    fi
    NOTIF_TITLE="${NOTIF_TITLE/Claude is waiting/Claude is still waiting}"
    send_notification
  done
fi

# Clean up (only reached if renotify is disabled)
rm -f "$PENDING_FILE"
