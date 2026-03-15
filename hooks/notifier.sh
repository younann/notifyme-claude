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

# --- Build notification text from session context ---
build_notification_text() {
  local app_name="$1"
  local project="$2"

  local title="Claude is waiting"
  local message=""

  # Build a contextual message that identifies the session
  if [ -n "$app_name" ] && [ -n "$project" ]; then
    title="Claude is waiting — ${app_name}"
    message="Project: ${project}"
  elif [ -n "$app_name" ]; then
    title="Claude is waiting — ${app_name}"
    message="Claude Code has finished and is waiting for your input."
  elif [ -n "$project" ]; then
    title="Claude is waiting"
    message="Project: ${project}"
  else
    message="Claude Code has finished and is waiting for your input."
  fi

  # Return via global vars (bash can't return two values)
  NOTIF_TITLE="$title"
  NOTIF_MESSAGE="$message"
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

  # Send notification FROM the terminal/IDE app so clicking it activates that app
  # Also activate the app immediately so the user is brought to the session
  if [ -n "$app_bundle" ]; then
    osascript -e "
      tell application id \"${app_bundle}\"
        activate
        display notification \"${esc_message}\" with title \"${esc_title}\"$([ "$sound" = "true" ] && echo " sound name \"Glass\"")
      end tell
    "
  else
    if [ "$sound" = "true" ]; then
      osascript -e "display notification \"${esc_message}\" with title \"${esc_title}\" sound name \"Glass\""
    else
      osascript -e "display notification \"${esc_message}\" with title \"${esc_title}\""
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

# Parse JSON with python3 (available since hooks use it)
read -r FILE_SEQ FILE_SOUND FILE_APP FILE_APP_NAME FILE_PROJECT < <(
  echo "$PENDING_CONTENT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(
    d.get('seq', ''),
    str(d.get('sound', True)).lower(),
    d.get('app', ''),
    d.get('app_name', ''),
    d.get('project', '')
)
" 2>/dev/null
)

# Only the latest notifier should fire
if [ "$FILE_SEQ" != "$SEQ" ]; then
  exit 0
fi

# Build contextual notification text
build_notification_text "$FILE_APP_NAME" "$FILE_PROJECT"

# Send notification with app activation
PLATFORM=$(detect_platform)
case "$PLATFORM" in
  macos) notify_macos "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
  linux) notify_linux "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
  wsl)   notify_wsl "$FILE_SOUND" "$FILE_APP" "$NOTIF_TITLE" "$NOTIF_MESSAGE" ;;
  *)     exit 0 ;;
esac

# Clean up
rm -f "$PENDING_FILE"
