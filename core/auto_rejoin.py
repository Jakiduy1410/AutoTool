import time
import json
from core.process import is_running, force_stop, start_app
from core.gameid import get_game_uri
from core.state import set_state

CONFIG = "config/config.json"

LAUNCH_DELAY = 35
STABLE_CHECK = 5


def load_config():
    with open(CONFIG) as f:
        return json.load(f)


def wait_until_stable(pkg):
    stable = 0
    while stable < STABLE_CHECK:
        if is_running(pkg):
            stable += 1
        else:
            stable = 0
        time.sleep(1)


def auto_rejoin_loop(logger):
    cfg = load_config()

    while True:
        for pkg in cfg["packages"]:
            uri = get_game_uri(pkg)
            if not uri:
                continue

            if not is_running(pkg):
                set_state(pkg, "DEAD")
                logger(f"[AUTO] {pkg} is not running")

                set_state(pkg, "RESTARTING")
                logger(f"[STATE] {get_state()}")
                logger(f"[AUTO] Launching {pkg}")

                force_stop(pkg)
                start_app(pkg, uri)

                set_state(pkg, "WAITING")
                logger(f"[AUTO] Waiting {pkg} to stabilize...")
                wait_until_stable(pkg)

                set_state(pkg, "COOLDOWN")
                logger(f"[AUTO] {pkg} stable, cooldown...")
                time.sleep(LAUNCH_DELAY)
            else:
                set_state(pkg, "RUNNING")

        time.sleep(cfg["interval"])
