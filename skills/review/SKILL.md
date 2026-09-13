---
name: review
description: >
  This skill should be used when the user asks "what needs my review", "show pending reviews",
  "what's in my review queue", "resolve the contradiction between X and Y", "I fixed that
  orphan page", or otherwise wants to see or act on items in wiki/review/pending/. This is the
  durable surface for findings that ingest and lint can't resolve on their own.
metadata:
  version: "0.3.0"
---

# Review the Queue

Surface and resolve items in `wiki/review/pending/` - the durable record of every contradiction,
orphan, missing page, or missing cross-reference that `ingest` or `lint` flagged and couldn't
resolve on its own. Files keep findings discoverable after the chat that created them ends.

## Listing pending items

1. Confirm `.secondbrain/config.json` exists (if not, direct the user to `init` and stop).
2. Read every file in `wiki/review/pending/`. If empty, say so plainly - "no pending review
   items" - don't invent findings.
3. Present each item grouped by `type` (contradiction, orphan, missing-page, missing-crosslink,
   metadata, duplicate-title, stale),
   showing: filename, related pages, the description, who flagged it (`ingest` or `lint`) and
   when, and the suggested next step from the file body.
4. If there are many, lead with the oldest (they've been waiting longest) or let the user filter
   by type if they ask.

## Resolving an item

Triggered when the user references a specific finding (by filename, by the pages involved, or by
describing what they did) and explains how it should be resolved - e.g. "the contradiction
between page-a and page-b is resolved, page-b was outdated" or "go ahead and link the orphan page
to concept-x".

1. Locate the matching file in `wiki/review/pending/`. If ambiguous which finding they mean, ask.
2. If the resolution requires a wiki edit (e.g. adding a link, updating a page to remove the
   contradiction), make that edit now, following `AGENTS.md` or `CLAUDE.md` conventions - this is the one
   place a human's explicit resolution instruction translates directly into wiki changes.
   For a stale finding, archive the page only when the human explicitly confirms it: move it to
   `wiki/archives/`, add `archived: true` and `archived_date`, and move its index row from Active
   to Archived. Never delete it.
3. Append a `## Resolution` section to the review file: the date, what was decided, and what
   changed as a result.
4. Move the file from `wiki/review/pending/` to `wiki/review/resolved/`, updating its `status`
   field to `resolved` and adding `resolved_date`.
5. **Write a learning.** A human resolving a flagged item is exactly the kind of decision future
   ingests should respect - create a file in `wiki/learnings/` (same convention as learnings from
   direct page edits: `<node-name>-<date>.md`) summarizing the resolution, so the next ingest
   doesn't reintroduce the same contradiction or leave a similar page
   disconnected.
6. Append an entry to `wiki/log.md`: `## [YYYY-MM-DD] review | resolved <finding filename>`.
7. Confirm to the user what was resolved and that a learning was recorded.

## Rules

- Never resolve a contradiction on your own judgment without the human's explicit input on which
  side is correct - that defeats the point of holding it for review in the first place.
- Don't silently skip old items - if something has been pending a long time, mention its age when
  listing, but don't auto-resolve or auto-archive it. Stale pages move to `wiki/archives/` only
  after explicit human confirmation.
