#!/usr/bin/env python3
"""Cache a paper's markdown body and metadata under papers/.

Sources (in order):
  1. https://huggingface.co/papers/{id}.md  (markdown body, when available)
  2. https://huggingface.co/api/papers/{id} (structured metadata)
  3. arxiv.org/abs/{id} (fallback if HF has no markdown)

Usage:
    python -m autolab.fetch_paper 2412.00123
    python -m autolab.fetch_paper https://arxiv.org/abs/2412.00123
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import httpx

from autolab.paths import papers_dir


def parse_id(s: str) -> str:
    s = s.strip()
    # HF / arXiv abs/pdf URLs and bare IDs
    m = re.search(r"(?:papers/|abs/|pdf/)([\d.]+(?:v\d+)?)", s)
    if m:
        return m.group(1).rstrip(".")
    m = re.fullmatch(r"\d{4}\.\d{4,5}(?:v\d+)?", s)
    if m:
        return s
    raise SystemExit(f"Could not parse arXiv id from: {s}")


def _arxiv_atom_meta(c: httpx.Client, arxiv_id: str) -> dict | None:
    """Fallback metadata from arxiv.org Atom feed."""
    import xml.etree.ElementTree as ET

    bare = re.sub(r"v\d+$", "", arxiv_id)
    r = c.get(f"http://export.arxiv.org/api/query?id_list={bare}")
    if r.status_code != 200:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
    summary = (entry.findtext("a:summary", default="", namespaces=ns) or "").strip()
    published = entry.findtext("a:published", default="", namespaces=ns) or ""
    authors = [
        {"name": (a.findtext("a:name", default="", namespaces=ns) or "").strip()}
        for a in entry.findall("a:author", ns)
    ]
    return {
        "title": title,
        "summary": summary,
        "publishedAt": published,
        "authors": authors,
        "_source": "arxiv",
    }


def fetch(arxiv_id: str) -> dict:
    pdir = papers_dir()
    pdir.mkdir(parents=True, exist_ok=True)
    md_path = pdir / f"{arxiv_id}.md"
    meta_path = pdir / f"{arxiv_id}.meta.json"

    out = {"arxiv_id": arxiv_id, "md_path": str(md_path), "meta_path": str(meta_path)}

    with httpx.Client(timeout=30.0, follow_redirects=True) as c:
        if not md_path.exists():
            r = c.get(f"https://huggingface.co/papers/{arxiv_id}.md")
            if r.status_code == 200 and r.text.strip():
                md_path.write_text(r.text)
                out["body_source"] = "hf_markdown"
            else:
                meta = _arxiv_atom_meta(c, arxiv_id)
                if meta and (meta.get("title") or meta.get("summary")):
                    md_path.write_text(
                        f"# {meta['title']}\n\n_arxiv {arxiv_id} (HF papers had no entry; arxiv abstract fallback)_\n\n## Abstract\n\n{meta['summary']}\n"
                    )
                    out["body_source"] = "arxiv_abstract_fallback"
                else:
                    md_path.write_text(f"# arxiv {arxiv_id}\n\n_(no body available)_\n")
                    out["body_source"] = "missing"
        else:
            out["body_source"] = "cached"

        if not meta_path.exists():
            r = c.get(f"https://huggingface.co/api/papers/{arxiv_id}")
            if r.status_code == 200:
                try:
                    meta = r.json()
                    if meta.get("title") or meta.get("summary"):
                        meta.setdefault("_source", "hf")
                        meta_path.write_text(json.dumps(meta, indent=2))
                        out["meta_source"] = "hf_api"
                    else:
                        meta = _arxiv_atom_meta(c, arxiv_id)
                        if meta:
                            meta_path.write_text(json.dumps(meta, indent=2))
                            out["meta_source"] = "arxiv_fallback"
                        else:
                            out["meta_source"] = "none"
                except json.JSONDecodeError:
                    out["meta_source"] = "hf_api_invalid_json"
            else:
                meta = _arxiv_atom_meta(c, arxiv_id)
                if meta:
                    meta_path.write_text(json.dumps(meta, indent=2))
                    out["meta_source"] = "arxiv_fallback"
                else:
                    out["meta_source"] = f"hf_api_status_{r.status_code}_no_arxiv"
        else:
            out["meta_source"] = "cached"

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper", help="arXiv id or HF/arXiv URL")
    args = ap.parse_args()
    aid = parse_id(args.paper)
    result = fetch(aid)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
