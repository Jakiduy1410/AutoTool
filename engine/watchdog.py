#!/usr/bin/env python3
import json, os, time, subprocess, traceback, glob
from datetime import datetime

BASE          = "/sdcard/Download/AutoTool"
ENGINE_CFG    = f"{BASE}/config/engine.json"
GLOBAL_CFG    = f"{BASE}/config/global.json"
USERMAP_CFG   = f"{BASE}/config/user_map.json"
CODEX_WS      = "/storage/emulated/0/Codex/Workspace"
MAIN_MAX_AGE  = 5  # giây — file .main được ghi mỗi 1s, >5s = executor chết

# ─────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────

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

# ─────────────────────────────────────────────
# PID detection (root)
# ─────────────────────────────────────────────

def get_pid(package: str):
    out = sh(f"pidof {package}", root=True)
    if out and not out.startswith("__ERR__"):
        try:
            return int(out.split()[0])
        except Exception:
            pass
    out = sh(f"ps -A | grep -F ' {package}' || true", root=True)
    if not out:
        return None
    for line in out.splitlines():
        for tok in line.split():
            if tok.isdigit():
                return int(tok)
    return None

def is_package_resumed(package: str) -> bool:
    out = sh("dumpsys activity activities | grep -m 1 'mResumedActivity' || true", root=True)
    return package in out

# ─────────────────────────────────────────────
# Executor alive check via .main file
# ─────────────────────────────────────────────

def is_executor_alive(user_id: str) -> tuple:
    """
    executor_check.lua ghi <UserId>.main mỗi 1 giây.
    mtime <= 5s  →  executor đang chạy = in-game.
    Trả về (alive: bool, age_sec: float)
    """
    fpath = os.path.join(CODEX_WS, f"{user_id}.main")
    try:
        age = time.time() - os.path.getmtime(fpath)
        return age <= MAIN_MAX_AGE, round(age, 1)
    except FileNotFoundError:
        return False, -1

# ─────────────────────────────────────────────
# User map load (mapping được tạo bởi discover_usermap.sh)
# ─────────────────────────────────────────────

def load_user_map() -> dict:
    return load_json(USERMAP_CFG, {})

# ─────────────────────────────────────────────
# App control
# ─────────────────────────────────────────────

