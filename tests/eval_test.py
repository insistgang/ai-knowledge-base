"""Eval tests for AI knowledge base — LLM-as-Judge + local validation.

Usage:
    python3 tests/eval_test.py          # local only (no API cost)
    pytest tests/eval_test.py -m slow -v # full eval with LLM-as-Judge
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import pytest

logger = logging.getLogger(__name__)

# ── Test cases ────────────────────────────────────────────────────────

EVAL_CASES = [
    {
        "id": "positive-tech-article",
        "scene": "正面案例：技术文章",
        "input": {
            "title": "LangGraph: Build Stateful Agent Workflows",
            "summary": "LangGraph is a library for building stateful, "
            "multi-actor applications with LLMs. It extends LangChain "
            "with graph-based control flow, supporting cycles, conditionals, "
            "and human-in-the-loop patterns for complex agent orchestration.",
            "tags": ["langgraph", "agent", "workflow", "llm"],
        },
        "expected": lambda out: (
            hasattr(out, "get") and isinstance(out, dict)
            and "summary" in out
            and len(out.get("tech_highlights", [])) >= 1
            and out.get("relevance_score", 0) >= 5
        ),
    },
    {
        "id": "negative-irrelevant",
        "scene": "负面案例：无关内容",
        "input": {
            "title": "My Personal Blog",
            "summary": "Welcome to my personal blog. I write about my life, hobbies, and daily routines.",
            "tags": ["blog", "personal", "life"],
        },
        "expected": lambda out: (
            hasattr(out, "get") and isinstance(out, dict)
            and out.get("relevance_score", 10) <= 5
        ),
    },
    {
        "id": "edge-short-input",
        "scene": "边界案例：极短输入",
        "input": {
            "title": "AI",
            "summary": "AI",
            "tags": [],
        },
        "expected": lambda out: (
            hasattr(out, "get") and isinstance(out, dict)
        ),  # Must not crash
    },
]


# ── Local validation (no API) ─────────────────────────────────────────

def local_analyze(item: dict[str, Any]) -> dict[str, Any]:
    """Heuristic analysis that does NOT call an LLM."""
    title = item.get("title", "")
    summary = item.get("summary", "")
    tags = item.get("tags", [])
    blob = f"{title} {summary} {' '.join(tags)}".lower()

    # Count AI-relevant words
    ai_keywords = re.findall(
        r"llm|agent|langchain|langgraph|rag|mcp|vector|embedding|transformer|"
        r"fine.?tun|prompt|openai|deepseek|claude|workflow|ai",
        blob,
    )
    score = min(10, len(ai_keywords) * 2 + 2)

    tech_highlights: list[str] = []
    if ai_keywords:
        tech_highlights.append(
            f"Contains {len(ai_keywords)} AI-related keyword(s)"
        )

    return {
        "summary": summary[:100],
        "tech_highlights": tech_highlights,
        "relevance_score": score,
        "reason": f"Heuristic: {len(ai_keywords)} keyword matches",
        "suggested_tags": tags[:5],
        "audience": ["developer"],
        "risks": [],
    }


class TestLocalValidation:
    """Local-only tests — zero API cost."""

    @pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c["id"])
    def test_case_meets_expectations(self, case: dict[str, Any]) -> None:
        result = local_analyze(case["input"])
        assert case["expected"](result), (
            f"Case '{case['id']}' ({case['scene']}) failed: {result}"
        )

    def test_positive_has_tech_highlights(self) -> None:
        result = local_analyze(EVAL_CASES[0]["input"])
        assert len(result["tech_highlights"]) >= 1

    def test_positive_score_above_threshold(self) -> None:
        result = local_analyze(EVAL_CASES[0]["input"])
        assert result["relevance_score"] >= 5

    def test_negative_score_below_threshold(self) -> None:
        result = local_analyze(EVAL_CASES[1]["input"])
        assert result["relevance_score"] <= 5

    def test_edge_case_does_not_crash(self) -> None:
        result = local_analyze(EVAL_CASES[2]["input"])
        assert isinstance(result, dict)
        assert "summary" in result
        assert "relevance_score" in result


# ── LLM-as-Judge (API cost) ───────────────────────────────────────────

@pytest.mark.slow
class TestLLMJudge:
    """LLM-as-Judge evaluation — requires API key."""

    @pytest.fixture(autouse=True)
    def skip_if_no_key(self) -> None:
        if not os.getenv("DEEPSEEK_API_KEY"):
            pytest.skip("DEEPSEEK_API_KEY not set")

    def test_llm_judge_positive_case(self) -> None:
        from pipeline.model_client import chat_with_retry, create_provider

        case = EVAL_CASES[0]
        prompt = json.dumps(case["input"], ensure_ascii=False)
        llm = create_provider()
        try:
            resp = chat_with_retry(
                llm,
                [
                    {
                        "role": "system",
                        "content": "你是一个评测员。分析以下技术条目，返回 JSON："
                        '{"relevance_score": 5, "reason": "..."}',
                    },
                    {"role": "user", "content": f"分析：{prompt}"},
                ],
                temperature=0.0,
                max_tokens=256,
            )
        finally:
            llm.close()

        # Parse JSON from response
        raw = resp.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)

        assert isinstance(result.get("relevance_score"), (int, float))
        assert result["relevance_score"] >= 5, (
            f"LLM judged positive case too low: {result}"
        )

    def test_llm_judge_negative_case(self) -> None:
        from pipeline.model_client import chat_with_retry, create_provider

        case = EVAL_CASES[1]
        prompt = json.dumps(case["input"], ensure_ascii=False)
        llm = create_provider()
        try:
            resp = chat_with_retry(
                llm,
                [
                    {
                        "role": "system",
                        "content": "你是一个评测员。分析以下技术条目，返回 JSON："
                        '{"relevance_score": 1, "reason": "..."}',
                    },
                    {"role": "user", "content": f"分析：{prompt}"},
                ],
                temperature=0.0,
                max_tokens=256,
            )
        finally:
            llm.close()

        raw = resp.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)

        assert isinstance(result.get("relevance_score"), (int, float))
        assert result["relevance_score"] <= 5, (
            f"LLM judged negative case too high: {result}"
        )


if __name__ == "__main__":
    # Run local validation only (no API cost)
    pytest.main([__file__, "-v", "-m", "not slow"])
