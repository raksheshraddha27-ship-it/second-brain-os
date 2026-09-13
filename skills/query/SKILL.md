---
name: query
description: >
  Answer questions from a configured Second Brain wiki. Use when the user asks what their wiki,
  notes, or second brain knows. Ground answers in wiki pages rather than raw sources or unstated
  general knowledge.
metadata:
  version: "0.3.0"
---

# Query the Wiki

1. Confirm `.secondbrain/config.json` exists and read `wiki_folder`; otherwise direct the user to
   `init`.
2. Find candidate pages. At up to 100 content pages, read `wiki/index.md`. Above 100, locate the
   plugin root as the directory containing `.codex-plugin` or `.claude-plugin`, then run
   `scripts/bm25_search.py <wiki_dir> "<question>" --top-k 10`.
3. Read the strongest candidates and follow only links needed to answer the question.
4. Synthesize an answer with explicit wiki-page citations. If the wiki lacks relevant content,
   say so; do not present general knowledge as wiki-derived.
5. If the answer creates useful new synthesis, offer to save it. On approval, read the project
   schema, write an appropriately linked page, update `wiki/index.md`, and append
   `## [YYYY-MM-DD] query | <topic>` to `wiki/log.md`.

End every answer with a `Sources:` line listing the wiki pages used.
