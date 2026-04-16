"""Tests for the TF-IDF SOP retriever."""
from __future__ import annotations

from pathlib import Path

from modules import rag


def test_empty_query_returns_nothing(sop_dir: Path):
    assert rag.search_sops("", sop_dir=sop_dir) == []


def test_unknown_sop_directory_returns_nothing(tmp_path: Path):
    missing = tmp_path / "nope"
    assert rag.search_sops("temperature", sop_dir=missing) == []


def test_list_indexed_documents_skips_readme(sop_dir: Path):
    docs = rag.list_indexed_documents(sop_dir=sop_dir)
    paths = {Path(d["path"]).name for d in docs}
    assert "README.md" not in paths
    assert "sop_one.md" in paths
    assert "sop_two.md" in paths


def test_temperature_query_prefers_temperature_doc(sop_dir: Path):
    results = rag.search_sops("chilled storage temperature excursion", sop_dir=sop_dir)
    assert results, "expected at least one hit"
    best = results[0]
    assert "sop_one" in best.path.lower() or "temperature" in best.title.lower()
    assert best.snippet
    assert best.score > 0


def test_traceability_query_prefers_traceability_doc(sop_dir: Path):
    results = rag.search_sops("raw material supplier lot recall", sop_dir=sop_dir)
    assert results
    best = results[0]
    assert "sop_two" in best.path.lower() or "traceability" in best.title.lower()


def test_top_k_caps_results(sop_dir: Path):
    # sop_dir only has two indexable docs; top_k=1 must return at most one.
    hits = rag.search_sops("traceability", sop_dir=sop_dir, top_k=1)
    assert len(hits) <= 1


def test_naive_fallback_when_sklearn_missing(monkeypatch, sop_dir: Path):
    monkeypatch.setattr(rag, "_SKLEARN_AVAILABLE", False)
    hits = rag.search_sops("traceability", sop_dir=sop_dir)
    assert hits, "naive path must still return results"
    assert all(h.score >= 0 for h in hits)
