"""Workflow runner — thin entry point that builds state, graph, and invokes.

Usage::

    from pipeline.workflow_runner import run_workflow

    state = run_workflow(sources=["github"], limit=3, dry_run=True)
    print(state["review_status"])
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from pipeline.workflow_graph import build_workflow_graph
from pipeline.workflow_state import KBState, create_initial_state

logger = logging.getLogger(__name__)


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


def build_parser() -> argparse.ArgumentParser:
    """Build the production workflow CLI parser."""
    parser = argparse.ArgumentParser(
        description="Run the LangGraph AI knowledge-base workflow",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["github"],
        choices=["github", "rss"],
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--provider",
        choices=["deepseek", "qwen", "openai"],
        default=None,
    )
    parser.add_argument(
        "--analysis-depth",
        choices=["normal", "deep"],
        default=os.getenv("AI_KB_ANALYSIS_DEPTH", "normal"),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the production LangGraph workflow from the command line."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        state = run_workflow(
            sources=args.sources,
            limit=args.limit,
            provider=args.provider,
            analysis_depth=args.analysis_depth,
            dry_run=args.dry_run,
        )
    except Exception:
        logger.exception("LangGraph workflow failed")
        return 1

    errors = state.get("errors") or []
    total_collected = sum(
        int(source_stats.get("collected", 0))
        for source, source_stats in (state.get("stats") or {}).items()
        if not source.startswith("_") and isinstance(source_stats, dict)
    )
    total_articles = sum(
        len(items) for items in (state.get("articles") or {}).values()
    )
    print(
        "Workflow complete: "
        f"{total_collected} collected, {total_articles} articles, "
        f"review_status={state.get('review_status', 'unknown')}, "
        f"human_review={bool(state.get('needs_human_review', False))}"
    )

    if errors:
        for error in errors:
            logger.error("Workflow error: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
