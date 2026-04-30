"""Tests for workflow routing functions."""

from __future__ import annotations

import unittest

from pipeline.workflow_routes import (
    route_after_supervisor,
    should_continue_after_analyze,
    should_continue_after_collect,
)
from pipeline.workflow_state import create_initial_state


# ── should_continue_after_collect ─────────────────────────────────────

class ShouldContinueAfterCollectTest(unittest.TestCase):

    def test_returns_analyze_when_data_present(self) -> None:
        state = create_initial_state()
        state["raw_items"] = {"github": [{"name": "a/b"}]}
        self.assertEqual(should_continue_after_collect(state), "analyze")

    def test_returns_supervise_when_errors_present(self) -> None:
        state = create_initial_state()
        state["errors"] = ["Collection failed"]
        state["raw_items"] = {"github": [{"name": "a/b"}]}
        self.assertEqual(should_continue_after_collect(state), "supervise")

    def test_returns_supervise_when_raw_items_empty(self) -> None:
        state = create_initial_state()
        state["raw_items"] = {}
        self.assertEqual(should_continue_after_collect(state), "supervise")

    def test_returns_supervise_when_all_sources_empty(self) -> None:
        state = create_initial_state()
        state["raw_items"] = {"github": [], "rss": []}
        self.assertEqual(should_continue_after_collect(state), "supervise")


# ── should_continue_after_analyze ─────────────────────────────────────

class ShouldContinueAfterAnalyzeTest(unittest.TestCase):

    def test_returns_organize_when_data_present(self) -> None:
        state = create_initial_state()
        state["analyzed_items"] = {"github": [{"summary": "ok"}]}
        self.assertEqual(should_continue_after_analyze(state), "organize")

    def test_returns_supervise_when_errors_present(self) -> None:
        state = create_initial_state()
        state["errors"] = ["Analysis failed"]
        state["analyzed_items"] = {"github": [{"summary": "ok"}]}
        self.assertEqual(should_continue_after_analyze(state), "supervise")

    def test_returns_supervise_when_analyzed_items_empty(self) -> None:
        state = create_initial_state()
        state["analyzed_items"] = {}
        self.assertEqual(should_continue_after_analyze(state), "supervise")

    def test_returns_supervise_when_all_sources_empty(self) -> None:
        state = create_initial_state()
        state["analyzed_items"] = {"github": []}
        self.assertEqual(should_continue_after_analyze(state), "supervise")


# ── route_after_supervisor ────────────────────────────────────────────

class RouteAfterSupervisorTest(unittest.TestCase):

    def test_pass_goes_to_save(self) -> None:
        state = create_initial_state()
        state["review_status"] = "pass"
        self.assertEqual(route_after_supervisor(state), "save")

    def test_needs_revision_goes_to_revise(self) -> None:
        state = create_initial_state()
        state["review_status"] = "needs_revision"
        self.assertEqual(route_after_supervisor(state), "revise")

    def test_blocked_goes_to_stop(self) -> None:
        state = create_initial_state()
        state["review_status"] = "blocked"
        self.assertEqual(route_after_supervisor(state), "stop")

    def test_errors_force_stop(self) -> None:
        state = create_initial_state()
        state["review_status"] = "needs_revision"
        state["errors"] = ["boom"]
        self.assertEqual(route_after_supervisor(state), "stop")

    def test_unknown_status_goes_to_stop(self) -> None:
        state = create_initial_state()
        state["review_status"] = "in_progress"
        self.assertEqual(route_after_supervisor(state), "stop")


if __name__ == "__main__":
    unittest.main()
