"""Lightweight TF-IDF retrieval over local SOP / HACCP documents.

Used by the natural-language query interface to surface relevant policy text
alongside factual answers from the database. Deliberately avoids embeddings,
vector stores and remote LLMs so the dashboard still works offline on the
factory floor.

Documents are plain ``.md`` or ``.txt`` files placed under ``docs/sops/``.
The index is rebuilt on demand (cheap for tens of documents) so uploads take
effect immediately.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN_AVAILABLE = True
except ImportError:  # sklearn is optional at runtime
    _SKLEARN_AVAILABLE = False

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOP_DIR = _PROJECT_ROOT / "docs" / "sops"
SUPPORTED_EXTENSIONS = {".md", ".txt"}
SNIPPET_CHARS = 320


@dataclass
class SopHit:
    """A single retrieval result."""

    path: str
    title: str
    score: float
    snippet: str


def _iter_documents(sop_dir: Path) -> list[tuple[Path, str]]:
    docs: list[tuple[Path, str]] = []
    if not sop_dir.exists():
        return docs
    for root, _dirs, files in os.walk(sop_dir):
        for name in sorted(files):
            path = Path(root) / name
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            # Skip the docs/sops/README.md placeholder.
            if path.name.lower() == "readme.md" and path.parent == sop_dir:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if text.strip():
                docs.append((path, text))
    return docs


def _document_title(path: Path, text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or path.stem.replace("-", " ").title()
        if stripped:
            return stripped[:80]
    return path.stem.replace("-", " ").title()


def _build_snippet(text: str, query: str) -> str:
    lowered = text.lower()
    terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
    best = 0
    for term in terms:
        idx = lowered.find(term)
        if idx != -1:
            best = max(0, idx - SNIPPET_CHARS // 2)
            break
    snippet = text[best : best + SNIPPET_CHARS].strip()
    snippet = re.sub(r"\s+", " ", snippet)
    return snippet + ("..." if len(text) > best + SNIPPET_CHARS else "")


def search_sops(query: str, top_k: int = 3, sop_dir: Path | None = None) -> list[SopHit]:
    """Return the most relevant SOP snippets for ``query``.

    Falls back to a naive keyword count when scikit-learn is not installed, so
    callers still get best-effort results on a minimal environment.
    """
    if not query or not query.strip():
        return []

    docs = _iter_documents(sop_dir or DEFAULT_SOP_DIR)
    if not docs:
        return []

    paths = [str(p) for p, _ in docs]
    texts = [t for _, t in docs]
    titles = [_document_title(p, t) for p, t in docs]

    if _SKLEARN_AVAILABLE:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=1,
        )
        matrix = vectorizer.fit_transform(texts + [query])
        doc_vecs = matrix[:-1]
        query_vec = matrix[-1]
        scores = cosine_similarity(query_vec, doc_vecs)[0]
    else:
        terms = [t for t in re.findall(r"\w+", query.lower()) if len(t) > 2]
        scores = []
        for text in texts:
            lowered = text.lower()
            hits = sum(lowered.count(term) for term in terms)
            scores.append(float(hits) / max(len(lowered), 1))

    ranked = sorted(
        zip(paths, titles, texts, scores),
        key=lambda row: row[3],
        reverse=True,
    )

    hits: list[SopHit] = []
    for path, title, text, score in ranked[:top_k]:
        if score <= 0:
            continue
        hits.append(
            SopHit(
                path=path,
                title=title,
                score=float(round(score, 4)),
                snippet=_build_snippet(text, query),
            )
        )
    return hits


def list_indexed_documents(sop_dir: Path | None = None) -> list[dict[str, str]]:
    """Enumerate SOPs currently visible to the retriever (for UI status)."""
    docs = _iter_documents(sop_dir or DEFAULT_SOP_DIR)
    return [
        {
            "path": str(p),
            "title": _document_title(p, t),
            "size_bytes": str(len(t.encode("utf-8"))),
        }
        for p, t in docs
    ]
