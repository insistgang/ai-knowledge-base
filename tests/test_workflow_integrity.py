"""Production invariants for LangGraph state, cost, and persistence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.cost_tracker import CostTracker
from pipeline.workflow_nodes import analyze_node, save_node
from pipeline.workflow_state import create_initial_state
from workflows.human_flag import human_flag_node
from workflows.planner import planner_node
from workflows.reviewer import review_node
from workflows.reviser import revise_node


def _analysis(summary: str) -> dict:
    """Build one analysis item."""
    return {
        "summary": summary,
        "tech_highlights": ["specific detail"],
        "relevance_score": 8,
        "reason": "useful",
        "suggested_tags": ["agent-workflow"],
        "audience": ["developer"],
        "risks": [],
    }


class WorkflowStateBridgeTest(unittest.TestCase):
    """Verify grouped analyses enter review and revisions return to groups."""

    def test_analyze_node_populates_flat_review_input(self) -> None:
        state = create_initial_state(sources=["github"], analysis_depth="deep")
        state["raw_items"] = {"github": [{"name": "owner/repo"}]}
        analyzed = [_analysis("original")]

        with patch("pipeline.workflow_nodes.analyze", return_value=analyzed) as mock_analyze:
            result = analyze_node(state)

        self.assertEqual(result["analyses"], analyzed)
        self.assertIsInstance(result["llm_cost_tracker"], CostTracker)
        self.assertEqual(
            result["stats"]["_model_route"]["analysis_model"],
            "deepseek-v4-pro",
        )
        self.assertEqual(
            mock_analyze.call_args.kwargs["model_name"],
            "deepseek-v4-pro",
        )

    def test_planner_never_expands_requested_limit(self) -> None:
        state = create_initial_state(limit=3)

        result = planner_node(state)

        self.assertEqual(result["limit"], 3)
        self.assertEqual(result["plan"]["per_source_limit"], 3)

    def test_reviser_writes_improvements_back_to_source_groups(self) -> None:
        state = create_initial_state(sources=["github", "rss"])
        state["analyses"] = [_analysis("one"), _analysis("two")]
        state["analyzed_items"] = {
            "github": [state["analyses"][0]],
            "rss": [state["analyses"][1]],
        }
        state["review_feedback"] = {"issues": [{"field": "summary"}]}
        state["llm_cost_tracker"] = CostTracker()
        improved = [_analysis("better one"), _analysis("better two")]
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "estimated_cost_usd": 0.0,
            "model": "deepseek-v4-flash",
        }

        with patch(
            "workflows.reviewer.chat_json",
            return_value=({"analyses": improved, "changes_summary": "fixed"}, usage),
        ):
            result = revise_node(state)

        self.assertEqual(result["analyzed_items"]["github"][0]["summary"], "better one")
        self.assertEqual(result["analyzed_items"]["rss"][0]["summary"], "better two")


class WorkflowReviewAndSaveTest(unittest.TestCase):
    """Verify review provenance controls article status and costs are saved."""

    def test_successful_review_is_verified_and_uses_state_provider(self) -> None:
        state = create_initial_state(provider="qwen")
        state["analyses"] = [_analysis("review me")]
        state["llm_cost_tracker"] = CostTracker()
        feedback = {
            "scores": {
                "summary_quality": 8,
                "technical_depth": 8,
                "relevance": 8,
                "originality": 8,
                "formatting": 8,
            },
            "overall_comment": "good",
            "issues": [],
            "strengths": ["specific"],
        }
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "estimated_cost_usd": 0.001,
            "model": "qwen-plus",
        }

        with patch("workflows.reviewer.chat_json", return_value=(feedback, usage)) as chat:
            result = review_node(state)

        self.assertTrue(result["review_verified"])
        self.assertTrue(result["review_passed"])
        self.assertEqual(chat.call_args.kwargs["provider"], "qwen")
        self.assertEqual(state["llm_cost_tracker"].total()["calls"], 1)

    def test_save_marks_verified_articles_reviewed_and_saves_metrics(self) -> None:
        state = create_initial_state(sources=["github"])
        state.update({
            "review_status": "pass",
            "review_passed": True,
            "review_verified": True,
            "raw_items": {"github": [{"name": "owner/repo"}]},
            "articles": {"github": [{
                "id": "article-1",
                "title": "Title",
                "source_url": "https://example.com/repo",
                "summary": "summary",
                "status": "draft",
            }]},
            "llm_cost_tracker": CostTracker(),
        })

        with (
            patch("pipeline.workflow_nodes.save_raw", return_value=Path("raw.json")),
            patch(
                "pipeline.workflow_nodes.save_articles",
                return_value=[Path("article.json")],
            ) as save_articles,
            patch(
                "pipeline.workflow_nodes.save_cost_metrics",
                return_value=Path("cost.json"),
            ) as save_metrics,
        ):
            result = save_node(state)

        saved_article = save_articles.call_args.args[2][0]
        self.assertEqual(saved_article["status"], "reviewed")
        self.assertEqual(result["articles"]["github"][0]["status"], "reviewed")
        save_metrics.assert_called_once()
        self.assertIn("cost.json", result["saved_paths"])

    def test_human_flag_dry_run_has_no_file_side_effect(self) -> None:
        state = create_initial_state(dry_run=True)
        state["analyses"] = [_analysis("needs review")]

        with tempfile.TemporaryDirectory() as tmp:
            pending = Path(tmp) / "pending"
            with patch("workflows.human_flag.PENDING_DIR", pending):
                result = human_flag_node(state)

            self.assertFalse(pending.exists())

        self.assertTrue(result["needs_human_review"])


class ProductionWorkflowConfigurationTest(unittest.TestCase):
    """Verify scheduled collection invokes the LangGraph entry point."""

    def test_daily_workflow_uses_langgraph_runner_and_python_312(self) -> None:
        workflow = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "daily-collect.yml"
        ).read_text(encoding="utf-8")

        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn("python -m pipeline.workflow_runner", workflow)
        self.assertNotIn("python pipeline/pipeline.py", workflow)


if __name__ == "__main__":
    unittest.main()
