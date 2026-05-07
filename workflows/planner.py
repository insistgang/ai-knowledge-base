"""Planner Agent — dynamic strategy selection based on target count.

Decides collection volume, relevance threshold, and max review iterations
before the pipeline starts, adapting to the user's appetite for depth.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pipeline.workflow_state import KBState

logger = logging.getLogger(__name__)

DEFAULT_TARGET = 10

STRATEGIES = {
    "lite": {
        "per_source_limit": 5,
        "relevance_threshold": 0.7,
        "max_iterations": 1,
        "rationale": "目标 < 10 条，轻量采集，快速产出，仅一轮审核。",
    },
    "standard": {
        "per_source_limit": 10,
        "relevance_threshold": 0.5,
        "max_iterations": 2,
        "rationale": "目标 10-19 条，标准采集量，两轮审核迭代。",
    },
    "full": {
        "per_source_limit": 20,
        "relevance_threshold": 0.4,
        "max_iterations": 3,
        "rationale": "目标 ≥ 20 条，全面采集，低过滤，最严审核（三轮）。",
    },
}


def plan_strategy(target_count: int | None = None) -> dict[str, Any]:
    """Select a collection strategy based on the target item count.

    Args:
        target_count: Desired number of items.  Reads
            ``PLANNER_TARGET_COUNT`` from environment if not given,
            falling back to ``10``.

    Returns:
        Strategy dict with ``per_source_limit``, ``relevance_threshold``,
        ``max_iterations``, and ``rationale``.
    """
    if target_count is None:
        target_count = int(os.getenv("PLANNER_TARGET_COUNT", str(DEFAULT_TARGET)))

    if target_count < 10:
        plan = dict(STRATEGIES["lite"])
    elif target_count < 20:
        plan = dict(STRATEGIES["standard"])
    else:
        plan = dict(STRATEGIES["full"])

    plan["target_count"] = target_count
    logger.info("Planner: strategy=%s target=%d limit=%d",
                "lite" if target_count < 10 else "standard" if target_count < 20 else "full",
                target_count, plan["per_source_limit"])

    return plan


def planner_node(state: KBState) -> KBState:
    """LangGraph node: select strategy and annotate the state.

    Reads ``state["limit"]`` as the target count (or falls back to
    ``PLANNER_TARGET_COUNT`` / ``10``).
    """
    target = state.get("limit", DEFAULT_TARGET)
    plan = plan_strategy(target)

    return {
        **state,  # type: ignore[typeddict-item]
        "plan": plan,
        "limit": plan["per_source_limit"],
        "max_iterations": plan["max_iterations"],
    }
