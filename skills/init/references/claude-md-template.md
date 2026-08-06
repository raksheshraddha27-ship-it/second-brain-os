# CLAUDE.md Template

Fill in every `<placeholder>` using the user's Step 2 answers, then write the result to
`CLAUDE.md` at the project root. Remove this instructions block from the final output — only the
content below the `---` separator is written to the file.

---

# <topic> — Second Brain Wiki Schema

This project is a Second Brain OS wiki, following Andrej Karpathy's LLM Wiki pattern. This file
is the schema: it tells any agent operating on this project how the wiki is structured and what
rules to follow. Read this file before ingesting, querying, or linting.

## Layers

- **`<raw_folder>/`** — immutable raw sources (<source_types>). Never edit or delete files here.
  Only read from this folder.
- **`wiki/`** — the LLM-owned, LLM-maintained knowledge base. All wiki content lives here.
- **`wiki/archives/`** — pages that crossed the staleness threshold. Content is never deleted
  from the wiki, only moved here (see Staleness and lint below).
- **`wiki/review/`** — the durable human-review queue (see "Human review queue" below). Anything
  ingest or lint can't resolve on its own lives here as a file until a human acts on it.
- **This file (`CLAUDE.md`)** — the schema. Update it if the user asks you to change a
  convention, but never let ingestion/query/lint work silently redefine it.

## Page types

<page_types_list>

Each page is a markdown file with YAML frontmatter:

```yaml
---
type: <page type, e.g. concept|entity|source>
title: <human-readable title>
created: <ISO date>
updated: <ISO date>
source_files: [<raw filenames that contributed to this page>]
---
```

## Linking convention

Use Obsidian-style wikilinks: `[[page-name]]` (filename without `.md`, relative to `wiki/`).
Every page should link to at least one other page — an unlinked page is an orphan and will be
flagged by lint.

## `wiki/index.md`

A catalog of every page in the wiki: one row per page with a link, its type, a one-line summary,
and last-updated date, split into an **Active** section and an **Archived** section (pages moved
to `wiki/archives/` get relocated to the Archived section, never deleted from the catalog). Update
this on every ingest and every lint archive action. When answering a query, read this file first
to find candidate pages — **but only at moderate scale**. See "Search at scale" below for what to
do once the wiki has grown past ~100 pages.

## `wiki/log.md`

Append-only. Every ingest, query-that-got-filed-back, and lint pass gets one entry, in this exact
format so it stays greppable:

```
## [YYYY-MM-DD] <operation: ingest|query|lint|init> | <short title>
<one or two lines of detail>
```

## `wiki/learnings/`

Whenever a human directly edits a wiki page (not the LLM's own ingest/lint edits), that edit is a
signal that something should be done differently. Create a new file in `wiki/learnings/` named
`<node-name>-<date>.md` describing what changed and why, inferred from the diff and any
explanation the human gave. **Before drafting or updating any wiki page, first check
`wiki/learnings/` for entries relevant to that page or topic, and apply them.**

## Human review queue (`wiki/review/`)

Every finding that requires human judgment — not just chat output, an actual file — so it
survives headless/cron runs where nobody is reading the terminal in real time:

- `wiki/review/pending/` — one markdown file per open finding.
- `wiki/review/resolved/` — where files move once a human resolves them (via the `review` skill).

File naming: `<type>-<slug>-<YYYY-MM-DD>.md`. Frontmatter:

```yaml
---
type: contradiction | orphan | missing-page | missing-crosslink
status: pending
flagged_by: ingest | lint
flagged_date: <ISO date>
related_pages: [[page-a]], [[page-b]]
---
```

Body: a plain description of the issue and a suggested next step. Whoever creates the finding
(ingest or lint) writes this file **in addition to** reporting it in their output — the chat
summary is for immediate visibility, the file is for durability. When a human resolves an item
(via the `review` skill), the file gets a `## Resolution` section appended, moves to
`wiki/review/resolved/`, and — since a human resolving something is exactly the kind of decision
future drafting should respect — a corresponding entry gets written to `wiki/learnings/` too.

## Ingestion hygiene (enforced on every ingest)

1. **One file per ingestion cycle.** Never process more than one raw source file in a single
   ingest pass, even if several new files are waiting.
2. **Connectivity.** Every new or updated node must link to at least one existing node. If a
   newly drafted page would be an orphan, find a genuine connection before finalizing it, or
   write a `wiki/review/pending/` file about it rather than leaving it silently disconnected.
3. **Contradictions require human review.** If new information contradicts an existing page,
   do **not** silently overwrite or merge it. Write a `wiki/review/pending/` contradiction file
   (see above), note it in the ingest summary and in `log.md`, and leave the existing page
   untouched until a human resolves it via the `review` skill.
4. **Consult learnings first.** See `wiki/learnings/` above.

## Staleness and lint

<staleness_clause>

<lint_cadence_clause>

Lint checks for: contradictions between pages, orphan pages, stale nodes (per the rule above),
concepts mentioned but missing their own page, and missing cross-references. Lint only proposes
and flags for everything **except** staleness — findings for contradictions, orphans, and missing
links/pages each become a file in `wiki/review/pending/` (see "Human review queue" above) and are
never auto-resolved.

**Stale pages are archived, never deleted.** Once a page crosses the staleness threshold, it is
moved to `wiki/archives/` (frontmatter gets `archived: true` / `archived_date`), its `index.md`
row moves from Active to Archived, and the move is logged. This is the one lint action that
happens automatically rather than sitting in the review queue, because it's a mechanical
disposition based on a threshold you defined, not a judgment call — and because nothing is lost,
archived pages remain fully readable and queryable, just out of the active set.

## Search at scale

At small scale (≤100 pages), `wiki/index.md` is sufficient for finding candidate pages during
query, ingest, and lint — this is the default per Karpathy's pattern. **Once the wiki has more
than 100 active pages**, index-skimming stops scaling well. From that point on, agents use the
bundled BM25 search script instead:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/bm25_search.py <wiki_dir> "<query>" --top-k 10
```

This is a dependency-free, on-device Okapi BM25 implementation (Python standard library only —
no vector DB, no network calls) that ranks wiki pages by relevance to a query and returns the top
matches with snippets. It excludes `index.md`, `log.md`, and (implicitly, since they're a
separate concern) does not need to touch `wiki/archives/` for normal query/ingest search. This
threshold is fixed at 100 pages across ingest, query, and lint — not separately configurable per
operation.

## Scale expectations

Roughly <scale> sources expected.
