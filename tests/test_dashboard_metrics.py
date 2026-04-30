"""Tests for dashboard cost metrics loading."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reports.generate_dashboard import load_latest_cost_metrics


class DashboardMetricsTest(unittest.TestCase):
    """Verify dashboard cost metrics normalization."""

    def test_returns_empty_cost_metrics_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metrics = load_latest_cost_metrics(Path(tmp))

        self.assertFalse(metrics["available"])
        self.assertEqual(metrics["total"]["calls"], 0)
        self.assertEqual(metrics["budget"]["remaining_usd"], 0.0)

    def test_loads_latest_cost_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metrics_dir = Path(tmp)
            (metrics_dir / "cost-2026-04-29.json").write_text(
                json.dumps({
                    "date": "2026-04-29",
                    "generated_at": "2026-04-29T08:00:00Z",
                    "budget": {"budget_usd": 0.10, "remaining_usd": 0.09},
                    "total": {"calls": 1, "total_tokens": 1000},
                    "runs": [],
                }),
                encoding="utf-8",
            )
            (metrics_dir / "cost-2026-04-30.json").write_text(
                json.dumps({
                    "date": "2026-04-30",
                    "generated_at": "2026-04-30T08:00:00Z",
                    "budget": {
                        "budget_usd": 0.10,
                        "current_cost_usd": 0.0123,
                        "remaining_usd": 0.0877,
                        "exceeded": False,
                    },
                    "total": {
                        "calls": 5,
                        "prompt_tokens": 1200,
                        "completion_tokens": 800,
                        "total_tokens": 2000,
                        "estimated_cost_usd": 0.0123,
                    },
                    "runs": [{
                        "source": "github",
                        "model": "deepseek-v4-flash",
                        "calls": 5,
                        "total_tokens": 2000,
                        "estimated_cost_usd": 0.0123,
                    }],
                }),
                encoding="utf-8",
            )

            metrics = load_latest_cost_metrics(metrics_dir)

        self.assertTrue(metrics["available"])
        self.assertEqual(metrics["date"], "2026-04-30")
        self.assertEqual(metrics["budget"]["budget_usd"], 0.10)
        self.assertEqual(metrics["total"]["calls"], 5)
        self.assertEqual(metrics["runs"][0]["model"], "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
