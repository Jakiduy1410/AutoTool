#!/usr/bin/env bash
# Chạy một lần để build mapping package → UserId
# Kết quả lưu vào config/user_map.json

BASE="/sdcard/Download/AutoTool"
CODEX_WS="/storage/emulated/0/Codex/Workspace"
PKGFILE="$BASE/config/packages.json"
OUTFILE="$BASE/config/user_map.json"
GRACE=20  # giây chờ executor inject

if [ ! -f "$PKGFILE" ]; then
  echo "❌ Chưa có packages.json — chạy menu [4] trước."
  exit 1
fi

packs=$(python3 -c "
import json
packs = json.load(open('$PKGFILE'))['packages']
for p in packs: print(p)
")

echo "=============================="
echo "   DISCOVER USERID MAP"
echo "=============================="
echo "Sẽ mở từng clone lần lượt, chờ executor inject rồi detect UserId."
echo "Đảm bảo executor_check.lua đã có trong Autoexec của Codex!"
echo ""
read -r -p "Bắt đầu? (Enter để tiếp tục, Ctrl+C để hủy): "

# Snapshot file .main hiện có
existing=$(ls "$CODEX_WS"/*.main 2>/dev/null | xargs -I{} basename {} .main | sort)

declare -A result

for pkg in $packs; do
  echo ""
  echo "── Clone: $pkg ──"

  # Dừng app trước
  su -c "am force-stop $pkg" >/dev/null 2>&1

  # Snapshot trước khi mở
  before=$(ls "$CODEX_WS"/*.main 2>/dev/null | xargs -I{} basename {} .main | sort)

  # Mở app
  su -c "monkey -p $pkg -c android.intent.category.LAUNCHER 1" >/dev/null 2>&1
  echo "  → Đã mở, chờ ${GRACE}s cho executor inject..."
  sleep "$GRACE"

  # Tìm file .main mới nhất (mtime gần nhất)
  newest=$(ls -t "$CODEX_WS"/*.main 2>/dev/null | head -1)
  if [ -z "$newest" ]; then
    echo "  ⚠️  Không tìm thấy .main file — bỏ qua"
    continue
  fi

  age=$(( $(date +%s) - $(stat -c %Y "$newest") ))
  user_id=$(basename "$newest" .main)

  if [ "$age" -le $(( GRACE + 5 )) ]; then
    echo "  ✅ UserId = $user_id (age=${age}s)"
    result[$pkg]=$user_id
  else
    echo "  ⚠️  File quá cũ (age=${age}s) — executor có thể chưa inject"
    echo "  → Gán tạm $user_id, bạn có thể sửa sau trong user_map.json"
    result[$pkg]=$user_id
  fi

  # Dừng app sau khi discover xong
  su -c "am force-stop $pkg" >/dev/null 2>&1
  sleep 3
done

# Ghi kết quả ra JSON
python3 - << PY
import json, os
data = {}
$(for pkg in "${!result[@]}"; do echo "data['$pkg'] = '${result[$pkg]}'"; done)
os.makedirs(os.path.dirname("$OUTFILE"), exist_ok=True)
json.dump(data, open("$OUTFILE", "w"), indent=2)
print("✅ Đã lưu user_map.json:")
for k, v in data.items():
    print(f"   {k} → {v}")
PY

echo ""
echo "✅ Discover xong! Giờ bật watchdog bình thường qua menu [1]."
