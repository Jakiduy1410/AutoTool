#!/usr/bin/env bash
set -e

BASE="/sdcard/Download/AutoTool"
PKGFILE="$BASE/config/packages.json"
MAPFILE="$BASE/runtime/user_map.json"
GLOBAL="$BASE/config/global.json"

if [ ! -f "$PKGFILE" ]; then
  echo "❌ Chưa có $PKGFILE"
  echo "➡️ Hãy chạy menu [4] Check User Setup trước."
  exit 0
fi

join_url="$(python - <<PY
import json, pathlib
p=pathlib.Path("$GLOBAL")
d=json.loads(p.read_text()) if p.exists() else {}
print(d.get("join_url","").strip())
PY
)"

python - <<PY
import json, pathlib, subprocess

pkgfile=pathlib.Path("$PKGFILE")
packs=json.loads(pkgfile.read_text(encoding="utf-8")).get("packages",[])
mapfile=pathlib.Path("$MAPFILE")
user_map={}
if mapfile.exists():
    try: user_map=json.loads(mapfile.read_text(encoding="utf-8"))
    except: user_map={}

def pidof(pkg):
    try:
        out=subprocess.check_output(f"pidof {pkg}", shell=True, text=True).strip()
        return out.split()[0] if out else "None"
    except:
        return "None"

print("SCAN PACKAGES + CHECK LOGIN (best-effort)")
print("-"*60)
for i,pkg in enumerate(packs,1):
    pid=pidof(pkg)
    uid=user_map.get(pkg, "UNKNOWN")
    print(f"{i:2}. {pkg:28} pid={pid:6} userId={uid}")
print("-"*60)
PY

echo
echo "Tuỳ chọn:"
echo "  [j] Test JOIN game (mở join_url bằng clone bạn chọn)"
echo "  [Enter] Thoát"
read -r -p "Chọn: " opt

if [ "$opt" = "j" ]; then
  read -r -p "Nhập số clone (ví dụ 1): " idx
  pkg="$(python - <<PY
import json
packs=json.load(open("$PKGFILE","r",encoding="utf-8")).get("packages",[])
i=int("$idx")-1
print(packs[i] if 0 <= i < len(packs) else "")
PY
)"
  if [ -z "$pkg" ]; then
    echo "❌ Số không hợp lệ."
    exit 0
  fi
  if [ -z "$join_url" ]; then
    echo "❌ Chưa set join_url trong $GLOBAL"
    exit 0
  fi
  echo "➡️ JOIN: $pkg"
  su -c "am start -a android.intent.action.VIEW -d '$join_url' -p '$pkg'" >/dev/null 2>&1 || true
  echo "✅ Đã bắn intent join (nếu chưa login thì Roblox sẽ tự hiện màn login)."
fi
