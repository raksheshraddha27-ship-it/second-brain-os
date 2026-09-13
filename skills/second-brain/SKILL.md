---
name: second-brain
description: >
  Route Second Brain requests to setup, one-file sync, ingest, query, lint, or review. Use for
  "sync my wiki", "run my second brain", status requests, or requests that do not clearly name
  one specialist operation. Works in Codex and Claude Code without scheduled/background runs.
metadata:
  version: "0.3.0"
---

# Second Brain Orchestrator

Read `.secondbrain/config.json`, `.secondbrain/ingested.json`, the latest `wiki/log.md` entries,
and the pending-review count. If config is missing, route to `init`.

Route explicit questions to `query`, lint requests to `lint`, review requests to `review`, and
named source requests to `ingest`. Explicit regular/deep wording overrides the configured ingest
mode for that invocation.

## Manual sync

1. Recursively list non-hidden files in `raw_folder` and compare path plus content hash with
   `.secondbrain/ingested.json`.
2. If files are waiting, invoke `ingest` for exactly one: the oldest modification time. Never
   loop or batch. Report how many remain for later syncs.
3. If `automatic_lint_enabled=true`, invoke one resumable lint batch after successful ingest.
   Otherwise ask `Run lint now?` in interactive use and wait for explicit approval.
4. Report the ingested source, remaining queue, lint status, and pending-review count.

There is intentionally no scheduler or background execution. Every sync begins with an explicit
user request.
