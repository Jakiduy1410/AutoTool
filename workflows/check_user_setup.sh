#!/usr/bin/env bash
set -e

BASE="/sdcard/Download/AutoTool"
CFG_DIR="$BASE/config"
GLOBAL="$CFG_DIR/global.json"
OUT="$CFG_DIR/packages.json"

mkdir -p "$CFG_DIR"

prefix="$(python - <<PY
import json, pathlib
p=pathlib.Path("$GLOBAL")
d=json.loads(p.read_text()) if p.exists() else {}
print(d.get("package_prefix","").strip())
PY
)"

if [ -z "$prefix" ]; then
  echo "❌ Chưa set package_prefix. Vào menu [3] trước."
  exit 0
fi

echo "✅ package_prefix = $prefix"
echo "Đang quét packages..."

pkgs="$(pm list packages | sed 's/package://g' | grep -F "$prefix" || true)"

if [ -z "$pkgs" ]; then
  echo "⚠️ Không tìm thấy package nào match prefix."
else
  echo "Tìm thấy:"
  echo "$pkgs" | nl -w2 -s'. '
fi

python - <<PY
import json
pkgs = """$pkgs""".strip().splitlines() if """$pkgs""".strip() else []
out = {"prefix": "$prefix", "packages": pkgs}
open("$OUT","w",encoding="utf-8").write(json.dumps(out, indent=2, ensure_ascii=False))
print("✅ Đã lưu:", "$OUT", "| count =", len(pkgs))
PY
