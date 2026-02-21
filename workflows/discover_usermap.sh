#!/usr/bin/env bash
set -e

BASE="/sdcard/Download/AutoTool"
CODEX_WS="/storage/emulated/0/Codex/Workspace"
PKGFILE="$BASE/config/packages.json"
OUTFILE="$BASE/config/user_map.json"
GRACE=25

if [ ! -f "$PKGFILE" ]; then
  echo "❌ Chưa có packages.json — chạy menu [4] trước."
  exit 1
fi

# Đọc danh sách packages
mapfile -t PACKS < <(python3 -c "
import json
for p in json.load(open('$PKGFILE'))['packages']:
    print(p)
")

echo "=============================="
echo "   DISCOVER USERID MAP"
echo "=============================="
echo "Sẽ mở từng clone một, kill hết clone khác trước."
echo "Đảm bảo executor_check.lua đã có trong Autoexec Codex!"
echo ""
read -r -p "Bắt đầu? (Enter để tiếp tục): "

# Kill tất cả clone trước
echo ""
echo "── Kill tất cả clone ──"
for pkg in "${PACKS[@]}"; do
  su -c "am force-stop $pkg" >/dev/null 2>&1
  echo "  stopped: $pkg"
done
sleep 3

# Kết quả mapping
declare -A USERMAP

for pkg in "${PACKS[@]}"; do
  echo ""
  echo "── Discover: $pkg ──"

  # Kill tất cả clone (phòng có cái nào còn sót)
  for p in "${PACKS[@]}"; do
    su -c "am force-stop $p" >/dev/null 2>&1
  done
  sleep 2

  # Snapshot file .main TRƯỚC khi mở
  declare -A before_map
  for f in "$CODEX_WS"/*.main; do
    [ -f "$f" ] || continue
    before_map["$f"]=1
  done

  # Mở clone
  su -c "monkey -p $pkg -c android.intent.category.LAUNCHER 1" >/dev/null 2>&1
  echo "  → Đã mở, chờ ${GRACE}s..."

  # Chờ từng giây, phát hiện file mới ngay khi xuất hiện
  found_uid=""
  for i in $(seq 1 $GRACE); do
    sleep 1
    for f in "$CODEX_WS"/*.main; do
      [ -f "$f" ] || continue
      # File này có trong before không?
      if [ -z "${before_map[$f]+x}" ]; then
        # File mới xuất hiện!
        uid=$(basename "$f" .main)
        found_uid="$uid"
        break 2
      fi
    done
  done

  if [ -n "$found_uid" ]; then
    echo "  ✅ UserId = $found_uid"
    USERMAP[$pkg]=$found_uid
  else
    # Không có file mới → tìm file nào vừa update gần nhất
    echo "  ⚠️  Không có file mới, tìm file vừa update..."
    newest=""
    newest_age=9999
    for f in "$CODEX_WS"/*.main; do
      [ -f "$f" ] || continue
      age=$(( $(date +%s) - $(stat -c %Y "$f") ))
      if [ "$age" -lt "$newest_age" ]; then
        newest_age=$age
        newest="$f"
      fi
    done

    if [ -n "$newest" ] && [ "$newest_age" -le $(( GRACE + 5 )) ]; then
      uid=$(basename "$newest" .main)
      echo "  ✅ UserId = $uid (fallback, age=${newest_age}s)"
      USERMAP[$pkg]=$uid
    else
      echo "  ❌ Không detect được — executor có thể chưa inject"
      echo "     Kiểm tra executor_check.lua có trong Autoexec chưa?"
    fi
  fi

  # Kill clone sau khi discover xong
  su -c "am force-stop $pkg" >/dev/null 2>&1
  sleep 3
done

# Ghi kết quả ra JSON
echo ""
echo "── Lưu user_map.json ──"
python3 - << PY
import json, os

data = {}
$(for pkg in "${!USERMAP[@]}"; do
  echo "data['$pkg'] = '${USERMAP[$pkg]}'"
done)

os.makedirs(os.path.dirname("$OUTFILE"), exist_ok=True)
with open("$OUTFILE", "w") as f:
    json.dump(data, f, indent=2)

print(f"✅ Đã lưu {len(data)} mapping:")
for k, v in data.items():
    print(f"   {k} → {v}")
PY

echo ""
echo "✅ Xong! Giờ bật watchdog qua menu [1]."
