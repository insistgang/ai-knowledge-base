"""Tests for workflow_runner."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pipeline.workflow_state import KBState


class RunWorkflowTest(unittest.TestCase):
    """Verify run_workflow delegates correctly to state, graph, and invoke."""

    def _make_mock_graph(self, return_state: KBState) -> MagicMock:
        """Return a mock that behaves like a compiled LangGraph graph."""
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = return_state
        return mock_graph

    def test_passes_args_to_create_initial_state_via_build(self) -> None:
        from pipeline.workflow_runner import run_workflow

        mock_graph = self._make_mock_graph({})

        with patch("pipeline.workflow_runner.create_initial_state") as mock_create, \
             patch("pipeline.workflow_runner.build_workflow_graph", return_value=mock_graph):
            mock_create.return_value = {"collected_at": "2026-04-30T00:00:00Z"}

            run_workflow(
                sources=["github", "rss"],
                limit=10,
                provider="deepseek",
                analysis_depth="deep",
                dry_run=True,
            )

        mock_create.assert_called_once_with(
            sources=["github", "rss"],
            limit=10,
            provider="deepseek",
            analysis_depth="deep",
            dry_run=True,
        )

    def test_calls_build_workflow_graph(self) -> None:
        from pipeline.workflow_runner import run_workflow

        mock_graph = self._make_mock_graph({})

        with patch("pipeline.workflow_runner.create_initial_state", return_value={}), \
             patch("pipeline.workflow_runner.build_workflow_graph", return_value=mock_graph) as mock_build:
            run_workflow()

        mock_build.assert_called_once()

    def test_calls_graph_invoke(self) -> None:
        from pipeline.workflow_runner import run_workflow

        state = {"collected_at": "2026-04-30T00:00:00Z"}
        mock_graph = self._make_mock_graph(state)

        with patch("pipeline.workflow_runner.create_initial_state", return_value=state), \
             patch("pipeline.workflow_runner.build_workflow_graph", return_value=mock_graph):
            result = run_workflow()

        mock_graph.invoke.assert_called_once()
        call_args = mock_graph.invoke.call_args
        self.assertIs(call_args[0][0], state)
        self.assertEqual(call_args[1]["config"]["recursion_limit"], 20)
        self.assertEqual(result, state)

    def test_propagates_runtime_error(self) -> None:
        from pipeline.workflow_runner import run_workflow

        with patch("pipeline.workflow_runner.create_initial_state", return_value={}), \
             patch("pipeline.workflow_runner.build_workflow_graph",
                   side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError) as ctx:
                run_workflow()

        self.assertIn("boom", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
