"""Human Flag node — writes flagged items for manual review.

When the review/revision loop exceeds the iteration ceiling this node
persists the problem entries to ``knowledge/pending_review/`` so a human
can inspect and resolve them later.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.workflow_state import KBState

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PENDING_DIR = PROJECT_ROOT / "knowledge" / "pending_review"


def _flag_filename() -> str:
    """Generate a unique filename for the flag file."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"flag-{ts}.json"


def human_flag_node(state: KBState) -> KBState:
    """Write flagged analyses to ``knowledge/pending_review/`` and signal
    that human intervention is required.

    This node is the safety net when the ``review → revise`` loop
    exceeds the maximum allowed iterations.  Instead of looping forever
    it archives the current state for an operator to triage.

    Args:
        state: Current workflow state.

    Returns:
        Updated state with ``needs_human_review`` set and the flag
        file path appended to ``saved_paths``.
    """
    PENDING_DIR.mkdir(parents=True, exist_ok=True)

    analyses = state.get("analyses", [])
    review_feedback = state.get("review_feedback", {})
    iteration = state.get("iteration", 0)
    errors = list(state.get("errors") or [])

    payload = {
        "flagged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "iteration": iteration,
        "analyses_count": len(analyses),
        "analyses": analyses,
        "review_feedback": review_feedback,
        "errors": errors,
    }

    path = PENDING_DIR / _flag_filename()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.warning(
        "HumanFlag: written %d analyses to %s for manual review",
        len(analyses), path,
    )

    saved_paths: list[str] = list(state.get("saved_paths") or [])
    saved_paths.append(str(path))

    return {
        **state,  # type: ignore[typeddict-item]
        "needs_human_review": True,
        "saved_paths": saved_paths,
    }
