import re
import json
import time
import os
import sys

# Adjust these paths to match your coordinator's data directory
LOG_FILE = os.path.expanduser("~/.walletwasabi/coordinator/Logs.txt")
HISTORY_FILE = os.path.expanduser("~/.walletwasabi/coordinator/coinjoin-history.json")

PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}).*Successfully broadcast the coinjoin: ([a-f0-9]{64})\."
)

POLL_INTERVAL = 10


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_history(entries):
    with open(HISTORY_FILE, "w") as f:
        json.dump(entries, f)


def scan_log(known_txids, entries):
    if not os.path.exists(LOG_FILE):
        return
    with open(LOG_FILE, "r") as f:
        for line in f:
            m = PATTERN.match(line)
            if m:
                timestamp, txid = m.group(1), m.group(2)
                if txid not in known_txids:
                    entries.append({"timestamp": timestamp, "txid": txid})
                    known_txids.add(txid)
                    save_history(entries)
                    print(f"New coinjoin: {txid}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        LOG_FILE = sys.argv[1]
        HISTORY_FILE = sys.argv[2]

    print(f"Log file: {LOG_FILE}")
    print(f"History file: {HISTORY_FILE}")
    print("Watching for coinjoins...")

    entries = load_history()
    known = {e["txid"] for e in entries}

    scan_log(known, entries)
    while True:
        time.sleep(POLL_INTERVAL)
        scan_log(known, entries)
