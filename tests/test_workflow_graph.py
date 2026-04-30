"""Tests for the LangGraph workflow graph builder."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class BuildWorkflowGraphDependencyTest(unittest.TestCase):
    """Verify correct error handling when langgraph is missing."""

    def test_raises_runtime_error_when_langgraph_not_installed(self) -> None:
        with patch.dict("sys.modules", {"langgraph": None}):
            from pipeline.workflow_graph import build_workflow_graph

            with self.assertRaises(RuntimeError) as ctx:
                build_workflow_graph()

        msg = str(ctx.exception)
        self.assertIn("langgraph", msg)
        self.assertIn("pip install -r requirements.txt", msg)

    def test_requirements_contains_langgraph(self) -> None:
        req_path = PROJECT_ROOT / "requirements.txt"
        content = req_path.read_text(encoding="utf-8")
        self.assertIn("langgraph", content)


class BuildWorkflowGraphIntegrationTest(unittest.TestCase):
    """Integration tests that require langgraph to be installed.

    These are skipped gracefully when langgraph is absent.
    """

    def test_graph_builds_and_returns_non_none(self) -> None:
        try:
            from pipeline.workflow_graph import build_workflow_graph
        except RuntimeError:
            self.skipTest("langgraph not installed – skipping integration test")

        graph = build_workflow_graph()
        self.assertIsNotNone(graph)

    def test_graph_has_all_five_nodes(self) -> None:
        try:
            from pipeline.workflow_graph import build_workflow_graph
        except RuntimeError:
            self.skipTest("langgraph not installed – skipping integration test")

        graph = build_workflow_graph()
        expected = {"collect", "analyze", "organize", "supervise", "save"}
        # CompiledGraph stores nodes in graph._all_nodes or graph.nodes
        node_names = set(getattr(graph, "nodes", {}).keys())
        missing = expected - node_names
        self.assertFalse(missing, f"Missing nodes: {missing}")

    def test_graph_can_invoke_minimal_state(self) -> None:
        try:
            from pipeline.workflow_graph import build_workflow_graph
        except RuntimeError:
            self.skipTest("langgraph not installed – skipping integration test")

        from pipeline.workflow_state import create_initial_state

        # Mock the collectors so we don't hit the network
        graph = build_workflow_graph()
        state = create_initial_state(sources=["github"], limit=1)

        with patch("pipeline.workflow_nodes.COLLECTORS", {
            "github": lambda limit=5: [{"name": "test/repo", "url": "https://example.com",
                                         "summary": "ok", "stars": 1, "language": "Python",
                                         "topics": ["agent"]}]
        }), patch("pipeline.workflow_nodes.analyze", return_value=[{
            "summary": "A test project",
            "tech_highlights": ["h1"],
            "relevance_score": 7,
            "reason": "ok",
            "suggested_tags": ["agent"],
            "audience": ["developer"],
            "risks": [],
        }]), patch("pipeline.workflow_nodes.organize", return_value=[{
            "id": "test-001",
            "title": "Test",
            "source_url": "https://example.com",
            "summary": "ok",
            "status": "draft",
            "source": "github-trending",
            "collected_at": state["collected_at"],
            "analysis": {"tech_highlights": [], "relevance_score": 7, "reason": "", "risks": []},
            "tags": ["agent"],
            "audience": ["developer"],
        }]), patch("pipeline.workflow_nodes.save_raw", return_value="raw.json"), \
           patch("pipeline.workflow_nodes.save_articles", return_value=["art.json"]):
            result = graph.invoke(state, config={"recursion_limit": 10})

        self.assertIsNotNone(result)
        self.assertEqual(result.get("review_status"), "pass")


if __name__ == "__main__":
    unittest.main()
