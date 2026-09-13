---
name: init
description: >
  Initialize a Second Brain knowledge wiki in a project. Use when the user asks to set up,
  create, or initialize a second brain or maintained knowledge base. Do not overwrite an
  existing `.secondbrain/config.json` without explicit approval.
metadata:
  version: "0.3.0"
---

# Initialize a Second Brain

## Ask before creating

Collect these choices in one message:

1. Raw-source folder path.
2. Wiki topic or domain.
3. Expected source formats and approximate scale.
4. Desired page types; offer entity, concept, and source-summary pages as defaults.
5. Default ingest mode: **regular follows Karpathy's baseline; deep adds wider-graph synthesis
   at substantially higher token cost.** Recommend regular.
6. Lint behavior: manual or after every sync. **Lint improves contradiction and graph-health
   detection but can be token-intensive during its initial bootstrap.** Recommend manual.
7. Optional staleness threshold in days. Do not invent one.

## Create the wiki

Create the raw folder if needed and a sibling `wiki/` containing:

- `index.md` with Active and Archived tables: Page, Type, Summary, Last updated.
- `log.md` with `## [<today>] init | Second Brain created`.
- `learnings/`, `archives/`, `review/pending/`, and `review/resolved/`, each with `.gitkeep`.
- One directory for each chosen page type.

Read `references/claude-md-template.md`, fill every placeholder, and write the same generated
schema to both `AGENTS.md` and `CLAUDE.md` at the project root. This makes the project native to
Codex and Claude Code. Tell the user to keep the two generated schema files synchronized when
changing conventions.

## Create state

Create `.secondbrain/config.json`:

```json
{
  "raw_folder": "<chosen path>",
  "wiki_folder": "wiki",
  "topic": "<topic>",
  "source_types": ["<formats>"],
  "page_types": ["<page types>"],
  "default_ingest_mode": "<regular|deep>",
  "automatic_lint_enabled": <true|false>,
  "staleness_days": <number or null>,
  "created_at": "<ISO date>"
}
```

Create `.secondbrain/ingested.json` as `[]` and `.secondbrain/lint-state.json` as:

```json
{
  "version": 1,
  "bootstrap_complete": false,
  "page_hashes": {},
  "pending_pages": [],
  "checked_pairs": {},
  "known_findings": [],
  "active_batch": null,
  "last_completed_at": null
}
```

Report the selected folders and modes. Do not ingest during initialization.
