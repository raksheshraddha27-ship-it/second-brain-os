---
name: query
description: >
  This skill should be used when the user asks a question meant for their Second Brain wiki -
  e.g. "what does my second brain know about X", "ask my wiki about Y", "based on my notes,
  how do X and Y relate". Also invoked internally by the `second-brain` orchestrator skill.
metadata:
  version: "0.1.0"
---

# Query the Wiki

Answer a question using the wiki, not the raw sources - the whole point of the LLM Wiki pattern
is that synthesis already happened at ingest time.

## Steps

1. Confirm `.secondbrain/config.json` exists (if not, direct the user to `init` and stop).
2. Invoke the `wiki-query` subagent (via the Task tool) with the user's question and the wiki
   folder path. Do not answer from the raw folder or from general knowledge as a substitute -
   the answer should be grounded in what's actually in `wiki/`.
3. Relay the subagent's answer, including its page citations.
4. **Offer to file the answer back.** If the answer synthesizes something non-trivial (e.g.
   connects multiple pages in a way not already captured), ask the user if they'd like it saved
   as a new wiki page. If yes, invoke `wiki-query` again (or the same result) to write the page,
   update `index.md`, and append a `## [YYYY-MM-DD] query | <topic>` entry to `log.md`. If the
   answer was a simple lookup already covered by an existing page, don't bother asking.
