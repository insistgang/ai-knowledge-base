"""Tests for pipeline cost tracking."""

from __future__ import annotations

import unittest

from pipeline.cost_tracker import CostTracker
from pipeline.model_client import Usage


class CostTrackerTest(unittest.TestCase):
    """Verify LLM cost metrics aggregation."""

    def test_daily_payload_groups_by_source_and_model(self) -> None:
        tracker = CostTracker(budget_usd=0.10)
        tracker.add_call(
            source="github",
            item_name="owner/repo-a",
            model="deepseek-chat",
            usage=Usage(prompt_tokens=1000, completion_tokens=1000),
        )
        tracker.add_call(
            source="github",
            item_name="owner/repo-b",
            model="deepseek-chat",
            usage=Usage(prompt_tokens=500, completion_tokens=250),
        )
        tracker.add_call(
            source="rss",
            item_name="paper",
            model="qwen-turbo",
            usage=Usage(prompt_tokens=200, completion_tokens=100),
        )

        payload = tracker.to_daily_payload(
            date_str="2026-04-30",
            generated_at="2026-04-30T08:00:00Z",
        )

        self.assertEqual(payload["date"], "2026-04-30")
        self.assertEqual(payload["budget"]["budget_usd"], 0.10)
        self.assertFalse(payload["budget"]["exceeded"])
        self.assertEqual(payload["total"]["calls"], 3)
        self.assertEqual(payload["total"]["prompt_tokens"], 1700)
        self.assertEqual(payload["total"]["completion_tokens"], 1350)
        self.assertEqual(payload["total"]["total_tokens"], 3050)
        self.assertEqual(len(payload["runs"]), 2)
        self.assertEqual(len(payload["calls"]), 3)

        github_run = next(
            run for run in payload["runs"]
            if run["source"] == "github" and run["model"] == "deepseek-chat"
        )
        self.assertEqual(github_run["calls"], 2)
        self.assertEqual(github_run["total_tokens"], 2750)
        self.assertAlmostEqual(github_run["estimated_cost_usd"], 0.00178)

    def test_budget_exceeded_when_cost_reaches_threshold(self) -> None:
        tracker = CostTracker(budget_usd=0.001)

        self.assertFalse(tracker.is_budget_exceeded())
        tracker.add_call(
            source="github",
            item_name="owner/repo",
            model="deepseek-chat",
            usage=Usage(prompt_tokens=1000, completion_tokens=1000),
        )

        self.assertTrue(tracker.is_budget_exceeded())
        status = tracker.budget_status()
        self.assertEqual(status["budget_usd"], 0.001)
        self.assertEqual(status["remaining_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
