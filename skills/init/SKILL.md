---
name: init
description: >
  This skill should be used when the user wants to "set up a second brain", "create a second
  brain os", "initialize my wiki", "start a new knowledge base", or otherwise bootstrap the
  Second Brain OS system in a folder for the first time. One-time setup only — do not re-run
  automatically once `.secondbrain/config.json` already exists (ask before overwriting).
metadata:
  version: "0.1.0"
---

# Initialize a Second Brain

Set up the raw/wiki/schema structure and configuration for a new Second Brain, following
Andrej Karpathy's LLM Wiki pattern (raw sources are immutable; the wiki is LLM-owned; a schema
file governs behavior).

## Step 1: Check for existing setup

If `.secondbrain/config.json` already exists in the target directory, tell the user a Second
Brain is already configured here and ask whether they want to reconfigure (this will not delete
existing wiki content) before continuing.

## Step 2: Ask setup questions

Ask the user, in one message, before creating anything:

1. **Raw folder** — what is the exact path or name of the folder containing (or that will
   contain) their raw sources? It does not need to be named `raw/` — use whatever they tell you
   and store it verbatim. It can already exist (with files in it) or be empty/not-yet-created.
2. **Topic** — what is this wiki about / what domain does it cover?
3. **Source types** — what kinds of files will be fed in (meeting recordings, PPTs, PDFs,
   articles, transcripts, images, etc.)?
4. **Scale** — roughly how many sources do they expect to ingest (a dozen, hundreds)?
5. **Page types** — what kinds of wiki pages do they want (entity pages, concept pages, source
   summaries, people pages, project pages, etc.)? Offer Karpathy's defaults (entity, concept,
   source summary) if they have no preference.
6. **Staleness definition** — after how many days should a wiki node be considered "stale" and
   flagged for review during lint? If they don't give a number, staleness checking stays
   **disabled** — do not guess a default.
7. **Lint cadence** — how often should lint run automatically (e.g. every 7 days)? Only relevant
   if they plan to use scheduled sync; can be skipped for now and set later via `schedule-setup`.
8. **SessionStart catch-up hook** — do they want Claude Code to check, at the start of every
   session in this project, whether a scheduled sync was missed and catch up automatically? This
   is opt-in, not default-on.

Do not proceed to Step 3 until these are answered (staleness and lint cadence may be explicitly
skipped, per Step 2.6-2.7).

## Step 3: Create the folder structure

Given raw folder path `<raw_folder>`, create its parent-level sibling `wiki/` directory (i.e. if
`raw_folder` is `/Users/me/notes/raw`, create `/Users/me/notes/wiki`). If the raw folder does not
exist yet, create it too (empty).

Inside `wiki/`, create:

- `wiki/index.md` — seed with a `# Index` heading, an `## Active` subheading with an empty
  catalog table (columns: Page, Type, Summary, Last updated), and an `## Archived` subheading
  with the same empty column structure (populated later by lint when it archives stale pages).
- `wiki/log.md` — seed with a single `# Log` heading and one entry:
  `## [<today's date>] init | Second Brain created`.
- `wiki/learnings/` — empty directory (`.gitkeep` file inside so git tracks it).
- `wiki/archives/` — empty directory (`.gitkeep` file inside) for stale pages that lint later
  archives. Never deleted from, only added to.
- `wiki/review/pending/` and `wiki/review/resolved/` — empty directories (`.gitkeep` files
  inside). This is the durable review queue: every contradiction, orphan risk, or other
  human-judgment finding from `ingest` or `lint` becomes a file here, so it survives headless/cron
  runs where nobody is watching chat output in real time. See the `review` skill.
- Subdirectories for the page types agreed in Step 2.5 (e.g. `wiki/entities/`,
  `wiki/concepts/`, `wiki/sources/`) — do not create directories for page types the user didn't
  ask for.

## Step 4: Generate the CLAUDE.md schema

Read `references/claude-md-template.md` in this skill's directory and fill in the placeholders
using the Step 2 answers. Write the result to `CLAUDE.md` at the project root (the parent
directory containing both `raw_folder` and `wiki/`). This is the schema file Karpathy's pattern
calls for — it must include: the topic, source types, page-type conventions, the wikilink format
(`[[page-name]]`), the ingestion hygiene rules (one file per ingest cycle, every new/updated node
must link to at least one existing node, contradictions are held for human review rather than
auto-merged), the learnings rule (consult `wiki/learnings/` before drafting, log human edits as
new learnings), the review queue (`wiki/review/pending/` holds every human-judgment finding as its
own file until resolved via the `review` skill), and the staleness/lint rules from Step 2.6-2.7.

## Step 5: Create configuration files

Create `.secondbrain/config.json`:

```json
{
  "raw_folder": "<path from Step 2.1>",
  "wiki_folder": "wiki",
  "topic": "<Step 2.2>",
  "source_types": ["<Step 2.3>"],
  "page_types": ["<Step 2.5>"],
  "staleness_days": <number or null>,
  "lint_cadence_days": <number or null>,
  "session_start_hook_enabled": <true|false>,
  "created_at": "<today's date, ISO 8601>"
}
```

Create `.secondbrain/ingested.json` as an empty array: `[]`.

## Step 6: Wrap up

Tell the user the Second Brain is ready: where the raw folder is, where the wiki was created,
and that `CLAUDE.md` now governs behavior. If they haven't set up scheduling yet, mention the
`schedule-setup` skill as the next step for automatic ingestion. Do not ingest any files yet in
this step, even if the raw folder already has files in it — ingestion is a separate step (via the
`second-brain` orchestrator or the `ingest` skill), one file at a time.
