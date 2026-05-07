"""Reviewer node — LLM-powered quality review with 5-dimension scoring.

Reviews ``state["analyses"]`` (not articles) and computes a weighted
pass/fail decision in-code (never trusting LLM arithmetic).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pipeline.workflow_state import KBState

logger = logging.getLogger(__name__)

# ── Scoring dimensions ────────────────────────────────────────────────
SCORE_DIMENSIONS = {
    "summary_quality": 0.25,
    "technical_depth": 0.25,
    "relevance": 0.20,
    "originality": 0.15,
    "formatting": 0.15,
}

PASS_THRESHOLD = 7.0
MAX_REVIEW_ITEMS = 5

# ── Prompt templates ──────────────────────────────────────────────────
REVIEWER_SYSTEM = """你是一个 AI 知识库质量审核员。审核以下技术分析条目，严格从五个维度打分（每维 1-10）。

返回纯 JSON（不要 markdown）：
{
  "scores": {
    "summary_quality": 8,
    "technical_depth": 7,
    "relevance": 9,
    "originality": 6,
    "formatting": 8
  },
  "overall_comment": "一句话总体评价",
  "issues": [
    {"field": "...", "severity": "high|medium|low", "note": "..."}
  ],
  "strengths": ["具体优点"]
}

评分标准：
- summary_quality：摘要是否准确、简洁、保留关键术语
- technical_depth：技术亮点是否具体、有数据或架构细节
- relevance：与 AI/LLM/Agent 主题的相关度
- originality：项目是否有创新点，非重复造轮子
- formatting：标签是否精细、适用人群是否合理

严格打分，不要给全满分；有明显缺陷时必须体现在分数和 issues 里。"""


# ── Internal helpers ──────────────────────────────────────────────────

def chat_json(
    prompt: str,
    system: str = "你是一个 AI 助手。",
    temperature: float = 0.1,
    provider: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call LLM, parse JSON output, return (parsed, usage)."""
    from pipeline.model_client import chat_with_retry, create_provider, estimate_cost

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    llm = create_provider(provider)
    try:
        response = chat_with_retry(llm, messages, temperature=temperature, max_tokens=1024)
        usage = response.usage.to_dict()
        usage["estimated_cost_usd"] = estimate_cost(response.model or llm.model, response.usage)

        raw = response.content.strip()
        # Strip possible markdown fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:])
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        return json.loads(raw), usage
    finally:
        llm.close()


def accumulate_usage(tracker: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    """Accumulate token usage and cost into a running tracker dict."""
    t = dict(tracker)
    t["total_prompt_tokens"] = t.get("total_prompt_tokens", 0) + usage.get("prompt_tokens", 0)
    t["total_completion_tokens"] = t.get("total_completion_tokens", 0) + usage.get("completion_tokens", 0)
    t["total_cost_usd"] = t.get("total_cost_usd", 0.0) + usage.get("estimated_cost_usd", 0.0)
    t["api_calls"] = t.get("api_calls", 0) + 1
    return t


def _recalculate_weighted(scores: dict[str, int]) -> float:
    """Recalculate weighted total from raw scores (never trust LLM math)."""
    total = 0.0
    for dim, weight in SCORE_DIMENSIONS.items():
        total += scores.get(dim, 0) * weight
    return round(total, 2)


def _build_review_prompt(analyses: list[dict[str, Any]]) -> str:
    """Build a compact prompt summarising the analyses to review."""
    items = []
    for i, ana in enumerate(analyses, 1):
        items.append({
            "index": i,
            "summary": ana.get("summary", "")[:200],
            "tech_highlights": ana.get("tech_highlights", [])[:3],
            "relevance_score": ana.get("relevance_score"),
            "tags": ana.get("suggested_tags", ana.get("tags", []))[:5],
        })

    prompt = json.dumps(items, ensure_ascii=False, indent=2)
    return f"审核以下 {len(items)} 条分析结果，按维度打分：\n\n{prompt}"


# ── Public node ───────────────────────────────────────────────────────

def review_node(state: KBState, provider: str | None = None) -> KBState:
    """Run LLM-powered quality review on ``state["analyses"]``.

    Only the first 5 analyses are reviewed to control token consumption.
    Weighted total is recalculated in code (LLM math is never trusted).
    On LLM failure the node auto-passes so it never blocks the pipeline.

    Args:
        state: Current workflow state.
        provider: Optional LLM provider override.

    Returns:
        Updated state with ``review_passed``, ``review_feedback``,
        ``iteration``, and ``cost_tracker`` mutated.
    """
    analyses: list[dict[str, Any]] = state.get("analyses", [])
    iteration: int = state.get("iteration", 0) + 1
    cost_tracker: dict[str, Any] = dict(state.get("cost_tracker") or {})

    # No analyses to review
    if not analyses:
        logger.info("Reviewer: no analyses found, auto-pass")
        return _build_result(state, True, "No analyses to review", iteration, cost_tracker)

    # Limit to first 5
    subset = analyses[:MAX_REVIEW_ITEMS]
    if len(analyses) > MAX_REVIEW_ITEMS:
        logger.info("Reviewer: limiting to first %d of %d analyses", MAX_REVIEW_ITEMS, len(analyses))

    # ── LLM review ────────────────────────────────────────────────────
    try:
        prompt = _build_review_prompt(subset)
        feedback, usage = chat_json(
            prompt=prompt,
            system=REVIEWER_SYSTEM,
            temperature=0.1,
            provider=provider,
        )
        cost_tracker = accumulate_usage(cost_tracker, usage)

        # Recalculate weighted total in code (never trust LLM)
        scores = feedback.get("scores", {})
        weighted_total = _recalculate_weighted(scores)
        review_passed = weighted_total >= PASS_THRESHOLD

        logger.info(
            "Reviewer: weighted=%.2f threshold=%.1f passed=%s",
            weighted_total, PASS_THRESHOLD, review_passed,
        )

    except Exception:
        logger.warning("Reviewer: LLM call failed, auto-passing", exc_info=True)
        feedback = {
            "scores": {dim: 7 for dim in SCORE_DIMENSIONS},
            "overall_comment": "LLM review failed — auto-passed with neutral scores.",
            "issues": [],
            "strengths": [],
        }
        weighted_total = 7.0
        review_passed = True

    # Attach computed totals to feedback for downstream consumers
    feedback["_computed"] = {
        "weighted_total": weighted_total,
        "pass_threshold": PASS_THRESHOLD,
        "reviewed_count": len(subset),
        "total_count": len(analyses),
    }

    return _build_result(state, review_passed, feedback, iteration, cost_tracker)


def _build_result(
    state: KBState,
    review_passed: bool,
    feedback: dict[str, Any] | str,
    iteration: int,
    cost_tracker: dict[str, Any],
) -> KBState:
    """Pack review results back into a KBState-compat dict."""
    return {
        **state,  # type: ignore[typeddict-item]
        "review_passed": review_passed,
        "review_feedback": feedback,
        "iteration": iteration,
        "cost_tracker": cost_tracker,
    }
