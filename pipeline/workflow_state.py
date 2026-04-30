"""KBState — typed definition of the knowledge-base pipeline workflow state.

This module provides the data structure that LangGraph nodes will read and
write.  It does *not* import langgraph; it only defines the shape of the
state dict so nodes can be built independently.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypedDict


class KBState(TypedDict, total=False):
    """Workflow state shared across all pipeline nodes.

    Fields are all optional at creation time so nodes can populate them
    incrementally.  Consumers should guard against missing keys with
    ``.get()`` or explicit ``key in state`` checks.
    """

    # ── Input / configuration ────────────────────────────────────────
    sources: list[str]
    """Data sources to collect from, e.g. ``['github']`` or ``['github', 'rss']``."""

    limit: int
    """Maximum items to collect per source."""

    provider: str | None
    """LLM provider for analysis (``deepseek``, ``qwen``, ``openai``)."""

    analysis_depth: str
    """Analysis tier: ``normal`` or ``deep``."""

    dry_run: bool
    """Skip writing article files when ``True``."""

    # ── Timestamp ─────────────────────────────────────────────────────
    collected_at: str
    """ISO 8601 UTC timestamp set once at pipeline start."""

    # ── Intermediate data ─────────────────────────────────────────────
    raw_items: dict[str, list[dict[str, Any]]]
    """source name → list of raw collected items."""

    analyzed_items: dict[str, list[dict[str, Any]]]
    """source name → list of analysed item dicts."""

    articles: dict[str, list[dict[str, Any]]]
    """source name → list of standard-format article dicts."""

    # ── Review / quality gate ─────────────────────────────────────────
    review_status: str
    """Current review phase: ``pending`` → ``reviewed`` → ``passed`` | ``failed``."""

    review_findings: list[dict[str, Any]]
    """List of findings dicts from the Supervisor agent."""

    # ── Outputs ───────────────────────────────────────────────────────
    saved_paths: list[str]
    """File-system paths where articles were written."""

    stats: dict[str, Any]
    """Aggregated metrics produced by the pipeline."""

    # ── Error tracking ────────────────────────────────────────────────
    errors: list[str]
    """Non-fatal error messages collected during execution."""


def create_initial_state(
    sources: list[str] | None = None,
    limit: int = 5,
    provider: str | None = None,
    analysis_depth: str = "normal",
    dry_run: bool = False,
) -> KBState:
    """Build a fresh KBState with sensible defaults.

    All mutable fields (lists, dicts) are newly created on each call so
    state objects cannot accidentally share references.
    """
    return KBState(
        sources=sources if sources is not None else ["github"],
        limit=limit,
        provider=provider,
        analysis_depth=analysis_depth,
        dry_run=dry_run,
        collected_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        raw_items={},
        analyzed_items={},
        articles={},
        review_status="pending",
        review_findings=[],
        saved_paths=[],
        stats={},
        errors=[],
    )
