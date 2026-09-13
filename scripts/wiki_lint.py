#!/usr/bin/env python3
"""Low-token structural and incremental lint planner for Second Brain OS.

The script performs deterministic checks locally and prepares a small batch of
high-probability page pairs for semantic review by the calling agent. State is
committed only after the agent finishes a batch, so interrupted bootstrap runs
resume safely.
"""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
WORD_RE = re.compile(r"[a-z0-9]+")
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EXCLUDED_TOP_LEVEL = {"archives", "review", "learnings"}
EXCLUDED_FILES = {"index.md", "log.md"}
REQUIRED_FRONTMATTER = {"type", "title", "created", "updated", "source_files"}
CLAIM_MARKERS = {
    "not", "never", "no", "only", "must", "should", "before", "after", "since",
    "increased", "decreased", "replaced", "deprecated", "launched", "closed",
    "active", "inactive", "current", "formerly", "percent", "version",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for",
    "from", "had", "has", "have", "he", "her", "his", "i", "if", "in", "is",
    "it", "its", "of", "on", "or", "our", "she", "that", "the", "their",
    "them", "there", "they", "this", "to", "was", "we", "were", "will", "with",
    "you", "your",
}


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError, TypeError):
        return default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def parse_frontmatter(text):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    metadata = {}
    for line in match.group(1).splitlines():
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata, text[match.end():]


def tokenize(text):
    return [word for word in WORD_RE.findall(text.lower()) if word not in STOPWORDS]


def load_pages(wiki_dir):
    wiki_dir = Path(wiki_dir).resolve()
    pages = {}
    for path in sorted(wiki_dir.rglob("*.md")):
        relative = path.relative_to(wiki_dir)
        if path.name in EXCLUDED_FILES or relative.parts[0].lower() in EXCLUDED_TOP_LEVEL:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        metadata, body = parse_frontmatter(text)
        rel = relative.as_posix()
        pages[rel] = {
            "path": rel,
            "hash": sha256_text(text),
            "metadata": metadata,
            "body": body,
            "tokens": tokenize(body),
            "links": WIKILINK_RE.findall(body),
        }
    return pages


def normalize_link(value):
    value = value.split("|", 1)[0].split("#", 1)[0].strip().replace("\\", "/")
    if value.lower().endswith(".md"):
        value = value[:-3]
    return value.strip("/").lower()


def page_lookup(pages):
    exact = {}
    stems = {}
    for rel in pages:
        without_ext = rel[:-3].lower() if rel.lower().endswith(".md") else rel.lower()
        exact[without_ext] = rel
        stems.setdefault(Path(rel).stem.lower(), []).append(rel)
    return exact, stems


def resolve_link(value, exact, stems):
    normalized = normalize_link(value)
    if normalized in exact:
        return exact[normalized]
    matches = stems.get(Path(normalized).name, [])
    return matches[0] if len(matches) == 1 else None


def finding(kind, pages, description, details=None):
    identity = kind + "|" + "|".join(sorted(pages)) + "|" + description
    item = {
        "type": kind,
        "related_pages": pages,
        "description": description,
        "fingerprint": hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16],
    }
    if details:
        item["details"] = details
    return item


def deterministic_findings(pages, staleness_days):
    results = []
    exact, stems = page_lookup(pages)
    inbound = {rel: 0 for rel in pages}
    titles = {}

    for rel, page in pages.items():
        metadata = page["metadata"]
        missing = sorted(REQUIRED_FRONTMATTER - set(metadata))
        if missing:
            results.append(finding(
                "metadata", [rel], "Required frontmatter fields are missing", missing
            ))
        for field in ("created", "updated"):
            value = metadata.get(field)
            if value and (not DATE_RE.match(value) or not valid_iso_date(value)):
                results.append(finding(
                    "metadata", [rel], f"Invalid {field} date", [value]
                ))
        title = metadata.get("title", "").strip().lower()
        if title:
            titles.setdefault(title, []).append(rel)

        for raw_link in page["links"]:
            target = resolve_link(raw_link, exact, stems)
            if target:
                if target != rel:
                    inbound[target] += 1
            else:
                results.append(finding(
                    "missing-page", [rel], f"Unresolved wikilink: [[{raw_link}]]"
                ))

    for title, related in titles.items():
        if len(related) > 1:
            results.append(finding(
                "duplicate-title", related, f"Duplicate page title: {title}"
            ))

    for rel, count in inbound.items():
        if count == 0:
            results.append(finding(
                "orphan", [rel], "No inbound wikilinks from another active page"
            ))

    if staleness_days is not None:
        today = date.today()
        for rel, page in pages.items():
            updated = page["metadata"].get("updated")
            if not updated or not valid_iso_date(updated):
                continue
            age = (today - date.fromisoformat(updated)).days
            if age > staleness_days:
                results.append(finding(
                    "stale", [rel], f"Page is {age} days old; threshold is {staleness_days} days"
                ))
    return results


