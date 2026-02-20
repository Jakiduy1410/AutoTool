#!/usr/bin/env python3
import json, os, time, subprocess, traceback
from datetime import datetime

BASE = "/sdcard/Download/AutoTool"
ENGINE_CFG = f"{BASE}/config/engine.json"
GLOBAL_CFG = f"{BASE}/config/global.json"

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def now_ts():
    return int(time.time())

def sh(cmd: str, root: bool = False) -> str:
    try:
        if root:
            cmd = f"su -c \"{cmd}\""
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except Exception as e:
        return f"__ERR__ {e}"

def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def log(line: str, log_file: str):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{now_str()}] {line}\n")

def net_ok() -> bool:
    out = sh("ping -c 1 -W 1 1.1.1.1 >/dev/null 2>&1; echo $?")
    return out.strip() == "0"

def get_pid(package: str):
    # Dùng root vì process của clone app không visible với user thường
    out = sh(f"pidof {package}", root=True)
    if out and not out.startswith("__ERR__"):
        try:
            return int(out.split()[0])
        except Exception:
            pass
    out = sh(f"ps -A | grep -F ' {package}' || true", root=True)
    if not out:
        return None
    line = out.splitlines()[0].split()
    for tok in line:
        if tok.isdigit():
            return int(tok)
    return None

def resumed_activity_root() -> str:
    return sh("dumpsys activity activities | grep -m 1 'mResumedActivity' || true", root=True)

def clone_state_path(state_dir: str, package: str) -> str:
    safe = package.replace("/", "_")
    return os.path.join(state_dir, "clones", f"{safe}.json")

def load_clone_state(state_dir: str, package: str):
    path = clone_state_path(state_dir, package)
    d = load_json(path, {})
    if not d:
        d = {
            "package": package,
            "last_pid": None,
            "status": "INIT",
            "cooldown_until": 0,
            "last_action": "",
            "restart_count": 0,
            "last_seen": 0
        }
        write_json(path, d)
    return d

def save_clone_state(state_dir: str, package: str, d):
    write_json(clone_state_path(state_dir, package), d)

def start_app(package: str):
    return sh(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", root=True)

def stop_app(package: str):
    return sh(f"am force-stop {package}", root=True)

def is_package_resumed(package: str) -> bool:
    """Kiểm tra xem package có đang ở foreground không."""
    resumed = resumed_activity_root()
    return package in resumed

def join_game(package: str, join_url: str, fallback_url: str):
    """
    Bắn intent join theo thứ tự ưu tiên, dừng ngay khi app đã foreground.
    Tránh spam 4 intent liên tiếp gây crash/kick.
    """
    attempts = [
        (join_url,     f"am start -a android.intent.action.VIEW -d '{join_url}' {package}"),
        (join_url,     f"am start -a android.intent.action.VIEW -d '{join_url}' -p '{package}'"),
        (fallback_url, f"am start -a android.intent.action.VIEW -d '{fallback_url}' {package}"),
        (fallback_url, f"am start -a android.intent.action.VIEW -d '{fallback_url}' -p '{package}'"),
    ]

    for url, cmd in attempts:
        if not url:
            continue
        sh(cmd, root=True)
        time.sleep(2)
        # Nếu app đã foreground thì không cần bắn thêm
        if is_package_resumed(package):
            break

    return "OK"

def start_and_join(package: str, grace_sec: int, join_url: str, fallback_url: str):
    stop_app(package)
    start_app(package)
    time.sleep(max(1, grace_sec))
    join_game(package, join_url, fallback_url)
    return "OK"

def restart_and_join(package: str, grace_sec: int, join_url: str, fallback_url: str):
    stop_app(package)
    time.sleep(1)
    start_app(package)
    time.sleep(max(1, grace_sec))
    join_game(package, join_url, fallback_url)
    return "OK"

def main():
    eng = load_json(ENGINE_CFG, {})
    glb = load_json(GLOBAL_CFG, {})

    interval = int(eng.get("interval_sec", 5))
    cooldown_sec = int(eng.get("cooldown_sec", 30))
    grace = int(eng.get("start_grace_sec", 10))
    log_file = eng.get("log_file", f"{BASE}/logs/watchdog.log")
    packages_file = eng.get("packages_file", f"{BASE}/config/packages.json")
    state_dir = eng.get("state_dir", f"{BASE}/runtime")

    join_url = (glb.get("join_url") or "").strip()
    fallback_url = (glb.get("fallback_url") or "").strip()

    os.makedirs(os.path.join(state_dir, "clones"), exist_ok=True)
    log(f"WATCHDOG_START interval={interval}s cooldown={cooldown_sec}s grace={grace}s join={'YES' if (join_url or fallback_url) else 'NO'}", log_file)

    while True:
        try:
            packs = load_json(packages_file, {"packages": []}).get("packages", [])
            ok = net_ok()
            resumed = resumed_activity_root()
            ts = now_ts()

            snapshot = {
                "time": now_str(),
                "net": "OK" if ok else "DOWN",
                "resumed": resumed,
                "packages": []
            }

            for pkg in packs:
                pid = get_pid(pkg)
                st = load_clone_state(state_dir, pkg)

                action = "NONE"
                reason = ""

                if ts < int(st.get("cooldown_until", 0)):
                    st["status"] = "COOLDOWN"
                    reason = "cooldown"
                else:
                    if pid is None:
                        if st.get("last_pid") is not None:
                            st["status"] = "CRASHED"
                            reason = "pid_lost"
                            action = "RESTART+JOIN"
                            restart_and_join(pkg, grace, join_url, fallback_url)
                            st["restart_count"] = int(st.get("restart_count", 0)) + 1
                            st["cooldown_until"] = ts + cooldown_sec
                            st["last_action"] = "RESTART"
                        else:
                            st["status"] = "NOT_RUNNING"
                            reason = "pid_none"
                            action = "START+JOIN"
                            start_and_join(pkg, grace, join_url, fallback_url)
                            st["cooldown_until"] = ts + cooldown_sec
                            st["last_action"] = "START"
                    else:
                        st["status"] = "RUNNING"
                        reason = "pid_ok"

                st["last_seen"] = ts
                st["last_pid"] = pid
                save_clone_state(state_dir, pkg, st)

                snapshot["packages"].append({
                    "package": pkg,
                    "pid": pid,
                    "status": st["status"],
                    "cooldown_until": st.get("cooldown_until", 0),
                    "restart_count": st.get("restart_count", 0),
                    "last_action": st.get("last_action", "")
                })

                if action != "NONE":
                    log(f"[{pkg}] {st['status']} reason={reason} action={action}", log_file)

            write_json(os.path.join(state_dir, "watchdog_state.json"), snapshot)

        except Exception as e:
            log("EXCEPTION " + repr(e), log_file)
            log(traceback.format_exc().strip(), log_file)

        time.sleep(max(5, interval))

if __name__ == "__main__":
    main()
