"""Tests for GitHub collection diversity and historical deduplication."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from pipeline.pipeline import (
    MAX_MODEL_DESCRIPTION_CHARS,
    analyze_item,
    collect_github,
    load_existing_source_urls,
    normalize_source_url,
    select_balanced_repositories,
)


def _repo(name: str, description: str = "summary") -> dict[str, Any]:
    """Build a minimal GitHub Search API repository result."""
    return {
        "full_name": name,
        "html_url": f"https://github.com/{name}",
        "description": description,
        "stargazers_count": 100,
        "language": "Python",
        "topics": ["agent"],
    }


class StubSearchResponse:
    """Return deterministic repository search results."""

    def __init__(self, items: list[dict[str, Any]]) -> None:
        self._items = items

    def raise_for_status(self) -> None:
        """Match the successful httpx response interface."""

    def json(self) -> dict[str, Any]:
        """Return a GitHub Search compatible response."""
        return {"items": self._items}


class StubProvider:
    """Capture the prompt passed to the model boundary."""

    model = "deepseek-v4-flash"

    def close(self) -> None:
        """Match the provider close contract."""


class SourceUrlTest(unittest.TestCase):
    """Verify stable historical source URL handling."""

    def test_normalize_source_url_ignores_case_query_and_trailing_slash(self) -> None:
        normalized = normalize_source_url(
            "HTTPS://GitHub.com/Owner/Repo/?utm_source=test#readme"
        )

        self.assertEqual(normalized, "https://github.com/owner/repo")

    def test_normalize_source_url_rejects_a_malformed_port(self) -> None:
        normalized = normalize_source_url(
            "https://github.com:not-a-port/owner/repo"
        )

        self.assertEqual(normalized, "")

    def test_load_existing_source_urls_skips_invalid_json(self) -> None:
        with TemporaryDirectory() as temp_dir:
            article_dir = Path(temp_dir)
            (article_dir / "valid.json").write_text(
                json.dumps({"source_url": "https://github.com/Owner/Repo/"}),
                encoding="utf-8",
            )
            (article_dir / "invalid.json").write_text("{", encoding="utf-8")

            urls = load_existing_source_urls(article_dir)

        self.assertEqual(urls, {"https://github.com/owner/repo"})


class BalancedSelectionTest(unittest.TestCase):
    """Verify balanced candidate selection before LLM analysis."""

    def test_round_robin_selection_uses_each_query_before_refilling(self) -> None:
        groups = [
            [_repo("q1/first"), _repo("q1/second")],
            [_repo("q2/first"), _repo("q2/second")],
            [_repo("q3/first"), _repo("q3/second")],
            [_repo("q4/first"), _repo("q4/second")],
        ]

        selected = select_balanced_repositories(groups, limit=5)

        self.assertEqual(
            [item["full_name"] for item in selected],
            ["q1/first", "q2/first", "q3/first", "q4/first", "q1/second"],
        )

    def test_selection_skips_historical_and_in_run_duplicate_urls(self) -> None:
        groups = [
            [_repo("old/repo"), _repo("new/one")],
            [_repo("NEW/ONE"), _repo("new/two")],
        ]

        selected = select_balanced_repositories(
            groups,
            limit=5,
            excluded_urls={"https://github.com/old/repo/"},
        )

        self.assertEqual(
            [item["full_name"] for item in selected],
            ["new/one", "new/two"],
        )

    def test_selection_skips_candidates_without_a_repository_name(self) -> None:
        invalid = _repo("owner/invalid")
        invalid["full_name"] = ""
        selected = select_balanced_repositories(
            [[invalid, _repo("owner/valid")]],
            limit=1,
        )

        self.assertEqual(
            [item["full_name"] for item in selected],
            ["owner/valid"],
        )


class GitHubCollectorTest(unittest.TestCase):
    """Verify query construction and collector output diversity."""

    def test_collect_github_queries_all_groups_and_filters_history(self) -> None:
        calls: list[dict[str, Any]] = []
        responses = [
            [_repo("old/repo"), _repo("q1/new")],
            [_repo("q2/new")],
            [_repo("q3/new")],
            [_repo("q4/new")],
        ]

        def fake_get(
            url: str,
            params: dict[str, Any],
            headers: dict[str, str],
            timeout: float,
        ) -> StubSearchResponse:
            del url, headers, timeout
            calls.append(params)
            return StubSearchResponse(responses[len(calls) - 1])

        now = datetime(2026, 8, 13, tzinfo=timezone.utc)
        with (
            patch("pipeline.pipeline._get_week_index", return_value=0),
            patch("pipeline.pipeline.load_existing_source_urls", return_value={
                "https://github.com/old/repo"
            }),
            patch("httpx.get", side_effect=fake_get),
        ):
            collected = collect_github(limit=4, now=now)

        self.assertEqual(len(calls), 4)
        self.assertTrue(all("pushed:>=2026-05-15" in call["q"] for call in calls))
        self.assertTrue(all(call["per_page"] == 100 for call in calls))
        self.assertEqual(
            [item["name"] for item in collected],
            ["q1/new", "q2/new", "q3/new", "q4/new"],
        )


class ModelPromptBoundaryTest(unittest.TestCase):
    """Verify that oversized metadata does not inflate model input."""

    def test_analyze_item_truncates_description_only_in_model_prompt(self) -> None:
        long_description = "x" * (MAX_MODEL_DESCRIPTION_CHARS + 500)
        item = {
            "name": "owner/repo",
            "url": "https://github.com/owner/repo",
            "summary": long_description,
            "language": "Python",
            "topics": ["agent"],
        }
        provider = StubProvider()
        captured: dict[str, Any] = {}

        def fake_chat(current_provider: Any, messages: list[dict[str, str]], **_: Any) -> Any:
            del current_provider
            captured["messages"] = messages
            return type(
                "Response",
                (),
                {
                    "content": json.dumps({
                        "summary": "ok",
                        "tech_highlights": [],
                        "relevance_score": 7,
                        "reason": "ok",
                        "suggested_tags": [],
                        "audience": ["developer"],
                    }),
                    "model": "deepseek-v4-flash",
                    "usage": object(),
                },
            )()

        with (
            patch("pipeline.model_client.create_provider", return_value=provider),
            patch("pipeline.model_client.chat_with_retry", side_effect=fake_chat),
        ):
            result = analyze_item(item)

        prompt_payload = json.loads(captured["messages"][1]["content"].split("\n", 1)[1])
        self.assertEqual(len(prompt_payload["description"]), MAX_MODEL_DESCRIPTION_CHARS)
        self.assertEqual(item["summary"], long_description)
        self.assertEqual(result["summary"], "ok")


if __name__ == "__main__":
    unittest.main()
