#!/data/data/com.termux/files/usr/bin/bash
set -e

CFG="$(cd "$(dirname "$0")/../config" && pwd)/global.json"

cur="$(python - <<PY
import json, pathlib
p=pathlib.Path("$CFG")
d=json.loads(p.read_text()) if p.exists() else {}
print(d.get("package_prefix",""))
PY
)"

echo "Prefix hiện tại: ${cur:-<trống>}"
read -r -p "Nhập prefix mới (ví dụ: com.roblox): " newp

python - <<PY
import json, pathlib
cfg=pathlib.Path("$CFG")
d=json.loads(cfg.read_text()) if cfg.exists() else {}
d["package_prefix"]="$newp".strip()
cfg.write_text(json.dumps(d, indent=2, ensure_ascii=False))
print("Đã lưu prefix:", d["package_prefix"])
PY
