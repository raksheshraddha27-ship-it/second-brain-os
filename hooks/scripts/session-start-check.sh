#!/usr/bin/env bash
# Second Brain OS - SessionStart check.
# No-ops unless the user opted into this via schedule-setup
# ("session_start_hook_enabled": true in .secondbrain/config.json).
# Prints short context notes if (a) a scheduled sync appears to have been
# missed, and/or (b) there are items waiting in wiki/review/pending/. It does
# NOT run the sync or resolve anything itself - it just nudges Claude to
# consider invoking the second-brain / review skills this session, which
# matters most for headless/cron-driven syncs where nobody was watching when
# findings got filed.

set -euo pipefail

CONFIG=".secondbrain/config.json"
LOG="wiki/log.md"
REVIEW_PENDING="wiki/review/pending"

if [ ! -f "$CONFIG" ]; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  # No python3 available - silently skip rather than failing the session start.
  exit 0
fi

python3 - "$CONFIG" "$LOG" "$REVIEW_PENDING" <<'PYEOF'
import json, sys, os, re
from datetime import datetime, timezone

config_path, log_path, review_pending_dir = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(config_path) as f:
        config = json.load(f)
except Exception:
    sys.exit(0)

if not config.get("session_start_hook_enabled"):
    sys.exit(0)

lint_cadence = config.get("lint_cadence_days")
# Default expectation: if a sync cadence was configured for scheduling, treat
# more than ~1.5x that many days of silence in log.md as "likely missed".
threshold_days = lint_cadence if lint_cadence else 2

last_date = None
if os.path.exists(log_path):
    with open(log_path) as f:
        content = f.read()
    dates = re.findall(r"##\s*\[(\d{4}-\d{2}-\d{2})\]", content)
    if dates:
        last_date = max(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc) for d in dates)

if last_date is None:
    print("Second Brain OS: no ingest/lint history found yet in wiki/log.md.")
else:
    days_since = (datetime.now(timezone.utc) - last_date).days
    if days_since >= threshold_days:
        print(f"Second Brain OS: it has been {days_since} day(s) since the last logged sync "
              f"(threshold: {threshold_days}). A scheduled run may have been missed - consider "
              f"invoking the second-brain skill to catch up this session.")

# Surface the review backlog independently of sync status - a headless run
# may have flagged something with nobody around to see it.
if os.path.isdir(review_pending_dir):
    pending = [f for f in os.listdir(review_pending_dir) if f.endswith(".md")]
    if pending:
        print(f"Second Brain OS: {len(pending)} item(s) waiting in the review queue "
              f"(wiki/review/pending/) from prior ingest/lint runs - say 'show pending reviews' "
              f"to see them.")
PYEOF
