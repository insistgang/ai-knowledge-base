"""Tests for canonical article views and corpus-wide integrity auditing."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hooks.audit_corpus import build_corpus_audit
from pipeline.article_store import select_canonical_articles
from reports.generate_dashboard import load_articles


def _article(
    article_id: str,
    source_url: str,
    collected_at: str,
) -> dict:
    """Build a minimal valid article for storage tests."""
    return {
        "id": article_id,
        "title": article_id,
        "source": "github-trending",
        "source_url": source_url,
        "collected_at": collected_at,
        "summary": "summary",
        "analysis": {
            "tech_highlights": ["detail"],
            "relevance_score": 7,
            "reason": "reason",
            "risks": [],
        },
        "tags": ["agent-workflow"],
        "audience": ["developer"],
        "status": "draft",
    }


class CanonicalArticleSelectionTest(unittest.TestCase):
    """Verify non-destructive latest-record selection."""

    def test_selects_latest_record_for_normalized_url(self) -> None:
        older = _article(
            "old",
            "HTTPS://GitHub.com/Owner/Repo/?from=old",
            "2026-08-01T00:00:00Z",
        )
        newer = _article(
            "new",
            "https://github.com/owner/repo/",
            "2026-08-02T00:00:00Z",
        )

        selected = select_canonical_articles([older, newer])

        self.assertEqual([item["id"] for item in selected], ["new"])

    def test_keeps_distinct_records_without_urls(self) -> None:
        first = _article("first", "", "2026-08-01T00:00:00Z")
        second = _article("second", "", "2026-08-02T00:00:00Z")

        selected = select_canonical_articles([first, second])

        self.assertEqual({item["id"] for item in selected}, {"first", "second"})


class CorpusAuditTest(unittest.TestCase):
    """Verify duplicate IDs and URLs are reported independently."""

    def test_reports_duplicate_groups_without_mutating_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = []
            for name, article in {
                "one.json": _article("same-id", "https://example.com/a", "2026-08-01T00:00:00Z"),
                "two.json": _article("same-id", "https://example.com/b", "2026-08-02T00:00:00Z"),
                "three.json": _article("third", "https://example.com/a/", "2026-08-03T00:00:00Z"),
            }.items():
                path = root / name
                path.write_text(json.dumps(article), encoding="utf-8")
                paths.append(path)

            audit = build_corpus_audit(paths)

            self.assertEqual(audit["valid_files"], 3)
            self.assertEqual(audit["unique_ids"], 2)
            self.assertEqual(audit["unique_source_urls"], 2)
            self.assertIn("same-id", audit["duplicate_ids"])
            self.assertIn(
                "https://example.com/a",
                audit["duplicate_source_urls"],
            )


class DashboardCanonicalViewTest(unittest.TestCase):
    """Verify the generated dashboard consumes the canonical view."""

    def test_load_articles_hides_legacy_url_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article_dir = root / "knowledge" / "articles"
            article_dir.mkdir(parents=True)
            (article_dir / "old.json").write_text(
                json.dumps(_article(
                    "old",
                    "https://example.com/repo",
                    "2026-08-01T00:00:00Z",
                )),
                encoding="utf-8",
            )
            (article_dir / "new.json").write_text(
                json.dumps(_article(
                    "new",
                    "https://example.com/repo/",
                    "2026-08-02T00:00:00Z",
                )),
                encoding="utf-8",
            )

            with patch("reports.generate_dashboard.PROJECT_ROOT", root):
                articles = load_articles(article_dir)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["id"], "new")


if __name__ == "__main__":
    unittest.main()
