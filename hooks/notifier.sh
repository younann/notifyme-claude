#!/usr/bin/env bash
# Background notifier: sleeps for delay, then sends desktop notification
# if the user hasn't responded yet. Clicking the notification focuses the
# terminal/IDE that Claude Code is running in.
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

  # Prefer terminal-notifier: supports click-to-activate
  if command -v terminal-notifier &>/dev/null && [ -n "$app_bundle" ]; then
    local sound_flag=""
    if [ "$sound" = "true" ]; then
      sound_flag="-sound Glass"
    fi
    terminal-notifier \
      -title "Claude is waiting" \
      -message "Claude Code has finished and is waiting for your input." \
      -activate "$app_bundle" \
      $sound_flag \
      -group "notifyme-${SESSION_ID}" 2>/dev/null
    return 0
  fi

  # Fallback: osascript notification + activate the app
  if ! command -v osascript &>/dev/null; then return 1; fi
  if [ "$sound" = "true" ]; then
    osascript -e 'display notification "Claude Code has finished and is waiting for your input." with title "Claude is waiting" sound name "Glass"'
  else
    osascript -e 'display notification "Claude Code has finished and is waiting for your input." with title "Claude is waiting"'
  fi

  # Bring the terminal/IDE to front (best-effort)
  if [ -n "$app_bundle" ]; then
    osascript -e "
      tell application id \"$app_bundle\"
        activate
      end tell
    " 2>/dev/null
  fi
}

notify_linux() {
  local sound="$1"
  local app_bundle="$2"
  if ! command -v notify-send &>/dev/null; then return 1; fi

  # Try notify-send with action (works on GNOME, KDE, etc.)
  if notify-send --help 2>&1 | grep -q "\-\-action"; then
    local action
    action=$(notify-send "Claude is waiting" \
      "Claude Code has finished and is waiting for your input." \
      --action="focus=Open Terminal" \
      --wait 2>/dev/null)
    if [ "$action" = "focus" ] && [ -n "$app_bundle" ]; then
      # app_bundle on Linux is the WM_CLASS or executable name
      wmctrl -a "$app_bundle" 2>/dev/null || xdotool search --name "$app_bundle" windowactivate 2>/dev/null
    fi
  else
    notify-send "Claude is waiting" "Claude Code has finished and is waiting for your input."
  fi

  if [ "$sound" = "true" ]; then
    paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null ||
      aplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null
  fi
}

notify_wsl() {
  local sound="$1"
  local app_bundle="$2"
  if ! command -v powershell.exe &>/dev/null; then return 1; fi
  local sound_flag=""
  if [ "$sound" = "false" ]; then
    sound_flag="-Silent"
  fi
  # BurntToast supports -ActivatedAction to bring window to front
  powershell.exe -Command "
    if (Get-Module -ListAvailable -Name BurntToast) {
      \$activateAction = { (Get-Process -Name '$app_bundle' -ErrorAction SilentlyContinue | Select-Object -First 1).MainWindowHandle | ForEach-Object { [void][System.Runtime.InteropServices.Marshal]::GetDelegateForFunctionPointer((Add-Type -PassThru -Name NativeMethods -Namespace Win32 -MemberDefinition '[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd);')::SetForegroundWindow(\$_) } }
      New-BurntToastNotification -Text 'Claude is waiting', 'Claude Code has finished and is waiting for your input.' $sound_flag
    } else {
      [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null;
      \$n = New-Object System.Windows.Forms.NotifyIcon;
      \$n.Icon = [System.Drawing.SystemIcons]::Information;
      \$n.Visible = \$true;
      \$n.ShowBalloonTip(5000, 'Claude is waiting', 'Claude Code has finished and is waiting for your input.', 'Info');
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
FILE_SEQ=$(echo "$PENDING_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('seq',''))" 2>/dev/null)
FILE_SOUND=$(echo "$PENDING_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(str(d.get('sound',True)).lower())" 2>/dev/null)
FILE_APP=$(echo "$PENDING_CONTENT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('app',''))" 2>/dev/null)

# Only the latest notifier should fire
if [ "$FILE_SEQ" != "$SEQ" ]; then
  exit 0
fi

# Send notification with app activation
PLATFORM=$(detect_platform)
case "$PLATFORM" in
  macos) notify_macos "$FILE_SOUND" "$FILE_APP" ;;
  linux) notify_linux "$FILE_SOUND" "$FILE_APP" ;;
  wsl)   notify_wsl "$FILE_SOUND" "$FILE_APP" ;;
  *)     exit 0 ;;
esac

# Clean up
rm -f "$PENDING_FILE"
