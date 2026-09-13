# Cross-platform wiki schema template

Fill in every `<placeholder>` using the setup answers, then write the same result to `AGENTS.md`
and `CLAUDE.md` at the project root. Remove this instructions block from both outputs.

---

# <topic> — Second Brain Wiki Schema

This project is a Second Brain OS wiki, following Andrej Karpathy's LLM Wiki pattern. This file
is the schema: it tells any agent operating on this project how the wiki is structured and what
rules to follow. Read this file before ingesting, querying, or linting.

## Layers

- **`<raw_folder>/`** — immutable raw sources (<source_types>). Never edit or delete files here.
  Only read from this folder.
- **`wiki/`** — the LLM-owned, LLM-maintained knowledge base. All wiki content lives here.
- **`wiki/archives/`** — pages approved for archiving after crossing the staleness threshold.
  Content is never deleted from the wiki, only moved here (see Staleness and lint below).
- **`wiki/review/`** — the durable human-review queue (see "Human review queue" below). Anything
  ingest or lint can't resolve on its own lives here as a file until a human acts on it.
- **`AGENTS.md` and `CLAUDE.md`** — identical platform adapters for this schema. Keep them
  synchronized when conventions change; never let ingestion/query/lint silently redefine them.

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

Every finding that requires human judgment becomes an actual file rather than transient chat:

- `wiki/review/pending/` — one markdown file per open finding.
- `wiki/review/resolved/` — where files move once a human resolves them (via the `review` skill).

File naming: `<type>-<slug>-<YYYY-MM-DD>.md`. Frontmatter:

```yaml
---
type: contradiction | orphan | missing-page | missing-crosslink | metadata | duplicate-title | stale
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

5. **Ingest modes.** The configured default is **`<default_ingest_mode>`**. Regular ingest
   follows Karpathy's baseline workflow:
   create a source-summary page, update the index and log, and update or create every genuinely
   relevant entity/concept/topic page with useful cross-links. A source may touch 10-15 pages;
   there is no page-count cap. Deep ingest is opt-in only and adds an exhaustive pass over the
   wider graph for second-order connections and additional synthesis. Trade-off: **regular uses
   fewer tokens; deep can produce a denser, more connected wiki at substantially higher token
   cost.** An explicit mode request overrides the configured default for that ingest only.

## Staleness and lint

<lint_enabled_clause>

<staleness_clause>

Lint runs deterministic local checks for broken links, orphan pages, metadata errors, duplicate
titles, and stale candidates. It then uses `.secondbrain/lint-state.json` to compare only new or
changed pages with a small set of related pages for contradictions and missing cross-references.
The initial bootstrap is resumable and processes a bounded batch per approved run. Every finding
becomes a file in `wiki/review/pending/`; lint never resolves findings automatically.

**Stale pages are reviewed, never automatically archived.** Crossing the configured threshold
creates a `stale` review item. A page moves to `wiki/archives/` only after explicit human
confirmation; its frontmatter and `index.md` row are then updated, and nothing is deleted.

When automatic lint is disabled, sync must not run lint silently. It may offer lint after
ingestion, but requires explicit user confirmation.

## Search at scale

At small scale (≤100 pages), `wiki/index.md` is sufficient for finding candidate pages during
query and ingest. **Once the wiki has more than 100 active pages**, use the bundled BM25 search
script. Resolve `<plugin-root>` as the directory containing `.codex-plugin` or `.claude-plugin`:

```
python3 <plugin-root>/scripts/bm25_search.py <wiki_dir> "<query>" --top-k 10
```

This is a dependency-free, on-device Okapi BM25 implementation (Python standard library only —
no vector DB, no network calls) that ranks wiki pages by relevance to a query and returns the top
matches with snippets. It excludes `index.md`, `log.md`, and (implicitly, since they're a
separate concern) does not need to touch `wiki/archives/` for normal query/ingest search. This
threshold is fixed at 100 pages for ingest and query. Lint uses its own incremental local planner.

## Scale expectations

Roughly <scale> sources expected.
