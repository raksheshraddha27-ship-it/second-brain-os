#!/usr/bin/env python3
"""
Second Brain OS - lightweight BM25 search over the wiki.

Per Andrej Karpathy's LLM Wiki gist: "at small scale the index file is
enough ... as the wiki grows you want proper search." This script is the
"proper search" - used by the wiki-query, wiki-lint, and wiki-ingest agents
once a wiki grows beyond ~100 pages, instead of relying solely on manually
reading wiki/index.md and following links.

Implemented with the Python standard library only (Okapi BM25) - no
external dependencies (no rank_bm25, no vector DB, no network access
required), so it works on any machine with python3 installed.

Usage:
    python3 bm25_search.py <wiki_dir> "<query>" [--top-k N]

Prints a JSON array of {path, score, snippet} to stdout, highest-scoring
first. `path` is relative to <wiki_dir>. Only files scoring > 0 are
returned.
"""
import argparse
import json
import math
import os
import re

WORD_RE = re.compile(r"[a-z0-9]+")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)

# Structural files, not content pages - excluded from the search corpus.
EXCLUDE_FILES = {"index.md", "log.md"}


def tokenize(text):
    return WORD_RE.findall(text.lower())


def load_corpus(wiki_dir):
    docs = []
    for root, _dirs, files in os.walk(wiki_dir):
        for fname in files:
            if not fname.endswith(".md") or fname in EXCLUDE_FILES:
                continue
            path = os.path.join(root, fname)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    raw = f.read()
            except OSError:
                continue
            body = FRONTMATTER_RE.sub("", raw, count=1)
            docs.append({"path": path, "text": body})
    return docs


def bm25_scores(tokenized_docs, query_terms, k1=1.5, b=0.75):
    n_docs = len(tokenized_docs)
    if n_docs == 0:
        return []

    doc_lens = [len(tokens) for tokens in tokenized_docs]
    avgdl = (sum(doc_lens) / n_docs) if n_docs else 0.0

    doc_freq = {}
    for tokens in tokenized_docs:
        for term in set(tokens):
            doc_freq[term] = doc_freq.get(term, 0) + 1

    def idf(term):
        n_qi = doc_freq.get(term, 0)
        # +1 smoothing keeps idf non-negative even for very common terms.
        return math.log((n_docs - n_qi + 0.5) / (n_qi + 0.5) + 1)

    scores = [0.0] * n_docs
    for i, tokens in enumerate(tokenized_docs):
        term_freq = {}
        for t in tokens:
            term_freq[t] = term_freq.get(t, 0) + 1
        dl = doc_lens[i] or 1
        for term in query_terms:
            f = term_freq.get(term, 0)
            if f == 0:
                continue
            denom = f + k1 * (1 - b + b * dl / (avgdl or 1))
            scores[i] += idf(term) * (f * (k1 + 1)) / denom
    return scores


def make_snippet(text, query_terms, width=160):
    lower = text.lower()
    for term in query_terms:
        idx = lower.find(term)
        if idx != -1:
            start = max(0, idx - width // 2)
            return " ".join(text[start:start + width].split())
    return " ".join(text.strip().split())[:width]


def main():
    parser = argparse.ArgumentParser(description="BM25 search over a Second Brain wiki.")
    parser.add_argument("wiki_dir", help="Path to the wiki/ folder")
    parser.add_argument("query", help="Search query (natural language is fine)")
    parser.add_argument("--top-k", type=int, default=10, help="Max results to return")
    args = parser.parse_args()

    docs = load_corpus(args.wiki_dir)
    query_terms = tokenize(args.query)

    if not query_terms or not docs:
        print(json.dumps([]))
        return

    tokenized_docs = [tokenize(d["text"]) for d in docs]
    scores = bm25_scores(tokenized_docs, query_terms)

    ranked = sorted(zip(docs, scores), key=lambda pair: pair[1], reverse=True)
    results = [
        {
            "path": os.path.relpath(d["path"], args.wiki_dir),
            "score": round(score, 4),
            "snippet": make_snippet(d["text"], query_terms),
        }
        for d, score in ranked[: args.top_k]
        if score > 0
    ]
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
