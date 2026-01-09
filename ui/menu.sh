#!/data/data/com.termux/files/usr/bin/bash
set -e

WF_DIR="$(cd "$(dirname "$0")/../workflows" && pwd)"

pause() { read -r -p $'\nNhấn Enter để tiếp tục...'; }

while true; do
  clear
  echo "=============================="
  echo "      AUTO TOOL (UGPHONE)     "
  echo "=============================="
  echo "[1] Join Game + Start Watchdog + Status"
  echo "[2] Scan Packages + Select Game ID"
  echo "[3] Set Package Prefix"
  echo "[4] Check User Setup (scan packages)"
  echo "[5] (Phase 4)"
  echo "[6] (Phase 4)"
  echo "[7] Exit (auto stop watchdog)"
  echo "------------------------------"
  read -r -p "Chọn (1-7): " choice

  case "$choice" in
    1) bash "$WF_DIR/start_auto_rejoin.sh"; pause ;;
    2) bash "$WF_DIR/setup_game_and_packages.sh"; pause ;;
    3) bash "$WF_DIR/set_package_prefix.sh"; pause ;;
    4) bash "$WF_DIR/check_user_setup.sh"; pause ;;
    5) echo "Chưa tới Phase 4"; pause ;;
    6) echo "Chưa tới Phase 4"; pause ;;
    7) bash bin/stop_watchdog.sh >/dev/null 2>&1 || true; exit 0 ;;
    *) echo "Sai lựa chọn"; pause ;;
  esac
done
