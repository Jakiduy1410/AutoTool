#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "$0")/.." && pwd)
DEST="/sdcard/Download/DuyRejoin"

mkdir -p "$DEST"
rsync -a --delete \
  --exclude '.git' \
  --exclude 'data' \
  --exclude 'logs' \
  "$ROOT_DIR"/ "$DEST"/

echo "DONE"
