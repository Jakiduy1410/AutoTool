#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE="/sdcard/Download/AutoTool"
mkdir -p "$BASE/config" "$BASE/runtime/clones" "$BASE/logs"

if [ ! -f "$BASE/config/packages.json" ]; then
  echo "❌ Chưa có $BASE/config/packages.json"
  echo "➡️ Hãy chạy menu [4] Check User Setup trước."
  exit 0
fi

bash bin/start_watchdog.sh
echo "✅ Auto Rejoin started."

# nhảy sang dashboard để theo dõi RAM/CPU + state
bash ui/status.sh