def start_app(package: str):
    return sh(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", root=True)

def stop_app(package: str):
    return sh(f"am force-stop {package}", root=True)

def join_game(package: str, join_url: str, fallback_url: str):
    """Bắn intent join, dừng sớm khi app đã foreground."""
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
        if is_package_resumed(package):
            break

def start_and_join(package: str, grace_sec: int, join_url: str, fallback_url: str):
    stop_app(package)
    start_app(package)
    time.sleep(max(1, grace_sec))
    join_game(package, join_url, fallback_url)

def restart_and_join(package: str, grace_sec: int, join_url: str, fallback_url: str):
    stop_app(package)
    time.sleep(1)
    start_app(package)
    time.sleep(max(1, grace_sec))
    join_game(package, join_url, fallback_url)

# ─────────────────────────────────────────────
# Clone state
# ─────────────────────────────────────────────

def clone_state_path(state_dir: str, package: str) -> str:
    return os.path.join(state_dir, "clones", f"{package.replace('/', '_')}.json")

def load_clone_state(state_dir: str, package: str) -> dict:
    path = clone_state_path(state_dir, package)
    d = load_json(path, {})
    if not d:
        d = {
            "package":        package,
            "user_id":        "",
            "last_pid":       None,
            "status":         "INIT",
            "cooldown_until": 0,
            "last_action":    "",
            "restart_count":  0,
            "last_seen":      0,
            "loading_since":  0,
        }
        write_json(path, d)
    return d

def save_clone_state(state_dir: str, package: str, d: dict):
    write_json(clone_state_path(state_dir, package), d)

# ─────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────

def main():
    eng = load_json(ENGINE_CFG, {})
    glb = load_json(GLOBAL_CFG, {})

    interval      = int(eng.get("interval_sec", 5))
    cooldown_sec  = int(eng.get("cooldown_sec", 30))
    grace         = int(eng.get("start_grace_sec", 10))
    clone_delay   = int(eng.get("clone_start_delay_sec", 15))
    log_file      = eng.get("log_file",      f"{BASE}/logs/watchdog.log")
    packages_file = eng.get("packages_file", f"{BASE}/config/packages.json")
    state_dir     = eng.get("state_dir",     f"{BASE}/runtime")
    join_url      = (glb.get("join_url")     or "").strip()
    fallback_url  = (glb.get("fallback_url") or "").strip()

    os.makedirs(os.path.join(state_dir, "clones"), exist_ok=True)
    log(f"WATCHDOG_START interval={interval}s cooldown={cooldown_sec}s grace={grace}s clone_delay={clone_delay}s", log_file)

    # Load mapping package → UserId (tạo sẵn bởi discover_usermap.sh)
    user_map = load_user_map()
    if not user_map:
        log("WARNING: user_map.json trống! Chạy workflow [5] Discover UserMap trước.", log_file)

    while True:
        try:
            packs = load_json(packages_file, {"packages": []}).get("packages", [])
            ts    = now_ts()

            snapshot = {
                "time":     now_str(),
                "net":      "OK" if net_ok() else "DOWN",
                "packages": []
            }

            for i, pkg in enumerate(packs):
                pid     = get_pid(pkg)
                st      = load_clone_state(state_dir, pkg)
                ts      = now_ts()

                user_id = user_map.get(pkg, st.get("user_id", ""))
                st["user_id"] = user_id

                # Check executor alive
                executor_alive, main_age = (False, -1)
                if user_id:
                    executor_alive, main_age = is_executor_alive(user_id)

                action = "NONE"
                reason = ""

                if ts < int(st.get("cooldown_until", 0)):
                    # Đang cooldown, chờ thôi
                    st["status"] = "COOLDOWN"
                    reason = f"cooldown {int(st['cooldown_until']) - ts}s left"

                elif pid is None:
                    # App không có PID → cần khởi động
                    if st.get("last_pid") is not None:
                        st["status"] = "CRASHED"
                        reason = "pid_lost"
                        action = "RESTART+JOIN"
                        time.sleep(i * clone_delay)
                        restart_and_join(pkg, grace, join_url, fallback_url)
                        st["restart_count"]  = int(st.get("restart_count", 0)) + 1
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "RESTART"
                        st["loading_since"]  = ts
                    else:
                        st["status"] = "NOT_RUNNING"
                        reason = "pid_none"
                        action = "START+JOIN"
                        time.sleep(i * clone_delay)
                        start_and_join(pkg, grace, join_url, fallback_url)
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "START"
                        st["loading_since"]  = ts

                elif executor_alive:
                    # PID có + .main tươi = đang IN_GAME thực sự
                    st["status"]        = "IN_GAME"
                    st["loading_since"] = 0
                    reason = f"executor_alive age={main_age}s"

                else:
                    # PID có nhưng executor chưa inject / đã die / chưa có user_id
                    if not st.get("loading_since"):
                        st["loading_since"] = ts
                    waited = ts - st["loading_since"]
                    st["status"] = "LOADING"
                    if not user_id:
                        reason = f"pid_ok no_userid waited={waited}s (chạy menu [5])"
                    else:
                        reason = f"executor_dead waited={waited}s"

                    # Loading quá 2 phút → rejoin dù có user_id hay không
                    if waited > 120:
                        action = "REJOIN"
                        join_game(pkg, join_url, fallback_url)
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "REJOIN"
                        st["loading_since"]  = ts

                st["last_seen"] = ts
                st["last_pid"]  = pid
                save_clone_state(state_dir, pkg, st)

                snapshot["packages"].append({
                    "package":        pkg,
                    "user_id":        user_id,
                    "pid":            pid,
                    "status":         st["status"],
                    "executor_alive": executor_alive,
                    "main_age_sec":   main_age,
                    "cooldown_until": st.get("cooldown_until", 0),
                    "restart_count":  st.get("restart_count", 0),
                    "last_action":    st.get("last_action", ""),
                })

                if action != "NONE":
                    log(f"[{pkg}] ({user_id}) {st['status']} reason={reason} action={action}", log_file)

            write_json(os.path.join(state_dir, "watchdog_state.json"), snapshot)

        except Exception as e:
            log("EXCEPTION " + repr(e), log_file)
            log(traceback.format_exc().strip(), log_file)

        time.sleep(max(5, interval))

if __name__ == "__main__":
    main()
