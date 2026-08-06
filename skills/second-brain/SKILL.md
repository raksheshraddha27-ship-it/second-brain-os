---
name: second-brain
description: >
  This is the main orchestrator for the Second Brain OS system. Use it when the user says
  "run my second brain", "sync my wiki", "check for new files", "what's new in my second brain",
  "second brain status", when this skill is invoked headlessly by a scheduled cron/launchd/Task
  Scheduler job (`claude -p "run the second-brain skill"`), or during a SessionStart catch-up
  check. It is the single entry point that decides whether to ingest, lint, or query, and
  delegates the actual work to the matching specialist subagent. Do not let the ingest, query,
  or lint skills do orchestration decisions themselves — that logic lives here.
metadata:
  version: "0.1.0"
---

# Second Brain Orchestrator

Coordinate the Second Brain OS system. This skill never writes to `raw/` or `wiki/` directly —
it inspects state, makes a routing decision, and delegates all actual content work to the
`wiki-ingest`, `wiki-lint`, or `wiki-query` subagents (via the Task tool) so each operation stays
isolated and auditable through `wiki/log.md`.

## Step 0: Load state

1. Look for `.secondbrain/config.json` in the current working directory (or ask the user which
   project folder to operate in if ambiguous). If it does not exist, tell the user no Second
   Brain has been set up here yet and direct them to the `init` skill. Stop.
2. Read `.secondbrain/config.json` for: `raw_folder`, `wiki_folder`, `lint_cadence_days`,
   `staleness_days`, `session_start_hook_enabled`.
3. Read `.secondbrain/ingested.json` for the list of already-ingested raw filenames (with hashes).
4. Read the last few entries of `<wiki_folder>/log.md` to know what happened most recently
   (last ingest, last lint timestamp).
5. Count files in `<wiki_folder>/review/pending/` - this is the outstanding human-review backlog,
   and gets mentioned in every summary this skill produces (Steps 2, 3, 5) so it's never silently
   forgotten between sessions.

## Step 1: Determine the trigger mode

- **Explicit user question** (anything that reads as "what does my wiki know about X", "ask my
  second brain...") → go straight to Query (Step 4).
- **Explicit lint request** ("health check", "run lint", "find stale nodes") → go straight to
  Lint (Step 3).
- **Review request** ("what needs my review", "show pending reviews", "resolve X") → go straight
  to Review (Step 5).
- **Sync/cron/SessionStart-triggered run, or an explicit "check for new files"/"sync" request**
  → do the full Sync routine (Step 2).
- If genuinely ambiguous, ask the user briefly which they want.

## Step 2: Sync routine (cron / manual sync)

1. List all files in `raw_folder` (recursively, skip hidden/system files).
2. Diff against `.secondbrain/ingested.json` to find files not yet ingested.
3. **Hard rule: never batch-ingest.** Even if multiple new files are found, ingest **exactly one
   file per sync cycle** — the one with the oldest file modification time (deterministic, so
   nothing is skipped over repeated runs). Invoke the `ingest` skill (which delegates to the
   `wiki-ingest` subagent) with that single file path only. Do not pass a list of files to the
   ingest skill or subagent under any circumstance, and do not loop over multiple files within
   this same invocation — one sync cycle processes at most one new source.
4. If more unprocessed files remain after this one completes, write a note to `log.md` stating
   how many are still queued (e.g. `3 more file(s) pending — will be processed on subsequent
   sync runs`) so the schedule naturally works through the backlog one run at a time.
5. After the single ingestion (if any) completes, check whether lint is due: compare today's date
   to the last `lint` entry timestamp in `log.md` against `lint_cadence_days`. If due (or no lint
   has ever run and `lint_cadence_days` is set), invoke the `lint` skill.
6. Report a short summary: what was ingested (if anything), how many files remain queued, whether
   lint ran, and the current `wiki/review/pending/` count (e.g. "3 items awaiting your review -
   say 'show pending reviews' to see them").

## Step 3: Lint

Invoke the `lint` skill directly (it delegates to the `wiki-lint` subagent). Relay its findings
(now filed in `wiki/review/pending/`) to the user; do not apply any fixes yourself beyond what
`wiki-lint` already handled for archiving.

## Step 4: Query

Invoke the `query` skill directly (it delegates to the `wiki-query` subagent) with the user's
question. Relay the synthesized, cited answer back to the user.

## Step 5: Review

Invoke the `review` skill directly to list or resolve items in `wiki/review/pending/`.

## Notes for headless/cron invocations

When invoked via `claude -p` with no interactive user present (see the `schedule-setup` skill),
always run the Sync routine (Step 2) and write all output to `log.md` rather than expecting a
human to read the terminal reply. Never ask clarifying questions in this mode — make the
conservative choice (e.g. skip lint if `lint_cadence_days` isn't configured, per the user's setup
answer) and log why. Any new review findings still get written to `wiki/review/pending/` as
normal - that's precisely the mechanism that lets a headless run's findings survive until a human
is back in an interactive session (surfaced again via the SessionStart hook, if enabled).