def valid_iso_date(value):
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def idf_table(pages):
    total = max(len(pages), 1)
    frequencies = Counter()
    for page in pages.values():
        frequencies.update(set(page["tokens"]))
    return {
        term: math.log((total + 1) / (frequency + 1)) + 1
        for term, frequency in frequencies.items()
    }


def salient_terms(tokens, idf, limit=30):
    counts = Counter(tokens)
    ranked = sorted(
        counts,
        key=lambda term: (counts[term] * idf.get(term, 1.0), len(term)),
        reverse=True,
    )
    return ranked[:limit]


def similarity(left, right, idf):
    left_terms = set(salient_terms(left["tokens"], idf))
    right_terms = set(salient_terms(right["tokens"], idf))
    overlap = left_terms & right_terms
    if not overlap:
        return 0.0, set()
    score = sum(idf.get(term, 1.0) for term in overlap)
    denominator = math.sqrt(
        max(sum(idf.get(term, 1.0) for term in left_terms), 1.0)
        * max(sum(idf.get(term, 1.0) for term in right_terms), 1.0)
    )
    return score / denominator, overlap


def excerpt(body, overlap, limit=360):
    sentences = [part.strip() for part in SENTENCE_RE.split(body) if part.strip()]
    ranked = []
    for sentence in sentences:
        words = set(tokenize(sentence))
        signal = len(words & overlap) * 3
        signal += sum(1 for word in CLAIM_MARKERS if word in words)
        signal += 2 if re.search(r"\b\d+(?:\.\d+)?%?\b", sentence) else 0
        ranked.append((signal, sentence))
    ranked.sort(key=lambda item: item[0], reverse=True)
    chosen = " ".join(sentence for score, sentence in ranked[:2] if score > 0)
    if not chosen and sentences:
        chosen = sentences[0]
    return chosen[:limit]


def pair_key(left, right):
    return "||".join(sorted((left, right)))


def build_pairs(batch, pages, checked_pairs, top_k):
    idf = idf_table(pages)
    pairs = {}
    for rel in batch:
        if rel not in pages:
            continue
        ranked = []
        for other in pages:
            if other == rel:
                continue
            score, overlap = similarity(pages[rel], pages[other], idf)
            if score > 0:
                ranked.append((score, other, overlap))
        ranked.sort(key=lambda item: item[0], reverse=True)
        for score, other, overlap in ranked[:top_k]:
            key = pair_key(rel, other)
            signature = ":".join(sorted((pages[rel]["hash"], pages[other]["hash"])))
            if checked_pairs.get(key) == signature or key in pairs:
                continue
            left, right = sorted((rel, other))
            pairs[key] = {
                "left": left,
                "right": right,
                "score": round(score, 4),
                "shared_terms": sorted(overlap)[:12],
                "left_excerpt": excerpt(pages[left]["body"], overlap),
                "right_excerpt": excerpt(pages[right]["body"], overlap),
                "signature": signature,
            }
    return list(pairs.values())


def default_state():
    return {
        "version": 1,
        "bootstrap_complete": False,
        "page_hashes": {},
        "pending_pages": [],
        "checked_pairs": {},
        "known_findings": [],
        "active_batch": None,
        "last_completed_at": None,
    }


