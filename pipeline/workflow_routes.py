"""Workflow routing / conditional-edge functions.

Each function inspects the current KBState and returns the name of the
next node (a plain string).  LangGraph requires these to be pure
functions (state → str); we comply with that contract even though
langgraph is not yet imported.
"""

from __future__ import annotations

from typing import Any

from pipeline.workflow_state import KBState


def _has_errors(state: KBState) -> bool:
    """True when the error list is non-empty."""
    return bool(state.get("errors") or [])


def _source_items_non_empty(items: dict[str, list[dict[str, Any]]]) -> bool:
    """True when at least one source has ≥ 1 item."""
    return any(v for v in (items or {}).values())


# ── should_continue_after_collect ─────────────────────────────────────

def should_continue_after_collect(state: KBState) -> str:
    """Decide the next step after the collection node.

    Returns
    -------
    str
        ``"analyze"`` if collection produced usable data,
        ``"supervise"`` otherwise.
    """
    if _has_errors(state):
        return "supervise"
    raw_items = state.get("raw_items") or {}
    if not raw_items or not _source_items_non_empty(raw_items):
        return "supervise"
    return "analyze"


# ── should_continue_after_analyze ─────────────────────────────────────

def should_continue_after_analyze(state: KBState) -> str:
    """Decide the next step after the analysis node.

    Returns
    -------
    str
        ``"organize"`` if analysis produced results,
        ``"supervise"`` otherwise.
    """
    if _has_errors(state):
        return "supervise"
    analyzed_items = state.get("analyzed_items") or {}
    if not analyzed_items or not _source_items_non_empty(analyzed_items):
        return "supervise"
    return "organize"


# ── route_after_supervisor ────────────────────────────────────────────

def route_after_supervisor(state: KBState) -> str:
    """Decide the next step after the supervisor node.

    Returns
    -------
    str
        ``"save"`` if the review passed,
        ``"revise"`` if manual revision is needed,
        ``"stop"`` if the pipeline is blocked.
    """
    review_status: str = state.get("review_status", "pending")

    if review_status == "pass":
        return "save"

    if _has_errors(state):
        return "stop"

    if review_status == "needs_revision":
        return "revise"
    if review_status == "blocked":
        return "stop"

    # Any unrecognised status → stop for safety
    return "stop"
