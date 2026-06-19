#!/usr/bin/env python3
"""Scheduler for tidpl — runs `tidpl run` on a schedule using marker files."""

import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
MARKER = DATA_DIR / ".last_run"
LOG_FILE = DATA_DIR / "scheduler.log"

INTERVAL_DAYS = 2
SLEEP_HOURS = 6


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def should_run() -> bool:
    if not MARKER.exists():
        return True
    try:
        last = float(MARKER.read_text().strip())
        elapsed = (time.time() - last) / 86400
        if elapsed < INTERVAL_DAYS:
            log(f"Skipping ({elapsed:.1f}d < {INTERVAL_DAYS}d)")
            return False
    except Exception:
        pass
    return True


def run_tidpl():
    log("=== Starting tidpl run ===")
    venv_python = HERE / ".venv" / "bin" / "python3"
    result = subprocess.run(
        [str(venv_python), "-m", "tidpl.cli", "run"],
        cwd=HERE,
        capture_output=False,
        text=True,
    )
    if result.returncode == 0:
        MARKER.write_text(str(time.time()))
        log("=== Done ===")
    else:
        log(f"FAILED (exit {result.returncode})")


def main():
    log("Scheduler started")
    while True:
        try:
            if should_run():
                run_tidpl()
        except Exception as e:
            log(f"Error: {e}")

        log(f"Waiting {SLEEP_HOURS}h before next check...")
        time.sleep(SLEEP_HOURS * 3600)


if __name__ == "__main__":
    main()
