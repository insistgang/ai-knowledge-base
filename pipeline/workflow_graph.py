"""LangGraph workflow graph builder for the knowledge-base pipeline.

Wires together the state, nodes, and routing functions defined in the
other ``pipeline.workflow_*`` and ``workflows.*`` modules.  The returned
compiled graph can be invoked directly or exposed via an MCP tool / web
endpoint.

Node inventory:
    plan  →  collect  →  analyze  →  review  →  organize  →  supervise → save  → END
                revise  →   ↑
                human_flag → END
"""

from __future__ import annotations

from typing import Any

from pipeline.workflow_nodes import (
    analyze_node,
    collect_node,
    organize_node,
    save_node,
    supervise_node,
)
from pipeline.workflow_routes import (
    route_after_supervisor,
    should_continue_after_analyze,
    should_continue_after_collect,
)
from pipeline.workflow_state import KBState
from workflows.human_flag import human_flag_node
from workflows.planner import planner_node
from workflows.reviewer import review_node
from workflows.reviser import revise_node

DEFAULT_MAX_ITERATIONS = 3


# ── 3-way route after review ──────────────────────────────────────────

def route_after_review(state: KBState) -> str:
    """Decide next step after the LLM reviewer node.

    Returns
    -------
    str
        ``"organize"``   – review passed, proceed to organisation
        ``"revise"``     – review failed & iterations remain
        ``"human_flag"`` – review failed & loop exhausted
    """
    review_passed: bool = state.get("review_passed", False)
    iteration: int = state.get("iteration", 0)
    max_iterations: int = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)

    if review_passed:
        return "organize"

    if iteration < max_iterations:
        return "revise"

    return "human_flag"


# ── Graph builder ─────────────────────────────────────────────────────

def build_workflow_graph():
    """Construct and compile the full LangGraph workflow.

    Returns
    -------
    langgraph.graph.graph.CompiledGraph
        A runnable workflow graph.

    Raises
    ------
    RuntimeError
        If ``langgraph`` is not installed.
    """
    try:
        from langgraph.graph import END, StateGraph  # noqa: E402
    except ImportError:
        raise RuntimeError(
            "langgraph is required to build the workflow graph. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from None

    graph = StateGraph(KBState)

    # ── Nodes ─────────────────────────────────────────────────────────
    graph.add_node("plan", planner_node)
    graph.add_node("collect", collect_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("review", review_node)
    graph.add_node("revise", revise_node)
    graph.add_node("organize", organize_node)
    graph.add_node("supervise", supervise_node)
    graph.add_node("save", save_node)
    graph.add_node("human_flag", human_flag_node)

    # ── Entry ─────────────────────────────────────────────────────────
    graph.set_entry_point("plan")

    # ── Edges ─────────────────────────────────────────────────────────

    # plan → collect
    graph.add_edge("plan", "collect")

    # collect → analyze | supervise (V4 legacy path)
    graph.add_conditional_edges(
        "collect",
        should_continue_after_collect,
        {"analyze": "analyze", "supervise": "supervise"},
    )

    # analyze → review | supervise
    graph.add_conditional_edges(
        "analyze",
        should_continue_after_analyze,
        {"review": "review", "supervise": "supervise"},
    )

    # review → organize | revise | human_flag  (3-way)
    graph.add_conditional_edges(
        "review",
        route_after_review,
        {"organize": "organize", "revise": "revise", "human_flag": "human_flag"},
    )

    # revise → review (loop)
    graph.add_edge("revise", "review")

    # organize → supervise
    graph.add_edge("organize", "supervise")

    # supervise → save | revise(END) | stop(END)
    graph.add_conditional_edges(
        "supervise",
        route_after_supervisor,
        {"save": "save", "revise": END, "stop": END},
    )

    # human_flag → END
    graph.add_edge("human_flag", END)

    # save → END
    graph.add_edge("save", END)

    return graph.compile()
