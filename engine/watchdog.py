#!/usr/bin/env python3
import json, os, time, subprocess, traceback, glob
from datetime import datetime

BASE         = "/sdcard/Download/AutoTool"
ENGINE_CFG   = f"{BASE}/config/engine.json"
GLOBAL_CFG   = f"{BASE}/config/global.json"
USERMAP_CFG  = f"{BASE}/config/user_map.json"

# Thư mục Codex workspace — nơi executor_check.lua ghi file <UserId>.main
CODEX_WORKSPACE = "/sdcard/Codex/Workspace"

# File .main được ghi mỗi 1 giây → nếu mtime > ngưỡng này = executor đã chết
MAIN_FILE_MAX_AGE = 5

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
        parts = line.split()
        for tok in parts:
            if tok.isdigit():
                return int(tok)
    return None

def resumed_activity_root() -> str:
    return sh("dumpsys activity activities | grep -m 1 'mResumedActivity' || true", root=True)

def is_package_resumed(package: str) -> bool:
    return package in resumed_activity_root()

# ─────────────────────────────────────────────
# Executor check via .main file
# ─────────────────────────────────────────────

def main_file_path(user_id: str) -> str:
    return os.path.join(CODEX_WORKSPACE, f"{user_id}.main")

def is_executor_alive(user_id: str) -> tuple:
    """
    Check executor còn sống không dựa trên mtime của <UserId>.main.
    executor_check.lua ghi file này mỗi 1 giây khi đang in-game.
    Trả về (alive: bool, age_sec: float)
    """
    fpath = main_file_path(user_id)
    try:
        mtime = os.path.getmtime(fpath)
        age   = time.time() - mtime
        return age <= MAIN_FILE_MAX_AGE, age
    except FileNotFoundError:
        return False, -1

# ─────────────────────────────────────────────
# User map: package -> UserId (discover tự động)
# ─────────────────────────────────────────────

def load_user_map() -> dict:
    return load_json(USERMAP_CFG, {})

def save_user_map(user_map: dict):
    write_json(USERMAP_CFG, user_map)

def discover_userid(package: str, grace_sec: int, log_file: str) -> str:
    """
    Mở clone, chờ executor inject, tìm file .main nào mới xuất hiện.
    Trả về UserId (string) hoặc "" nếu không tìm được.
    Chỉ chạy một lần cho mỗi package chưa có UserId.
    """
    log(f"[DISCOVER] Bắt đầu discover UserId cho {package}", log_file)

    # Snapshot file .main đang có TRƯỚC khi mở
    existing = set(glob.glob(os.path.join(CODEX_WORKSPACE, "*.main")))
    ts_before = time.time()

    stop_app(package)
    start_app(package)

    wait_sec = max(grace_sec, 20)
    log(f"[DISCOVER] Chờ {wait_sec}s cho executor inject...", log_file)
    time.sleep(wait_sec)

    # Tìm file .main mới xuất hiện
    now_files = set(glob.glob(os.path.join(CODEX_WORKSPACE, "*.main")))
    new_files = now_files - existing

    if not new_files:
        # Không có file mới → tìm file nào vừa được update trong khoảng chờ
        candidates = []
        for fpath in now_files:
            try:
                age = time.time() - os.path.getmtime(fpath)
                if age <= wait_sec + 5:
                    candidates.append((age, fpath))
            except Exception:
                pass
        if candidates:
            candidates.sort()
            new_files = {candidates[0][1]}

    if not new_files:
        log(f"[DISCOVER] Không tìm thấy .main file mới cho {package}", log_file)
        return ""

    fpath   = list(new_files)[0]
    user_id = os.path.basename(fpath).replace(".main", "")
    log(f"[DISCOVER] OK: {package} → UserId={user_id}", log_file)
    return user_id

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

# ─────────────────────────────────────────────
# Clone state
# ─────────────────────────────────────────────

def clone_state_path(state_dir: str, package: str) -> str:
    safe = package.replace("/", "_")
    return os.path.join(state_dir, "clones", f"{safe}.json")

def load_clone_state(state_dir: str, package: str):
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

def save_clone_state(state_dir: str, package: str, d):
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

    join_url     = (glb.get("join_url")     or "").strip()
    fallback_url = (glb.get("fallback_url") or "").strip()

    os.makedirs(os.path.join(state_dir, "clones"), exist_ok=True)
    log(f"WATCHDOG_START interval={interval}s cooldown={cooldown_sec}s grace={grace}s clone_delay={clone_delay}s", log_file)

    user_map = load_user_map()

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

                # UserId từ map hoặc state đã lưu
                user_id = user_map.get(pkg, st.get("user_id", ""))
                st["user_id"] = user_id

                # Check executor alive qua .main file
                executor_alive = False
                main_age       = -1
                if user_id:
                    executor_alive, main_age = is_executor_alive(user_id)

                action = "NONE"
                reason = ""

                if ts < int(st.get("cooldown_until", 0)):
                    st["status"] = "COOLDOWN"
                    reason = "cooldown"

                elif pid is None:
                    # App không chạy
                    if st.get("last_pid") is not None:
                        st["status"]         = "CRASHED"
                        reason               = "pid_lost"
                        action               = "RESTART+JOIN"
                        time.sleep(i * clone_delay)
                        restart_and_join(pkg, grace, join_url, fallback_url)
                        st["restart_count"]  = int(st.get("restart_count", 0)) + 1
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "RESTART"
                        st["loading_since"]  = ts
                    else:
                        st["status"]         = "NOT_RUNNING"
                        reason               = "pid_none"
                        action               = "START+JOIN"
                        time.sleep(i * clone_delay)
                        start_and_join(pkg, grace, join_url, fallback_url)
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "START"
                        st["loading_since"]  = ts

                        # Discover UserId nếu chưa có
                        if not user_id:
                            found = discover_userid(pkg, grace, log_file)
                            if found:
                                user_map[pkg] = found
                                save_user_map(user_map)
                                st["user_id"] = found
                                user_id = found

                elif executor_alive:
                    # PID có + .main tươi = executor inject OK = đang IN_GAME
                    st["status"]        = "IN_GAME"
                    st["loading_since"] = 0
                    reason              = f"executor_alive age={main_age:.1f}s"

                elif user_id:
                    # PID có nhưng .main cũ/không có = app mở nhưng executor chưa/đã die
                    loading_since = st.get("loading_since") or ts
                    if not st.get("loading_since"):
                        st["loading_since"] = ts

                    waited       = ts - loading_since
                    st["status"] = "LOADING"
                    reason       = f"pid_ok executor_dead waited={waited}s"

                    # Loading quá 2 phút → rejoin
                    if waited > 120:
                        action               = "REJOIN"
                        join_game(pkg, join_url, fallback_url)
                        st["cooldown_until"] = ts + cooldown_sec
                        st["last_action"]    = "REJOIN"
                        st["loading_since"]  = ts

                else:
                    # PID có nhưng chưa discover được UserId
                    st["status"] = "RUNNING"
                    reason       = "pid_ok no_userid_yet"

                st["last_seen"] = ts
                st["last_pid"]  = pid
                save_clone_state(state_dir, pkg, st)

                snapshot["packages"].append({
                    "package":        pkg,
                    "user_id":        user_id,
                    "pid":            pid,
                    "status":         st["status"],
                    "executor_alive": executor_alive,
                    "main_age_sec":   round(main_age, 1),
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
