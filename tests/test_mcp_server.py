"""Tests for the MCP server's canonical knowledge view."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp_knowledge_server as server


def _article(article_id: str, url: str, collected_at: str) -> dict:
    """Build one MCP-readable article."""
    return {
        "id": article_id,
        "title": article_id,
        "source": "github-trending",
        "source_url": url,
        "collected_at": collected_at,
        "summary": "agent workflow",
        "analysis": {"relevance_score": 8, "reason": "useful", "tech_highlights": []},
        "tags": ["agent"],
        "status": "reviewed",
    }


class MCPServerCanonicalViewTest(unittest.TestCase):
    """Verify MCP tools expose canonical counts and exact tool names."""

    def setUp(self) -> None:
        server._articles = []
        server._articles_by_id = {}
        server._raw_article_count = 0

    def tearDown(self) -> None:
        server._articles = []
        server._articles_by_id = {}
        server._raw_article_count = 0

    def test_stats_reports_hidden_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article_dir = Path(tmp)
            (article_dir / "old.json").write_text(
                json.dumps(_article(
                    "old",
                    "https://github.com/owner/repo",
                    "2026-08-01T00:00:00Z",
                )),
                encoding="utf-8",
            )
            (article_dir / "new.json").write_text(
                json.dumps(_article(
                    "new",
                    "https://github.com/OWNER/REPO/",
                    "2026-08-02T00:00:00Z",
                )),
                encoding="utf-8",
            )

            with patch.object(server, "ARTICLES_DIR", article_dir):
                stats = server.handle_knowledge_stats({})
                result = server.handle_get_article({"article_id": "new"})

        self.assertEqual(stats["raw_total_articles"], 2)
        self.assertEqual(stats["total_articles"], 1)
        self.assertEqual(stats["duplicates_hidden"], 1)
        self.assertEqual(result["id"], "new")

    def test_tools_list_uses_documented_stats_name(self) -> None:
        response = server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        })

        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {"search_articles", "get_article", "knowledge_stats"},
        )


if __name__ == "__main__":
    unittest.main()
