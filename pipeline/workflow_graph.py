"""LangGraph workflow graph builder for the knowledge-base pipeline.

Wires together the state, nodes, and routing functions defined in the
other ``pipeline.workflow_*`` modules.  The returned compiled graph can
be invoked directly or exposed via an MCP tool / web endpoint.
"""

from __future__ import annotations

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


def build_workflow_graph():
    """Construct and compile the 5-node LangGraph workflow.

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
    graph.add_node("collect", collect_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("organize", organize_node)
    graph.add_node("supervise", supervise_node)
    graph.add_node("save", save_node)

    # ── Entry ─────────────────────────────────────────────────────────
    graph.set_entry_point("collect")

    # ── Edges ─────────────────────────────────────────────────────────

    # collect → analyze | supervise
    graph.add_conditional_edges(
        "collect",
        should_continue_after_collect,
        {"analyze": "analyze", "supervise": "supervise"},
    )

    # analyze → organize | supervise
    graph.add_conditional_edges(
        "analyze",
        should_continue_after_analyze,
        {"organize": "organize", "supervise": "supervise"},
    )

    # organize → supervise
    graph.add_edge("organize", "supervise")

    # supervise → save | revise(END) | stop(END)
    graph.add_conditional_edges(
        "supervise",
        route_after_supervisor,
        {"save": "save", "revise": END, "stop": END},
    )

    # save → END
    graph.add_edge("save", END)

    return graph.compile()
