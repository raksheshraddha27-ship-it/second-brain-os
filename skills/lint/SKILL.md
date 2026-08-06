---
name: lint
description: >
  This skill should be used when the user asks to "run a lint on my wiki", "health check my
  second brain", "check for stale nodes", "find contradictions in my wiki", or "audit my
  knowledge base". Also invoked internally by the `second-brain` orchestrator skill on its
  configured cadence.
metadata:
  version: "0.1.0"
---

# Lint the Wiki

Periodically audit the wiki for health issues. Contradictions, orphans, missing pages, and
missing cross-links are never auto-fixed - each becomes a file in `wiki/review/pending/` for the
human, consistent with the "hold for review" philosophy used during ingest. The one exception is
stale pages: those get automatically archived (moved to `wiki/archives/`, never deleted) since
that's a mechanical disposition based on a threshold the user defined themselves, not a judgment
call.

## Steps

1. Confirm `.secondbrain/config.json` exists (if not, direct the user to `init` and stop).
2. Read `staleness_days` from config. **If it is not set, skip the staleness check entirely -
   do not invent a default.** Only run staleness checks when the user has explicitly defined
   what "stale" means for their wiki.
3. Invoke the `wiki-lint` subagent (via the Task tool) with the wiki folder path,
   `staleness_days` (or explicit instruction to skip that check if unset), and the schema.
4. Take the subagent's findings and present them, grouped by type: contradictions, orphan pages,
   missing pages, missing cross-links (each naming its `wiki/review/pending/` filename) - plus a
   separate list of any pages the subagent archived this run (with the reason each crossed the
   staleness threshold). Mention the `review` skill as the way to see/resolve the queue later.
5. Append a log entry: `## [YYYY-MM-DD] lint | <N> findings (<K> new), <M> archived` to
   `wiki/log.md` with a one-line breakdown of counts by category. Lint itself performs no other
   writes beyond what the `wiki-lint` subagent already did for archiving and filing findings.
