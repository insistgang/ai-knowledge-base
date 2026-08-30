"""Workflow node functions that operate on KBState.

Each node is a pure function (state in → state out) that delegates to the
existing pipeline layer.  No langgraph dependency — nodes are designed to be
wired later with ``langgraph.graph.StateGraph``.
"""

from __future__ import annotations

from typing import Any

from pipeline.cost_tracker import CostTracker
from pipeline.workflow_state import KBState

# Reuse existing pipeline internals without duplicating logic.
from pipeline.pipeline import (  # noqa: E402
    COLLECTORS,
    analyze,
    normalize_analysis_depth,
    organize,
    read_daily_budget,
    read_model_routes,
    save_articles,
    save_cost_metrics,
    save_raw,
    select_analysis_model,
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
    tracker = state.get("llm_cost_tracker")
    if not isinstance(tracker, CostTracker):
        tracker = CostTracker(budget_usd=read_daily_budget())

    analysis_depth = normalize_analysis_depth(
        str(state.get("analysis_depth", "normal"))
    )
    model_routes = read_model_routes(provider)
    analysis_model = select_analysis_model(analysis_depth, model_routes)

    for source, items in raw_items.items():
        if not items:
            analyzed_items[source] = []
            stats.setdefault(source, {})["analyzed"] = 0
            continue
        try:
            result = analyze(
                source,
                items,
                provider=provider,
                cost_tracker=tracker,
                model_name=analysis_model,
            )
            analyzed_items[source] = result
            stats.setdefault(source, {})["analyzed"] = len(result)
        except Exception as exc:
            errors.append(f"Analysis failed for {source}: {exc}")
            stats.setdefault(source, {})["analyzed"] = 0

    analyses = [
        analysis
        for source in raw_items
        for analysis in analyzed_items.get(source, [])
    ]
    stats["_model_route"] = {
        "analysis_depth": analysis_depth,
        "analysis_model": analysis_model,
        "routes": model_routes,
    }

    return {
        **state,
        "analyzed_items": analyzed_items,
        "analyses": analyses,
        "llm_cost_tracker": tracker,
        "stats": stats,
        "errors": errors,
    }


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
    """Write reviewed raw data, articles, and cost metrics to disk."""
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
    errors: list[str] = list(state.get("errors") or [])
    stats: dict[str, Any] = dict(state.get("stats") or {})
    review_verified = bool(state.get("review_verified", False))
    review_passed = bool(state.get("review_passed", False))

    articles_to_save: dict[str, list[dict[str, Any]]] = {}
    for source, source_articles in articles.items():
        articles_to_save[source] = []
        for article in source_articles:
            normalized = dict(article)
            if (
                review_verified
                and review_passed
                and normalized.get("status") == "draft"
            ):
                normalized["status"] = "reviewed"
            articles_to_save[source].append(normalized)

    for source in sources:
        if source in raw_items and raw_items[source]:
            try:
                raw_path = save_raw(source, collected_at, raw_items[source], dry_run=dry_run)
                saved_paths.append(str(raw_path))
            except Exception as exc:
                errors.append(f"Raw save failed for {source}: {exc}")

        if source in articles_to_save and articles_to_save[source]:
            try:
                article_paths = save_articles(
                    source,
                    collected_at,
                    articles_to_save[source],
                    dry_run=dry_run,
                )
                saved_paths.extend(str(p) for p in article_paths)
            except Exception as exc:
                errors.append(f"Article save failed for {source}: {exc}")

    tracker = state.get("llm_cost_tracker")
    if isinstance(tracker, CostTracker):
        try:
            metrics_path = save_cost_metrics(
                collected_at=collected_at,
                cost_tracker=tracker,
                dry_run=dry_run,
            )
            saved_paths.append(str(metrics_path))
            stats["_cost"] = {
                "metrics_path": str(metrics_path),
                "budget": tracker.budget_status(),
                "total": tracker.total(),
                "runs": tracker.summarize_runs(),
            }
        except Exception as exc:
            errors.append(f"Cost metrics save failed: {exc}")

    return {
        **state,
        "articles": articles_to_save,
        "saved_paths": saved_paths,
        "stats": stats,
        "errors": errors,
    }
