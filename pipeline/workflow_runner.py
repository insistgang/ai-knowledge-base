"""Workflow runner — thin entry point that builds state, graph, and invokes.

Usage::

    from pipeline.workflow_runner import run_workflow

    state = run_workflow(sources=["github"], limit=3, dry_run=True)
    print(state["review_status"])
"""

from __future__ import annotations

from pipeline.workflow_graph import build_workflow_graph
from pipeline.workflow_state import KBState, create_initial_state


def run_workflow(
    sources: list[str] | None = None,
    limit: int = 5,
    provider: str | None = None,
    analysis_depth: str = "normal",
    dry_run: bool = False,
) -> KBState:
    """Build and execute the full knowledge-base pipeline workflow.

    Args:
        sources: Data sources to collect from (default: ``["github"]``).
        limit: Max items per source.
        provider: LLM provider override for analysis.
        analysis_depth: ``"normal"`` or ``"deep"``.
        dry_run: Skips article file writes when ``True``.

    Returns:
        The final ``KBState`` after all nodes have completed.

    Raises:
        RuntimeError: If ``langgraph`` is not installed.
    """
    state = create_initial_state(
        sources=sources,
        limit=limit,
        provider=provider,
        analysis_depth=analysis_depth,
        dry_run=dry_run,
    )
    graph = build_workflow_graph()
    return graph.invoke(state, config={"recursion_limit": 20})
