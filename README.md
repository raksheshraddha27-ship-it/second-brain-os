# Second Brain OS

A Claude Code plugin that turns any folder of raw sources (meeting recordings, PPTs, notes,
articles, PDFs) into a self-maintaining, LLM-curated knowledge wiki - implementing
[Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
raw sources are compiled once into a persistent, interlinked markdown wiki, then kept current,
instead of being re-read from scratch on every question.

## How it works

Three layers, per Karpathy's pattern:

- **`raw/`** (name is whatever you choose) - your immutable source documents. Read-only, enforced
  automatically by a hook.
- **`wiki/`** - the LLM-owned, interlinked markdown knowledge base (`index.md` catalog,
  `log.md` history, page-type folders, `learnings/`, `archives/`, `review/`).
- **`CLAUDE.md`** - the schema file generated during setup, governing conventions and rules.

On top of Karpathy's bare pattern, this plugin adds opinionated hygiene rules: every new/updated
page must connect to the existing graph, contradictions are held for human review instead of
being auto-merged, ingestion processes exactly one raw file at a time (never a batch), human
edits to wiki pages are captured as `wiki/learnings/` entries that future drafting must consult,
and stale pages are archived to `wiki/archives/` rather than ever being deleted. Once the wiki
grows past ~100 pages, lookups switch from scanning `index.md` to a bundled dependency-free BM25
search script (`scripts/bm25_search.py`).

Anything `ingest` or `lint` can't resolve on its own - contradictions, orphans, missing pages,
missing links - becomes a durable file in `wiki/review/pending/`, not just chat output. That way a
finding from a headless/cron run doesn't vanish the moment the terminal closes; it's a file you
can come back to, see with the `review` skill, and resolve whenever you're ready. Resolving one
also files a `wiki/learnings/` entry, so the decision sticks for future ingests.

## Components

| Component | Type | Purpose |
|---|---|---|
| `second-brain` | Skill (orchestrator) | Single entry point for manual, cron, and SessionStart-triggered runs. Reads state and dispatches to the skills below. |
| `init` | Skill | One-time setup: asks about your raw folder, topic, sources, page types, staleness definition; creates `wiki/`, `CLAUDE.md`, and config. |
| `ingest` | Skill | Adds exactly one raw file to the wiki via the `wiki-ingest` subagent. |
| `query` | Skill | Answers questions from the wiki via the `wiki-query` subagent; can file answers back as new pages. |
| `lint` | Skill | Periodic health audit via the `wiki-lint` subagent: contradictions, orphans, staleness, missing links. |
| `schedule-setup` | Skill | Installs an OS-level cron/launchd/Task Scheduler entry for automatic syncing. |
| `review` | Skill | Lists and resolves items in `wiki/review/pending/`; resolving one files a learning. |
| `wiki-ingest` | Subagent | Does the actual multi-page reading/drafting/updating during ingest; files review findings. |
| `wiki-lint` | Subagent | Runs the audit, files review findings for anything needing judgment, and archives stale pages (the one automatic action it's allowed to take). |
| `wiki-query` | Subagent | Reads the wiki and synthesizes cited answers. |
| `hooks.json` | Hooks | `PreToolUse` blocks edits inside `raw/` (immutability); `SessionStart` optionally checks for a missed scheduled sync and/or a pending review backlog. |
| `scripts/bm25_search.py` | Script | Dependency-free Okapi BM25 search over `wiki/*.md`, used by the query/ingest/lint subagents once the wiki exceeds ~100 pages. |

## Setup

1. Install the plugin (see below), then in a Claude Code session run: *"set up a second brain"*
   to trigger the `init` skill. Answer its questions - raw folder path/name, topic, source types,
   expected scale, page types, staleness definition (optional), lint cadence (optional).
2. Optionally run *"set up automatic ingestion"* to trigger `schedule-setup`. Note: Claude Code
   plugins have no built-in scheduler - this installs a real OS-level cron/launchd/Task Scheduler
   job that calls `claude -p` headlessly. It depends on the machine being on at the scheduled
   time; a missed run is picked up on the next one (or via the optional SessionStart catch-up
   hook, which you can opt into during this step).
3. Drop files into your raw folder and either wait for the schedule, or say *"sync my second
   brain"* / *"ingest raw/\<file\>"* manually.

Each sync processes **at most one new file** - by design, not a limitation. A backlog drains
gradually across runs so every source gets full attention and any contradiction it introduces is
caught individually.

## Usage

- *"What does my second brain know about X?"* -> `query`
- *"Ingest raw/meeting-2026-08-05.txt"* -> `ingest`
- *"Run a health check on my wiki"* -> `lint`
- *"What needs my review?"* / *"resolve the contradiction between X and Y"* -> `review`
- *"Sync my second brain"* / scheduled cron run -> `second-brain` orchestrator
- Open the `wiki/` folder in [Obsidian](https://obsidian.md) for the graph view.

## Installing this plugin

This repo follows the standard Claude Code plugin layout (`.claude-plugin/plugin.json` +
`skills/` + `agents/` + `hooks/`). Add it as a plugin source and install it, e.g.:

```
/plugin marketplace add <this-repo-url>
/plugin install second-brain-os
```

(Exact commands may vary by Claude Code version - run `claude plugin --help` or see the
[Claude Code plugin docs](https://docs.claude.com) if these don't match your CLI.)

## Requirements

- Claude Code CLI, with `claude` available on `PATH` if you want scheduled/headless syncing.
- `python3` available on the machine for the optional SessionStart catch-up check (the hook
  silently no-ops if missing).
- [Obsidian](https://obsidian.md) (optional) for visualizing the wiki as a graph.

## Credit

Pattern: [Andrej Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
This plugin implements the pattern with an opinionated hygiene/orchestration layer on top; the
gist itself deliberately leaves page taxonomy, linking syntax, and schema conventions
unspecified for the implementer to decide.
