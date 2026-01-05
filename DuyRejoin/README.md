# DuyRejoin Phase 0

This repository contains the initial Termux tooling for the DuyRejoin project. Phase 0 focuses on bootstrapping the environment, collecting runtime snapshots, and syncing the repo to the Download directory.

## Constants (examples)
- `EXAMPLE_PACKAGE="com.zamdepzai.clienv"`
- `SPLASH_ACTIVITY="com.roblox.client.startup.ActivitySplash"`
- `INGAME_ACTIVITY="com.roblox.client.ActivityNativeMain"`
- `DEFAULT_PLACE_ID="1537690962"`
- `DOWNLOAD_DST="/sdcard/Download/DuyRejoin"`
- `REPO_SRC="$HOME/DuyRejoin-src"`

## Bootstrap Termux
Run once to install dependencies and prepare directories:

```sh
cd "$HOME/DuyRejoin"
sh scripts/bootstrap_termux.sh
```

## Run the collector (20 loops example)
The collector emits one JSON line per loop with process, activity, and network status. Pass the target package as the first argument and control the loop count and interval with environment variables (defaults: infinite loops, 3s interval).

```sh
cd "$HOME/DuyRejoin"
LOOPS=20 INTERVAL=3 sh app/core/collector.sh com.zamdepzai.clienv
```

## Deploy to Download and run from there
Sync the repo to the Download directory (excluding runtime data and logs) and run scripts from the deployed copy:

```sh
cd "$HOME/DuyRejoin"
sh scripts/deploy_to_download.sh
cd /sdcard/Download/DuyRejoin
sh app/core/collector.sh com.zamdepzai.clienv
```
