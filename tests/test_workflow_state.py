"""Tests for KBState and create_initial_state."""

from __future__ import annotations

import unittest

from pipeline.workflow_state import KBState, create_initial_state


class CreateInitialStateDefaultsTest(unittest.TestCase):
    """Verify default values of a freshly created KBState."""

    def setUp(self) -> None:
        self.state = create_initial_state()

    def test_default_sources_is_github(self) -> None:
        self.assertEqual(self.state["sources"], ["github"])

    def test_default_limit_is_5(self) -> None:
        self.assertEqual(self.state["limit"], 5)

    def test_default_provider_is_none(self) -> None:
        self.assertIsNone(self.state["provider"])

    def test_default_analysis_depth_is_normal(self) -> None:
        self.assertEqual(self.state["analysis_depth"], "normal")

    def test_default_dry_run_is_false(self) -> None:
        self.assertFalse(self.state["dry_run"])

    def test_default_review_status_is_pending(self) -> None:
        self.assertEqual(self.state["review_status"], "pending")

    def test_default_raw_items_is_empty_dict(self) -> None:
        self.assertEqual(self.state["raw_items"], {})

    def test_default_analyzed_items_is_empty_dict(self) -> None:
        self.assertEqual(self.state["analyzed_items"], {})

    def test_default_articles_is_empty_dict(self) -> None:
        self.assertEqual(self.state["articles"], {})

    def test_default_stats_is_empty_dict(self) -> None:
        self.assertEqual(self.state["stats"], {})

    def test_default_review_findings_is_empty_list(self) -> None:
        self.assertEqual(self.state["review_findings"], [])

    def test_default_saved_paths_is_empty_list(self) -> None:
        self.assertEqual(self.state["saved_paths"], [])

    def test_default_errors_is_empty_list(self) -> None:
        self.assertEqual(self.state["errors"], [])

    def test_collected_at_is_iso_utc(self) -> None:
        ts = self.state["collected_at"]
        # YYYY-MM-DDThh:mm:ssZ
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class CreateInitialStateCustomTest(unittest.TestCase):
    """Verify that custom values propagate correctly."""

    def test_custom_sources(self) -> None:
        state = create_initial_state(sources=["github", "rss"])
        self.assertEqual(state["sources"], ["github", "rss"])

    def test_custom_limit(self) -> None:
        state = create_initial_state(limit=10)
        self.assertEqual(state["limit"], 10)

    def test_custom_provider(self) -> None:
        state = create_initial_state(provider="deepseek")
        self.assertEqual(state["provider"], "deepseek")

    def test_custom_analysis_depth(self) -> None:
        state = create_initial_state(analysis_depth="deep")
        self.assertEqual(state["analysis_depth"], "deep")

    def test_custom_dry_run(self) -> None:
        state = create_initial_state(dry_run=True)
        self.assertTrue(state["dry_run"])


class ReferenceIsolationTest(unittest.TestCase):
    """Each call to create_initial_state must produce independent objects."""

    def test_dicts_are_independent(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["raw_items"]["github"] = [{"name": "owner/repo"}]
        self.assertNotIn("github", s2["raw_items"])

    def test_lists_are_independent(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["errors"].append("boom")
        self.assertEqual(s2["errors"], [])

    def test_sources_list_independent_when_default(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["sources"].append("rss")
        self.assertEqual(s2["sources"], ["github"])

    def test_review_findings_are_independent(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["review_findings"].append({"msg": "bad tag"})
        self.assertEqual(s2["review_findings"], [])

    def test_saved_paths_are_independent(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["saved_paths"].append("/tmp/article.json")
        self.assertEqual(s2["saved_paths"], [])

    def test_articles_are_independent(self) -> None:
        s1 = create_initial_state()
        s2 = create_initial_state()
        s1["articles"]["github"] = [{"id": "github-001"}]
        self.assertEqual(s2["articles"], {})


if __name__ == "__main__":
    unittest.main()
