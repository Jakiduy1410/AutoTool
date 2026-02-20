#!/usr/bin/env bash
set -e

BASE="/sdcard/Download/AutoTool"
PIDFILE="$BASE/runtime/watchdog.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "Không có pidfile (watchdog có thể chưa chạy)."
  exit 0
fi

PID="$(cat "$PIDFILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stopped watchdog pid=$PID"
else
  echo "PID không tồn tại, dọn pidfile."
fi

rm -f "$PIDFILE"
