import curses
import threading
import time
import json
import platform

from core.packages import get_packages_by_prefix
from core.auto_rejoin import auto_rejoin_loop
from core.state import init as init_state   # <-- ADD STATE


# ===== LOAD CONFIG =====
with open("config/config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

ENV = config.get("env", "android")  # "pc" hoặc "android"

auto_running = False
auto_thread = None


def safe(callable_fn):
    """Run curses function safely (Windows-proof)."""
    try:
        callable_fn()
    except curses.error:
        pass


def main(stdscr):
    global auto_running, auto_thread

    # ===== BASIC CURSES INIT =====
    curses.noecho()
    curses.cbreak()
    safe(lambda: stdscr.keypad(True))

    # ===== HIDE CURSOR =====
    if ENV != "pc" and platform.system() != "Windows":
        safe(lambda: curses.curs_set(0))

    h, w = stdscr.getmaxyx()

    # ===== STATIC UI =====
    stdscr.clear()
    stdscr.box()
    safe(lambda: stdscr.addstr(1, 2, "AUTO TOOL V5 - ZAM STYLE"))
    safe(lambda: stdscr.hline(2, 1, "-", w - 2))

    safe(lambda: stdscr.addstr(3, 2, "[1] Start Auto Rejoin"))
    safe(lambda: stdscr.addstr(4, 2, "[2] Scan Packages"))

    if ENV != "pc":
        safe(lambda: stdscr.addstr(5, 2, "[3] Set GameID (CLI)"))
        safe(lambda: stdscr.addstr(6, 2, "[4] Detect UserID (CLI)"))
        safe(lambda: stdscr.addstr(7, 2, "[5] Other Tools"))
        exit_line = 8
    else:
        safe(lambda: stdscr.addstr(5, 2, "[3] Set GameID (Android only)"))
        safe(lambda: stdscr.addstr(6, 2, "[4] Detect UserID (Android only)"))
        exit_line = 7

    safe(lambda: stdscr.addstr(exit_line, 2, "[0] Exit"))
    safe(lambda: stdscr.hline(exit_line + 1, 1, "-", w - 2))

    # ===== LOG WINDOW =====
    log_h = max(3, h - 8)
    logw = curses.newwin(log_h, w - 4, 7, 2)

    safe(lambda: logw.scrollok(True))
    safe(lambda: logw.idlok(True))

    safe(lambda: logw.addstr("LOG:\n"))
    safe(lambda: logw.refresh())
    safe(lambda: stdscr.refresh())

    stdscr.timeout(500)

    # ===== LOGGER =====
    def logger(msg: str):
        safe(lambda: logw.addstr(msg + "\n"))
        safe(lambda: logw.refresh())

    # ===== AUTO THREAD =====
    def auto_worker():
        logger("[AUTO] Auto Rejoin started")
        auto_rejoin_loop(logger)

    # ===== EVENT LOOP =====
    while True:
        key = stdscr.getch()

        if key == ord('1') and not auto_running:
            auto_running = True

            # ===== INIT STATE =====
            pkgs = list(config.get("packages", {}).keys())
            init_state(pkgs)
            logger("[STATE] Init state")

            auto_thread = threading.Thread(
                target=auto_worker,
                daemon=True
            )
            auto_thread.start()
            logger("[UI] Start Auto Rejoin")

        elif key == ord('2'):
            pkgs = get_packages_by_prefix()
            logger("[SCAN] Found packages:")
            for p in pkgs:
                logger(f"  - {p}")

        elif key == ord('0'):
            logger("[UI] Exit")
            break

        time.sleep(0.05)


if __name__ == "__main__":
    curses.wrapper(main)
