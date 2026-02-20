#!/usr/bin/env bash
set -e

echo "[*] Installing deps..."
pkg install -y python git rsync procps iproute2 coreutils tsu

echo "[*] Setup storage..."
termux-setup-storage

BASE=/sdcard/Download/AutoTool
mkdir -p $BASE/logs $BASE/runtime

echo "[*] Test log write..."
echo "BOOTSTRAP_OK $(date)" >> $BASE/logs/bootstrap.log

echo "[✓] Phase 0 bootstrap done"
