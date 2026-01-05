#!/data/data/com.termux/files/usr/bin/env bash
set -euo pipefail

DST="/sdcard/Download/DuyRejoin"

printf '[*] Updating packages...\n'
pkg update -y
printf '[*] Installing dependencies...\n'
pkg install -y git rsync procps iproute2 coreutils

printf '[*] Ensuring storage permission...\n'
termux-setup-storage || true

printf '[*] Creating runtime directories at %s...\n' "$DST"
mkdir -p "$DST"/bin
mkdir -p "$DST"/app
mkdir -p "$DST"/scripts
mkdir -p "$DST"/data
mkdir -p "$DST"/logs

printf '[*] Bootstrap complete.\n'
