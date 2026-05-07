"""Contract tests for multi-agent routing specs (Section 9)."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / ".opencode" / "agents"
SPECS_DIR = PROJECT_ROOT / "specs"


def _read_frontmatter(path: str) -> dict[str, str]:
    """Parse YAML-like frontmatter from a Markdown agent file."""
    text = Path(path).read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


class RouterAgentContractTest(unittest.TestCase):
    """Verify router.md exists and frontmatter permissions are correct."""

    def test_router_md_exists(self) -> None:
        path = AGENTS_DIR / "router.md"
        self.assertTrue(path.is_file(), f"Missing agent file: {path}")

    def test_router_mode_is_subagent(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "router.md"))
        self.assertEqual(fm.get("mode"), "subagent")

    def test_router_edit_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "router.md"))
        self.assertEqual(fm.get("edit"), "deny")

    def test_router_bash_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "router.md"))
        self.assertEqual(fm.get("bash"), "deny")

    def test_router_webfetch_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "router.md"))
        self.assertEqual(fm.get("webfetch"), "deny")


class SupervisorAgentContractTest(unittest.TestCase):
    """Verify supervisor.md exists and frontmatter permissions are correct."""

    def test_supervisor_md_exists(self) -> None:
        path = AGENTS_DIR / "supervisor.md"
        self.assertTrue(path.is_file(), f"Missing agent file: {path}")

    def test_supervisor_mode_is_subagent(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "supervisor.md"))
        self.assertEqual(fm.get("mode"), "subagent")

    def test_supervisor_edit_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "supervisor.md"))
        self.assertEqual(fm.get("edit"), "deny")

    def test_supervisor_bash_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "supervisor.md"))
        self.assertEqual(fm.get("bash"), "deny")

    def test_supervisor_webfetch_is_denied(self) -> None:
        fm = _read_frontmatter(str(AGENTS_DIR / "supervisor.md"))
        self.assertEqual(fm.get("webfetch"), "deny")


class RoutingDocContentTest(unittest.TestCase):
    """Verify specs/multi-agent-routing.md contains required content."""

    @classmethod
    def setUpClass(cls) -> None:
        path = SPECS_DIR / "multi-agent-routing.md"
        cls.doc = path.read_text(encoding="utf-8")

    def test_routing_doc_exists(self) -> None:
        path = SPECS_DIR / "multi-agent-routing.md"
        self.assertTrue(path.is_file(), f"Missing routing doc: {path}")

    def test_collect_routes_to_collector(self) -> None:
        self.assertIn("collect", self.doc)
        self.assertRegex(self.doc, r"collect.*→.*collector")

    def test_analyze_routes_to_analyzer(self) -> None:
        self.assertRegex(self.doc, r"analyze.*→.*analyzer")

    def test_organize_routes_to_organizer(self) -> None:
        self.assertRegex(self.doc, r"organize.*→.*organizer")

    def test_review_routes_to_supervisor(self) -> None:
        self.assertRegex(self.doc, r"review.*→.*supervisor")

    def test_unknown_routes_to_ask_human(self) -> None:
        self.assertRegex(self.doc, r"unknown.*→.*ask_human")

    def test_contains_quality_issue_keyword_field_missing(self) -> None:
        self.assertIn("字段缺失", self.doc)

    def test_contains_quality_issue_keyword_tag_broad(self) -> None:
        self.assertIn("标签宽泛", self.doc)

    def test_contains_quality_issue_keyword_hollow_words(self) -> None:
        self.assertIn("空洞词", self.doc)

    def test_contains_quality_issue_keyword_score_anomaly(self) -> None:
        self.assertIn("评分异常", self.doc)

    def test_contains_quality_issue_keyword_source_doubtful(self) -> None:
        self.assertIn("来源存疑", self.doc)


if __name__ == "__main__":
    unittest.main()
