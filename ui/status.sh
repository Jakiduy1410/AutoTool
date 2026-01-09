#!/data/data/com.termux/files/usr/bin/bash
set -e

BASE="/sdcard/Download/AutoTool"
STATE="$BASE/runtime/watchdog_state.json"
PIDFILE="$BASE/runtime/watchdog.pid"
MAP="$BASE/runtime/user_map.json"

# ---- terminal helpers (tput ưu tiên) ----
has_tput=1
command -v tput >/dev/null 2>&1 || has_tput=0

cup(){ # row col (1-based)
  if [ "$has_tput" = "1" ]; then tput cup $(( $1-1 )) $(( $2-1 )); else printf "\033[%s;%sH" "$1" "$2"; fi
}
clr_eol(){
  if [ "$has_tput" = "1" ]; then tput el; else printf "\033[K"; fi
}
hide_cursor(){
  if [ "$has_tput" = "1" ]; then tput civis 2>/dev/null || true; else printf "\033[?25l"; fi
}
show_cursor(){
  if [ "$has_tput" = "1" ]; then tput cnorm 2>/dev/null || true; else printf "\033[?25h"; fi
}

print_at(){ # row col text (pad để đè sạch)
  cup "$1" "$2"; clr_eol
  printf "%-78s" "$3"
}

# ---- CPU% from /proc/stat delta ----
cpu_init() {
  read -r _ u n s i iw irq sirq stl _ < /proc/stat
  CPU_T=$((u+n+s+i+iw+irq+sirq+stl))
  CPU_I=$((i+iw))
}
cpu_percent() {
  read -r _ u n s i iw irq sirq stl _ < /proc/stat
  local t=$((u+n+s+i+iw+irq+sirq+stl))
  local id=$((i+iw))
  local td=$((t-CPU_T))
  local idd=$((id-CPU_I))
  CPU_T=$t; CPU_I=$id
  [ "$td" -le 0 ] && { echo 0; return; }
  echo $(( (100*(td-idd))/td ))
}

ram_percent_line() {
  local mt ma used pct
  mt=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
  ma=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
  used=$((mt-ma))
  pct=$(( (100*used)/mt ))
  # kB -> MB
  echo "${pct}% (${used/1024}MB/${mt/1024}MB)"
}

watchdog_pid() {
  if [ -f "$PIDFILE" ]; then
    cat "$PIDFILE" 2>/dev/null || echo "-"
  else
    echo "-"
  fi
}

render_frame() {
  clear
  echo "========================== AUTO TOOL STATUS =========================="
  echo " CPU: --%                 RAM: --%                                  "
  echo " NET: --                  TIME: ----                 WD_PID: --       "
  echo "-----------------------------------------------------------------------"
  echo " #  PACKAGE                     USER        PID     STATE     RC  CD "
  echo "-----------------------------------------------------------------------"
  for _ in $(seq 1 8); do echo "                                                                       "; done
  echo "-----------------------------------------------------------------------"
  echo " Controls: [q] Back   [x] Stop watchdog + Exit dashboard"
}

cleanup(){ show_cursor; }
trap cleanup EXIT

hide_cursor
render_frame
cpu_init

while true; do
  # --- system bar ---
  cpu="$(cpu_percent)"
  ram="$(ram_percent_line)"
  wd="$(watchdog_pid)"

  net="?"
  tm="?"
  if [ -f "$STATE" ]; then
    net="$(python - <<PY
import json
d=json.load(open("$STATE","r",encoding="utf-8"))
print(d.get("net","?"))
PY
)"
    tm="$(python - <<PY
import json
d=json.load(open("$STATE","r",encoding="utf-8"))
print(d.get("time","?"))
PY
)"
  fi

  print_at 2 2 "CPU: ${cpu}%"
  print_at 2 26 "RAM: ${ram}"
  print_at 3 2 "NET: ${net}"
  print_at 3 22 "TIME: ${tm}"
  print_at 3 55 "WD_PID: ${wd}"

  # --- clones table (8 dòng cố định) ---
  # chuẩn bị 8 dòng data bằng 1 lần python duy nhất
  lines="$(python - <<PY
import json, os, time
state_path="$STATE"
map_path="$MAP"

packs=[]
if os.path.exists(state_path):
    d=json.load(open(state_path,"r",encoding="utf-8"))
    packs=d.get("packages",[])

user_map={}
if os.path.exists(map_path):
    try: user_map=json.load(open(map_path,"r",encoding="utf-8"))
    except: user_map={}

now=int(time.time())

out=[]
for i,x in enumerate(packs[:8],1):
    pkg=x.get("package","")
    uid=str(user_map.get(pkg,"UNKNOWN"))
    pid=x.get("pid")
    pid="None" if pid is None else str(pid)
    st=x.get("status","")
    rc=str(x.get("restart_count",""))
    cd_until=int(x.get("cooldown_until",0) or 0)
    cd=max(0, cd_until-now)
    # output: idx|pkg|uid|pid|st|rc|cd
    out.append(f"{i}|{pkg}|{uid}|{pid}|{st}|{rc}|{cd}")
print("\\n".join(out))
PY
)"

  # clear 8 rows first
  start_row=6
  for j in $(seq 0 7); do
    print_at $((start_row+j)) 1 " "
  done

  if [ -n "$lines" ]; then
    row=0
    while IFS='|' read -r idx pkg uid pid st rc cd; do
      # fixed widths
      pkg2="${pkg:0:26}"
      uid2="${uid:0:10}"
      pid2="${pid:0:7}"
      st2="${st:0:9}"
      rc2="${rc:0:3}"
      cd2="${cd:0:3}"

      print_at $((start_row+row)) 1 "$(printf " %-2s %-26s %-10s %-7s %-9s %-3s %-3s" "$idx" "$pkg2" "$uid2" "$pid2" "$st2" "$rc2" "$cd2")"
      row=$((row+1))
    done <<< "$lines"
  else
    print_at "$start_row" 1 " (No clone data yet. Run [4] then [1])"
  fi

  # --- keys ---
  read -r -t 1 -n 1 key || true
  if [ "$key" = "q" ]; then
    exit 0
  elif [ "$key" = "x" ]; then
    # stop watchdog and exit dashboard
    bash bin/stop_watchdog.sh >/dev/null 2>&1 || true
    exit 0
  fi
done
