#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail

su_run() {
  if command -v su >/dev/null 2>&1; then
    su -c "$*"
  else
    eval "$*"
  fi
}

now_ts() {
  date +%s
}

log_info() {
  printf '[INFO] %s\n' "$*" >&2
}

log_warn() {
  printf '[WARN] %s\n' "$*" >&2
}

log_err() {
  printf '[ERROR] %s\n' "$*" >&2
}
