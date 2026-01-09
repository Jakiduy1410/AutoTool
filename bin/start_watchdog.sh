#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE="/sdcard/Download/AutoTool"
PIDFILE="$BASE/runtime/watchdog.pid"
LOG="$BASE/logs/watchdog.log"

mkdir -p "$BASE/runtime" "$BASE/logs"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Watchdog đang chạy (pid=$(cat "$PIDFILE"))"
  exit 0
fi

nohup python "$PWD/engine/watchdog.py" >> "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Started watchdog pid=$!"
