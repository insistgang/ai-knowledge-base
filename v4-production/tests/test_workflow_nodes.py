"""Tests for workflow node functions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pipeline.workflow_nodes import (
    analyze_node,
    collect_node,
    organize_node,
    save_node,
    supervise_node,
)
from pipeline.workflow_state import create_initial_state


def _sample_item(name: str = "owner/repo") -> dict:
    return {
        "name": name,
        "url": f"https://github.com/{name}",
        "summary": "Test summary",
        "stars": 500,
        "language": "Python",
        "topics": ["agent"],
    }


def _sample_analyzed() -> dict:
    return {
        "summary": "Test project",
        "tech_highlights": ["highlight 1", "highlight 2"],
        "relevance_score": 7,
        "reason": "Good",
        "suggested_tags": ["agent"],
        "audience": ["developer"],
        "risks": [],
    }


class CollectNodeTest(unittest.TestCase):
    """collect_node tests."""

    def test_collect_node_populates_raw_items(self) -> None:
        state = create_initial_state(sources=["github"], limit=3)
        with patch("pipeline.workflow_nodes.COLLECTORS", {
            "github": MagicMock(return_value=[_sample_item("a/b"), _sample_item("c/d")])
        }):
            result = collect_node(state)

        self.assertEqual(result["raw_items"]["github"], [_sample_item("a/b"), _sample_item("c/d")])
        self.assertEqual(result["stats"]["github"]["collected"], 2)

    def test_unknown_source_adds_error(self) -> None:
        state = create_initial_state(sources=["xyz"], limit=3)
        with patch("pipeline.workflow_nodes.COLLECTORS", {}):
            result = collect_node(state)

        self.assertIn("Unknown source: xyz", result["errors"])
        self.assertEqual(result["stats"]["xyz"]["collected"], 0)

    def test_collect_node_preserves_existing_errors(self) -> None:
        state = create_initial_state(sources=["github"], limit=3)
        state["errors"] = ["prior error"]
        with patch("pipeline.workflow_nodes.COLLECTORS", {
            "github": MagicMock(return_value=[])
        }):
            result = collect_node(state)

        self.assertIn("prior error", result["errors"])


class AnalyzeNodeTest(unittest.TestCase):
    """analyze_node tests."""

    def test_analyze_node_populates_analyzed_items(self) -> None:
        state = create_initial_state(sources=["github"])
        state["raw_items"] = {"github": [_sample_item()]}
        analyzed_result = [_sample_analyzed()]

        with patch("pipeline.workflow_nodes.analyze", return_value=analyzed_result):
            result = analyze_node(state)

        self.assertEqual(result["analyzed_items"]["github"], analyzed_result)
        self.assertEqual(result["stats"]["github"]["analyzed"], 1)

    def test_analyze_node_skips_empty_raw_items(self) -> None:
        state = create_initial_state(sources=["github"])
        state["raw_items"] = {"github": []}
        result = analyze_node(state)
        self.assertEqual(result["analyzed_items"]["github"], [])
        self.assertEqual(result["stats"]["github"]["analyzed"], 0)


class OrganizeNodeTest(unittest.TestCase):
    """organize_node tests."""

    def test_organize_node_populates_articles(self) -> None:
        state = create_initial_state(sources=["github"])
        state["collected_at"] = "2026-04-30T12:00:00Z"
        state["raw_items"] = {"github": [_sample_item()]}
        state["analyzed_items"] = {"github": [_sample_analyzed()]}
        organized = [{
            "id": "gh-001", "title": "Test",
            "source_url": "https://example.com",
            "summary": "ok", "status": "draft",
        }]

        with patch("pipeline.workflow_nodes.organize", return_value=organized):
            result = organize_node(state)

        self.assertEqual(result["articles"]["github"], organized)
        self.assertEqual(result["stats"]["github"]["articles"], 1)

    def test_organize_node_skips_when_no_analyzed(self) -> None:
        state = create_initial_state(sources=["github"])
        state["raw_items"] = {"github": [_sample_item()]}
        state["analyzed_items"] = {"github": []}
        result = organize_node(state)
        self.assertEqual(result["articles"]["github"], [])
        self.assertEqual(result["stats"]["github"]["articles"], 0)


class SuperviseNodeTest(unittest.TestCase):
    """supervise_node tests."""

    def test_pass_when_all_articles_valid(self) -> None:
        state = create_initial_state()
        state["articles"] = {"github": [{
            "id": "gh-001", "title": "T", "source_url": "u", "summary": "s", "status": "draft"
        }]}
        result = supervise_node(state)
        self.assertEqual(result["review_status"], "pass")
        self.assertEqual(result["review_findings"], [])

    def test_needs_revision_when_fields_missing(self) -> None:
        state = create_initial_state()
        state["articles"] = {"github": [{"id": "gh-001"}]}  # missing title, source_url, ...
        result = supervise_node(state)
        self.assertEqual(result["review_status"], "needs_revision")
        self.assertGreater(len(result["review_findings"]), 0)
        finding = result["review_findings"][0]
        self.assertEqual(finding["severity"], "high")
        self.assertIn("title", finding["field"])

    def test_blocked_when_errors_present(self) -> None:
        state = create_initial_state()
        state["errors"] = ["Collection failed"]
        result = supervise_node(state)
        self.assertEqual(result["review_status"], "blocked")
        self.assertEqual(result["review_findings"][0]["severity"], "high")


class SaveNodeTest(unittest.TestCase):
    """save_node tests."""

    def test_save_blocked_when_not_passed(self) -> None:
        state = create_initial_state()
        state["review_status"] = "needs_revision"
        result = save_node(state)
        self.assertIn("Save blocked", result["errors"][-1])

    def test_save_calls_raw_and_articles(self) -> None:
        state = create_initial_state(sources=["github"])
        state["review_status"] = "pass"
        state["collected_at"] = "2026-04-30T12:00:00Z"
        state["raw_items"] = {"github": [_sample_item()]}
        state["articles"] = {"github": [{"id": "gh-001", "title": "T", "source_url": "u", "summary": "s", "status": "draft"}]}

        with patch("pipeline.workflow_nodes.save_raw") as mock_raw, \
             patch("pipeline.workflow_nodes.save_articles") as mock_art:
            mock_raw.return_value = "raw.json"
            mock_art.return_value = ["art.json"]
            result = save_node(state)

        self.assertIn("raw.json", result["saved_paths"])
        self.assertIn("art.json", result["saved_paths"])

    def test_save_honors_dry_run(self) -> None:
        state = create_initial_state(sources=["github"])
        state["review_status"] = "pass"
        state["collected_at"] = "2026-04-30T12:00:00Z"
        state["raw_items"] = {"github": [_sample_item()]}
        state["articles"] = {"github": [{"id": "gh-001", "title": "T", "source_url": "u", "summary": "s", "status": "draft"}]}

        with patch("pipeline.workflow_nodes.save_raw") as mock_raw, \
             patch("pipeline.workflow_nodes.save_articles") as mock_art:
            mock_raw.return_value = "raw.json"
            mock_art.return_value = ["art.json"]
            save_node({**state, "dry_run": True})

        mock_raw.assert_called_once()
        _, raw_kwargs = mock_raw.call_args
        self.assertIs(raw_kwargs["dry_run"], True)

        mock_art.assert_called_once()
        _, art_kwargs = mock_art.call_args
        self.assertIs(art_kwargs["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
