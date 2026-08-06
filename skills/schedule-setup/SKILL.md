---
name: schedule-setup
description: >
  This skill should be used when the user wants to "set up automatic ingestion", "schedule my
  second brain", "make my wiki update automatically", or "run this on a schedule". Configures
  OS-level scheduling so the Second Brain syncs without the user manually opening Claude Code.
metadata:
  version: "0.1.0"
---

# Set Up Automatic Scheduling

## Important limitation to state up front

Claude Code plugins have **no built-in cron or background scheduler** - there is no "run every N
hours" primitive inside the plugin itself. Tell the user this plainly before proceeding: what
you're about to set up is an **OS-level** scheduled job (cron, launchd, or Windows Task
Scheduler) that runs outside Claude Code and calls `claude -p` in headless mode at the chosen
cadence. This is automatic once installed, but it depends on the OS scheduler firing (the machine
must be on; a laptop asleep at the scheduled time will simply miss that run and catch up at the
next one).

## Steps

1. Confirm `.secondbrain/config.json` exists (if not, direct the user to `init` first).
2. Ask the user their desired cadence (e.g. every hour, daily at a specific time, every 6 hours).
3. Detect the OS via `uname` (bash) or equivalent. Determine the working directory to run from
   (the project root containing `.secondbrain/`, `raw/`, and `wiki/`).
4. Build the headless command:
   `claude -p "Use the second-brain skill to sync" --cwd <project root>`
   (adjust flags to whatever the installed Claude Code CLI actually supports - confirm with
   `claude --help` if unsure of exact non-interactive flags).
5. Install the scheduler entry automatically (do this yourself via Bash - do not just print
   instructions for the user to run manually):
   - **macOS**: prefer a `launchd` plist in `~/Library/LaunchAgents/` (survives reboots more
     reliably than cron on macOS), e.g.
     `com.secondbrain.<project-slug>.plist` with `StartInterval` or `StartCalendarInterval`
     matching the chosen cadence, then `launchctl load` it.
   - **Linux**: add a line to the user's crontab via `crontab -l` + append + `crontab -` , using
     standard cron syntax for the cadence.
   - **Windows**: use `schtasks /create` with `/sc` set to the matching schedule type
     (MINUTE/HOURLY/DAILY) and `/tr` set to the headless command.
6. Ask whether they also want the **SessionStart fallback hook** enabled (this catches up on a
   sync that was missed because the OS scheduler didn't fire, by checking elapsed time whenever a
   Claude Code session starts in this project). This is opt-in - do not enable it by default.
   If yes, set `"session_start_hook_enabled": true` in `.secondbrain/config.json` (the hook
   itself is always present in the plugin's `hooks/hooks.json`, but no-ops unless this flag is
   true).
7. Confirm what was installed (show the exact cron line / plist / schtasks command used) and how
   to remove it later (`crontab -e` and delete the line / `launchctl unload` + delete the plist /
   `schtasks /delete`).
8. Remind the user that each scheduled run processes at most one new raw file (per the
   `second-brain` orchestrator's one-file-at-a-time rule) - a backlog of many files will drain
   down gradually across multiple scheduled runs, by design, not all at once.
