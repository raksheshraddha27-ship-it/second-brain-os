---
name: ingest
description: >
  This skill should be used when the user asks to "ingest this file", "add this source to my
  wiki", "process raw/<filename>", or names a specific file in the raw folder to add to the
  Second Brain. Also invoked internally by the `second-brain` orchestrator skill with exactly
  one file path. Processes exactly one raw source per invocation — never more.
metadata:
  version: "0.1.0"
---

# Ingest a Single Source

Add exactly one raw source file into the wiki. This skill is a thin wrapper: it validates,
delegates the real work to the `wiki-ingest` subagent, then records the result.

## Hard rule: one file only

If the user or caller provides more than one filename, process **only the first one** and tell
them explicitly that the rest need separate, subsequent ingest calls — never combine multiple
raw sources into a single ingestion pass, and never loop over a list of files within this skill.
This mirrors the immutability of `raw/`: sources go in one at a time, deliberately, so each one
gets full attention and any contradictions it introduces are caught individually.

## Steps

1. Confirm `.secondbrain/config.json` exists (if not, direct the user to `init` and stop).
2. Resolve the single target file path against `raw_folder` from the config.
3. Check `.secondbrain/ingested.json` — if this exact file (by path + content hash) was already
   ingested, tell the user and stop; do not re-ingest unless they explicitly ask for a re-ingest
   of an updated version.
4. Read `CLAUDE.md` for the current schema/conventions.
5. Invoke the `wiki-ingest` subagent (via the Task tool) with: the single file path, the wiki
   folder path, and the schema contents. Do not read or summarize the source file yourself first
   — let the subagent do the actual reading and drafting so the work is isolated and auditable.
6. When the subagent returns, review its summary of pages created/updated and any findings it
   wrote to `wiki/review/pending/`.
7. Update `.secondbrain/ingested.json` with `{filename, path, hash, ingested_at}` for this file.
8. Append one entry to `wiki/log.md` in the standard format:
   `## [YYYY-MM-DD] ingest | <source title>` followed by a one/two-line summary of what changed
   and how many review findings were filed.
9. Report back to the user: pages created, pages updated, and any findings now sitting in
   `wiki/review/pending/` awaiting their attention (name each file, not just "there were
   contradictions" — the user should be able to go straight to the review skill or open the file).
   Mention the `review` skill as the way to see and resolve them.
