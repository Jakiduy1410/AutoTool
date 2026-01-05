#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
. "${SCRIPT_DIR}/../lib/sys.sh"

PACKAGE="${1-}"
if [ -z "$PACKAGE" ]; then
  log_err "Usage: $0 <package>"
  exit 1
fi

LOOPS=${LOOPS:-0}
INTERVAL=${INTERVAL:-3}
INGAME_ACTIVITY="${INGAME_ACTIVITY:-com.roblox.client.ActivityNativeMain}"

net_ok_streak=0
net_down_streak=0

escape_json() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

find_pid() {
  local pkg="$1"
  local pid

  pid=$(su_run "pidof -s ${pkg}" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "$pid"
    return
  fi

  pid=$(su_run "pgrep -f ${pkg}" 2>/dev/null | head -n 1 || true)
  if [ -n "$pid" ]; then
    echo "$pid"
    return
  fi

  pid=$(su_run "ps" 2>/dev/null | awk -v pkg="${pkg}" 'NR>1 && $NF ~ pkg {print $2; exit}')
  if [ -n "$pid" ]; then
    echo "$pid"
  fi
}

get_resumed_activity() {
  local dump
  dump=$(su_run "dumpsys activity activities" 2>/dev/null || true)
  printf '%s\n' "$dump" | grep -m1 'mResumedActivity' || true
}

check_net() {
  if su_run "ping -c1 -W1 1.1.1.1" >/dev/null 2>&1; then
    echo "NET_OK"
    return
  fi

  if su_run "ping -c1 -W1 8.8.8.8" >/dev/null 2>&1; then
    echo "NET_OK"
  else
    echo "NET_DOWN"
  fi
}

loop_count=0
while :; do
  if [ "$LOOPS" -gt 0 ] && [ "$loop_count" -ge "$LOOPS" ]; then
    break
  fi

  ts=$(now_ts)
  pid=$(find_pid "$PACKAGE" || true)
  pid_output="null"
  if [ -n "${pid-}" ]; then
    pid_output="$pid"
  fi

  resumed_line=$(get_resumed_activity)
  resumed=""
  if [ -n "$resumed_line" ]; then
    resumed=${resumed_line#*mResumedActivity: }
  fi

  ingame=false
  if printf '%s' "$resumed" | grep -q "$INGAME_ACTIVITY"; then
    ingame=true
  fi

  net_status=$(check_net)
  if [ "$net_status" = "NET_OK" ]; then
    net_ok_streak=$((net_ok_streak + 1))
    net_down_streak=0
  else
    net_down_streak=$((net_down_streak + 1))
    net_ok_streak=0
  fi

  if [ "$net_down_streak" -ge 3 ]; then
    log_warn "NET_DOWN streak reached ${net_down_streak} (threshold: disconnect)"
  elif [ "$net_ok_streak" -ge 2 ]; then
    log_info "NET_OK streak reached ${net_ok_streak} (threshold: recover)"
  fi

  resumed_json=$(escape_json "$resumed")
  printf '{"ts":%s,"package":"%s","pid":%s,"resumed":"%s","ingame":%s,"net":"%s","net_ok_streak":%s,"net_down_streak":%s}\n' \
    "$ts" "$PACKAGE" "$pid_output" "$resumed_json" "$ingame" "$net_status" "$net_ok_streak" "$net_down_streak"

  loop_count=$((loop_count + 1))
  sleep "$INTERVAL"
done
