---
name: ingest
description: >
  Ingest exactly one source into a configured Second Brain wiki. Use for requests to ingest,
  process, or add a named raw file. Supports regular Karpathy-style ingest and explicit deep
  ingest. Works directly without a platform-specific subagent.
metadata:
  version: "0.3.0"
---

# Ingest One Source

Integrate exactly one immutable raw source into the wiki. Never edit, rename, move, or delete a
raw source. If multiple files are supplied, process only the first and leave the rest for later
invocations.

## Resolve context and mode

1. Confirm `.secondbrain/config.json` exists; otherwise direct the user to `init`.
2. Read the configured raw and wiki folders and `default_ingest_mode`. Missing mode defaults to
   `regular`. An explicit regular/deep request overrides it for this run.
3. Check `.secondbrain/ingested.json`. Skip an unchanged path-and-hash match unless the user
   explicitly requests re-ingestion.
4. Read the project's `AGENTS.md` or `CLAUDE.md` schema. If both exist, they should contain the
   same generated schema; report a material conflict rather than guessing.

## Read only useful context

1. Read the source in full. Stop if its format cannot be read reliably.
2. Search `wiki/learnings/` for entries relevant to the source topic; do not load every learning
   without a reason.
3. Find related active pages before drafting. At up to 100 content pages, use `wiki/index.md`.
   Above 100, locate the plugin root as the directory containing `.codex-plugin` or
   `.claude-plugin`, then run `scripts/bm25_search.py <wiki_dir> "<source terms>" --top-k 10`.

## Integrate

- **Regular mode:** follow Karpathy's baseline. Create one source summary, update or create every
  genuinely relevant entity/concept/topic page, maintain useful wikilinks, update the index, and
  append to the log. There is no arbitrary page cap; incidental mentions do not justify pages.
- **Deep mode:** perform the regular work, then inspect the wider related graph for second-order
  connections and additional synthesis. This is substantially more token-intensive.
- Every created or updated page must have a genuine connection to another page. File an `orphan`
  review item instead of forcing a weak link.
- If the source conflicts with an existing claim, leave that claim unchanged and create one
  durable `contradiction` file in `wiki/review/pending/` with the pages, claims, source, date, and
  suggested human decision.

## Persist and report

1. Update `wiki/index.md` for created and changed pages.
2. Append `## [YYYY-MM-DD] ingest | <source title>` to `wiki/log.md` with a compact summary.
3. Record `{filename, path, hash, ingested_at}` in `.secondbrain/ingested.json` only after wiki
   writes succeed.
4. Report the mode, pages created, pages updated, and every pending-review filename.
