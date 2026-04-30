"""Workflow node functions that operate on KBState.

Each node is a pure function (state in → state out) that delegates to the
existing pipeline layer.  No langgraph dependency — nodes are designed to be
wired later with ``langgraph.graph.StateGraph``.
"""

from __future__ import annotations

from typing import Any

from pipeline.workflow_state import KBState

# Reuse existing pipeline internals without duplicating logic.
from pipeline.pipeline import (  # noqa: E402
    COLLECTORS,
    analyze,
    organize,
    save_articles,
    save_raw,
)

REQUIRED_ARTICLE_FIELDS = ["id", "title", "source_url", "summary", "status"]


# ── collect_node ──────────────────────────────────────────────────────

def collect_node(state: KBState) -> KBState:
    """Run the collector for each configured source and populate raw_items."""
    sources: list[str] = list(state.get("sources") or ["github"])
    limit: int = state.get("limit", 5)
    raw_items: dict[str, list[dict[str, Any]]] = dict(state.get("raw_items") or {})
    stats: dict[str, Any] = dict(state.get("stats") or {})
    errors: list[str] = list(state.get("errors") or [])

    for source in sources:
        collector = COLLECTORS.get(source)
        if collector is None:
            errors.append(f"Unknown source: {source}")
            stats.setdefault(source, {})["collected"] = 0
            continue
        try:
            items = collector(limit=limit)
            raw_items[source] = items
            stats.setdefault(source, {})["collected"] = len(items)
        except Exception as exc:
            errors.append(f"Collection failed for {source}: {exc}")
            stats.setdefault(source, {})["collected"] = 0

    return {**state, "raw_items": raw_items, "stats": stats, "errors": errors}


# ── analyze_node ──────────────────────────────────────────────────────

def analyze_node(state: KBState) -> KBState:
    """Analyse each source's raw_items and populate analyzed_items."""
    raw_items: dict[str, list[dict[str, Any]]] = state.get("raw_items") or {}
    analyzed_items: dict[str, list[dict[str, Any]]] = dict(state.get("analyzed_items") or {})
    stats: dict[str, Any] = dict(state.get("stats") or {})
    errors: list[str] = list(state.get("errors") or [])
    provider: str | None = state.get("provider")

    for source, items in raw_items.items():
        if not items:
            analyzed_items[source] = []
            stats.setdefault(source, {})["analyzed"] = 0
            continue
        try:
            result = analyze(source, items, provider=provider)
            analyzed_items[source] = result
            stats.setdefault(source, {})["analyzed"] = len(result)
        except Exception as exc:
            errors.append(f"Analysis failed for {source}: {exc}")
            stats.setdefault(source, {})["analyzed"] = 0

    return {**state, "analyzed_items": analyzed_items, "stats": stats, "errors": errors}


# ── organize_node ─────────────────────────────────────────────────────

def organize_node(state: KBState) -> KBState:
    """Transform raw + analysed items into standard article format."""
    raw_items: dict[str, list[dict[str, Any]]] = state.get("raw_items") or {}
    analyzed_items: dict[str, list[dict[str, Any]]] = state.get("analyzed_items") or {}
    collected_at: str = state.get("collected_at", "")
    articles: dict[str, list[dict[str, Any]]] = dict(state.get("articles") or {})
    stats: dict[str, Any] = dict(state.get("stats") or {})
    errors: list[str] = list(state.get("errors") or [])

    for source, raw_list in raw_items.items():
        analyzed_list = analyzed_items.get(source, [])
        if not analyzed_list:
            articles[source] = []
            stats.setdefault(source, {})["articles"] = 0
            continue
        try:
            result = organize(source, collected_at, raw_list, analyzed_list)
            articles[source] = result
            stats.setdefault(source, {})["articles"] = len(result)
        except Exception as exc:
            errors.append(f"Organization failed for {source}: {exc}")
            stats.setdefault(source, {})["articles"] = 0

    return {**state, "articles": articles, "stats": stats, "errors": errors}


# ── supervise_node ────────────────────────────────────────────────────

def supervise_node(state: KBState) -> KBState:
    """Run rule-based quality checks over articles.  No LLM call."""
    errors: list[str] = list(state.get("errors") or [])
    articles: dict[str, list[dict[str, Any]]] = state.get("articles") or {}
    findings: list[dict[str, Any]] = []

    if errors:
        return {
            **state,
            "review_status": "blocked",
            "review_findings": [
                {
                    "severity": "high",
                    "field": "errors",
                    "issue": f"Pipeline encountered {len(errors)} error(s)",
                    "suggestion": "Resolve errors before retrying",
                }
            ],
        }

    review_status: str = "pass"
    for source, source_articles in articles.items():
        for article in source_articles:
            missing = [f for f in REQUIRED_ARTICLE_FIELDS if f not in article]
            if missing:
                review_status = "needs_revision"
                findings.append({
                    "severity": "high",
                    "field": ", ".join(missing),
                    "issue": f"Article '{article.get('id', '?')}' missing fields: {missing}",
                    "suggestion": f"Add: {missing}",
                })

    return {**state, "review_status": review_status, "review_findings": findings}


# ── save_node ─────────────────────────────────────────────────────────

def save_node(state: KBState) -> KBState:
    """Write raw data and articles to disk if review passed."""
    review_status: str = state.get("review_status", "pending")
    if review_status != "pass":
        errors: list[str] = list(state.get("errors") or [])
        errors.append(f"Save blocked: review_status={review_status} (expected 'pass')")
        return {**state, "errors": errors}

    sources: list[str] = list(state.get("sources") or ["github"])
    raw_items: dict[str, list[dict[str, Any]]] = state.get("raw_items") or {}
    articles: dict[str, list[dict[str, Any]]] = state.get("articles") or {}
    collected_at: str = state.get("collected_at", "")
    dry_run: bool = state.get("dry_run", False)
    saved_paths: list[str] = list(state.get("saved_paths") or [])

    for source in sources:
        if source in raw_items and raw_items[source]:
            try:
                raw_path = save_raw(source, collected_at, raw_items[source], dry_run=dry_run)
                saved_paths.append(str(raw_path))
            except Exception as exc:
                saved_paths.append(f"ERROR: raw save failed for {source}: {exc}")

        if source in articles and articles[source]:
            try:
                article_paths = save_articles(
                    source, collected_at, articles[source], dry_run=dry_run
                )
                saved_paths.extend(str(p) for p in article_paths)
            except Exception as exc:
                saved_paths.append(f"ERROR: article save failed for {source}: {exc}")

    return {**state, "saved_paths": saved_paths}
