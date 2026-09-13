---
name: lint
description: >
  Use when the user explicitly asks to lint, health-check, or audit a Second Brain wiki, or when
  automatic lint is both enabled and due. Runs deterministic checks locally and uses the current
  agent only for targeted semantic comparisons. Does not delegate to a lint subagent.
metadata:
  version: "0.3.0"
---

# Low-Token Wiki Lint

Lint is optional. Never start it merely because an ingest completed. Run only after explicit
interactive approval, or when `.secondbrain/config.json` has `automatic_lint_enabled: true` and
its configured cadence is due.

The goal is to preserve high-value contradiction and graph-health detection without repeatedly
loading the whole wiki into an LLM context. Structural discovery is local and deterministic;
semantic analysis is incremental and candidate-driven.

## Step 1: Load configuration

1. Confirm `.secondbrain/config.json` exists; otherwise direct the user to `init` and stop.
2. Read `wiki_folder` and `staleness_days` from config.
3. Use `.secondbrain/lint-state.json` for resumable state. Do not create or edit this file by
   hand; the bundled script owns it.
4. Resolve `<plugin-root>` as the directory containing `.codex-plugin` or `.claude-plugin` and
   the shared `scripts/` directory.

## Step 2: Prepare or resume one batch

Run:

```bash
python3 <plugin-root>/scripts/wiki_lint.py scan <wiki_dir> --state-file .secondbrain/lint-state.json --max-pages 15 --top-k 3
```

Add `--staleness-days <N>` only when configured. If `python3` is unavailable, try the platform's
available Python command. Do not replace the script with a full-wiki manual read.

The first run is a bootstrap lint: all active pages enter a persistent queue, but only one batch
is returned. Later invocations resume that queue. After bootstrap completes, only pages whose
content hashes changed are queued.

## Step 3: File deterministic findings

The script reports broken links, orphan pages, missing or invalid metadata, duplicate titles,
and stale-page candidates without model analysis. For each new finding:

1. Check `wiki/review/pending/` and `wiki/review/resolved/` for the same fingerprint or issue.
2. If it is not already recorded, create
   `wiki/review/pending/<type>-<slug>-<YYYY-MM-DD>.md` with `type`, `status: pending`,
   `flagged_by: lint`, `flagged_date`, `fingerprint`, `related_pages`, the description, and a
   suggested next step.
3. Do not automatically archive stale pages. Age creates a `stale` review candidate; a human
   decides whether it should be archived.

## Step 4: Targeted semantic checks

For each `semantic_candidate_pairs` item returned by the script:

1. Inspect the supplied excerpts first.
2. Open full pages only when the excerpts indicate a plausible contradiction, missing
   cross-reference, or ambiguous claim that cannot be judged from the excerpts.
3. File confirmed contradictions or missing cross-links in `wiki/review/pending/`, including the
   script pair, exact conflicting claims or missing relationship, and a stable fingerprint.
4. Never resolve contradictions automatically. Do not file speculative findings.

Do not scan unrelated pages, follow the graph beyond the candidate pair, or reread unchanged
pages. This bounded semantic pass is the main token-control mechanism.

## Step 5: Commit only after findings are durable

After all findings from the returned batch have been written, run:

```bash
python3 <plugin-root>/scripts/wiki_lint.py commit <wiki_dir> --state-file .secondbrain/lint-state.json --batch-id <batch_id>
```

If the run is interrupted before commit, the same active batch is returned next time. Never
commit before writing review files.

## Step 6: Log and report

Append one entry to `wiki/log.md`:

`## [YYYY-MM-DD] lint | <mode>, <N> findings, <R> pages remaining`

Report deterministic and semantic findings separately. If pages remain, say that bootstrap lint
is incomplete and another approved lint run will resume it. Do not loop through additional
batches in the same invocation unless the user explicitly requested a deep or complete lint.
