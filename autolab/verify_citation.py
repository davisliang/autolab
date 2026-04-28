#!/usr/bin/env python3
"""Score how strongly a claim matches a candidate arXiv paper.

Method:
  1. Fetch the candidate paper's title + abstract via Hugging Face Papers API.
  2. Compute a fuzzy-token-set ratio (rapidfuzz) between claim and (title || abstract).
  3. Return a normalized score in [0, 1].

Usage:
    python -m autolab.verify_citation \
        --claim "Per-layer LR scaling outperforms uniform LR on small MNIST MLPs" \
        --candidate-arxiv-id 2412.00123

Prints JSON: {arxiv_id, title, score_title, score_abstract, score_combined}.

Score interpretation (informal):
  >= 0.85: same idea, likely duplicative
  0.50-0.85: related, citable
  < 0.50: tangential
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET

import httpx
from rapidfuzz import fuzz


def fetch_meta_arxiv(arxiv_id: str) -> dict:
    """Fallback to arxiv.org Atom API for title + summary."""
    bare = re.sub(r"v\d+$", "", arxiv_id)
    with httpx.Client(timeout=20.0, follow_redirects=True) as c:
        r = c.get(f"http://export.arxiv.org/api/query?id_list={bare}")
        if r.status_code != 200:
            return {"title": "", "summary": "", "_source": f"arxiv_status_{r.status_code}"}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return {"title": "", "summary": "", "_source": "arxiv_parse_error"}
    entry = root.find("a:entry", ns)
    if entry is None:
        return {"title": "", "summary": "", "_source": "arxiv_no_entry"}
    title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
    summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
    return {"title": title, "summary": summary, "_source": "arxiv"}


def fetch_meta(arxiv_id: str) -> dict:
    with httpx.Client(timeout=20.0, follow_redirects=True) as c:
        r = c.get(f"https://huggingface.co/api/papers/{arxiv_id}")
        if r.status_code == 200:
            try:
                meta = r.json()
                if meta.get("title") or meta.get("summary"):
                    meta.setdefault("_source", "hf")
                    return meta
            except json.JSONDecodeError:
                pass
    return fetch_meta_arxiv(arxiv_id)


def score(claim: str, title: str, abstract: str) -> dict:
    s_title = fuzz.token_set_ratio(claim, title or "") / 100.0
    s_abs = fuzz.token_set_ratio(claim, abstract or "") / 100.0
    if title.strip():
        combined = 0.6 * s_title + 0.4 * s_abs
    else:
        combined = s_abs
    return {
        "score_title": round(s_title, 4),
        "score_abstract": round(s_abs, 4),
        "score_combined": round(combined, 4),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", required=True)
    ap.add_argument("--candidate-arxiv-id", required=True)
    args = ap.parse_args()

    meta = fetch_meta(args.candidate_arxiv_id)
    title = meta.get("title", "") or ""
    abstract = meta.get("summary", "") or ""
    s = score(args.claim, title, abstract)

    out = {
        "arxiv_id": args.candidate_arxiv_id,
        "title": title,
        **s,
        "verifier_method": "title-match-rapidfuzz",
    }
    print(json.dumps(out))


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