def scan(args):
    pages = load_pages(args.wiki_dir)
    state = read_json(args.state_file, default_state())
    if state.get("version") != 1:
        state = default_state()

    current_hashes = {rel: page["hash"] for rel, page in pages.items()}
    committed = state.get("page_hashes", {})
    pending = [rel for rel in state.get("pending_pages", []) if rel in pages]
    changed = [rel for rel, digest in current_hashes.items() if committed.get(rel) != digest]
    pending = sorted(set(pending) | set(changed))
    removed = sorted(set(committed) - set(current_hashes))
    state["pending_pages"] = pending

    active = state.get("active_batch")
    if active:
        batch_paths = [item["path"] for item in active.get("pages", []) if item["path"] in pages]
        batch_id = active["id"]
    else:
        batch_paths = pending[: args.max_pages]
        batch_id = uuid.uuid4().hex
        state["active_batch"] = {
            "id": batch_id,
            "pages": [{"path": rel, "hash": current_hashes[rel]} for rel in batch_paths],
            "removed_pages": removed,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    pairs = build_pairs(batch_paths, pages, state.get("checked_pairs", {}), args.top_k)
    all_findings = deterministic_findings(pages, args.staleness_days)
    current_fingerprints = {item["fingerprint"] for item in all_findings}
    known_findings = {
        fingerprint for fingerprint in state.get("known_findings", [])
        if fingerprint in current_fingerprints
    }
    state["known_findings"] = sorted(known_findings)
    if state.get("bootstrap_complete"):
        batch_findings = [
            item for item in all_findings if item["fingerprint"] not in known_findings
        ]
    else:
        batch_set = set(batch_paths)
        batch_findings = [
            item for item in all_findings
            if item["fingerprint"] not in known_findings
            and batch_set.intersection(item["related_pages"])
        ]
    state["active_batch"]["pairs"] = [
        {"left": item["left"], "right": item["right"], "signature": item["signature"]}
        for item in pairs
    ]
    state["active_batch"]["finding_fingerprints"] = [
        item["fingerprint"] for item in batch_findings
    ]
    write_json(args.state_file, state)

    output = {
        "mode": "bootstrap" if not state.get("bootstrap_complete") else "incremental",
        "batch_id": batch_id,
        "batch_pages": batch_paths,
        "remaining_after_batch": max(len(pending) - len(batch_paths), 0),
        "removed_pages": removed,
        "deterministic_findings": batch_findings,
        "semantic_candidate_pairs": pairs,
        "instructions": "Review excerpts first. Open full pages only for plausible contradictions or missing cross-links. Commit this batch only after durable findings are written.",
    }
    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")


def commit(args):
    pages = load_pages(args.wiki_dir)
    state = read_json(args.state_file, default_state())
    active = state.get("active_batch")
    if not active or active.get("id") != args.batch_id:
        raise SystemExit("No matching active lint batch to commit")

    committed = state.setdefault("page_hashes", {})
    processed = set()
    for item in active.get("pages", []):
        rel = item["path"]
        if rel in pages and pages[rel]["hash"] == item["hash"]:
            committed[rel] = item["hash"]
            processed.add(rel)
    for rel in active.get("removed_pages", []):
        committed.pop(rel, None)
    for item in active.get("pairs", []):
        state.setdefault("checked_pairs", {})[pair_key(item["left"], item["right"])] = item["signature"]
    state["known_findings"] = sorted(set(state.get("known_findings", [])) | set(
        active.get("finding_fingerprints", [])
    ))

    state["pending_pages"] = [
        rel for rel in state.get("pending_pages", []) if rel not in processed and rel in pages
    ]
    state["active_batch"] = None
    state["last_completed_at"] = datetime.now(timezone.utc).isoformat()
    if not state["pending_pages"]:
        state["bootstrap_complete"] = True
    write_json(args.state_file, state)
    json.dump({
        "committed_batch": args.batch_id,
        "processed_pages": sorted(processed),
        "remaining_pages": len(state["pending_pages"]),
        "bootstrap_complete": state["bootstrap_complete"],
    }, sys.stdout, indent=2)
    sys.stdout.write("\n")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Create or resume a lint batch")
    scan_parser.add_argument("wiki_dir")
    scan_parser.add_argument("--state-file", required=True)
    scan_parser.add_argument("--max-pages", type=int, default=15)
    scan_parser.add_argument("--top-k", type=int, default=3)
    scan_parser.add_argument("--staleness-days", type=int)
    scan_parser.set_defaults(func=scan)

    commit_parser = subparsers.add_parser("commit", help="Commit a completed lint batch")
    commit_parser.add_argument("wiki_dir")
    commit_parser.add_argument("--state-file", required=True)
    commit_parser.add_argument("--batch-id", required=True)
    commit_parser.set_defaults(func=commit)
    return parser


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
