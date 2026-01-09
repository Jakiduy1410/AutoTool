#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE="/sdcard/Download/AutoTool"
CFG="$BASE/config"
GAMES="$CFG/games.json"
GLOBAL="$CFG/global.json"
PKGFILE="$CFG/packages.json"

mkdir -p "$CFG"

# 1) Quét packages theo prefix (reuse workflow cũ)
bash workflows/check_user_setup.sh >/dev/null

if [ ! -f "$PKGFILE" ]; then
  echo "❌ Không tạo được packages.json. Hãy chạy [4] trước."
  exit 0
fi

echo "✅ Packages hiện tại:"
python - <<PY
import json
d=json.load(open("$PKGFILE","r",encoding="utf-8"))
packs=d.get("packages",[])
for i,p in enumerate(packs,1):
    print(f"{i}. {p}")
print("Total:", len(packs))
PY

echo
echo "================= CHỌN GAME ================="
if [ ! -f "$GAMES" ]; then
  echo "❌ Thiếu $GAMES"
  exit 0
fi

python - <<PY
import json
d=json.load(open("$GAMES","r",encoding="utf-8"))
games=d.get("games",[])
for i,g in enumerate(games,1):
    print(f"{i}. {g.get('name','(no name)')}  | placeId={g.get('placeId')}")
PY

read -r -p "Chọn số game (Enter = 1): " pick
pick="${pick:-1}"

python - <<PY
import json, pathlib
games=json.load(open("$GAMES","r",encoding="utf-8")).get("games",[])
i=int("$pick")-1
if not (0 <= i < len(games)):
    raise SystemExit("❌ Số game không hợp lệ")
g=games[i]
placeId=int(g["placeId"])
name=str(g.get("name","Roblox Game"))

cfg_path=pathlib.Path("$GLOBAL")
cfg=json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}

cfg["selected_game_name"]=name
cfg["selected_place_id"]=placeId
cfg["join_url"]=f"roblox://placeId={placeId}"
cfg["fallback_url"]=f"https://www.roblox.com/games/{placeId}"

cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print("✅ Đã set game:", name, "| placeId=", placeId)
print("   join_url =", cfg["join_url"])
PY

echo
echo "✅ Setup xong. Giờ bấm [1] để join game + bật watchdog."
