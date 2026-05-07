"""Reviser node — rewrites analyses based on reviewer feedback.

Reads ``state["analyses"]`` and ``state["review_feedback"]``, injects the
feedback into a revision prompt, and calls the LLM to produce improved
analyses.  Returns the updated state with replaced analyses.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pipeline.workflow_state import KBState

logger = logging.getLogger(__name__)

REVISION_SYSTEM = """你是一个 AI 知识库内容修订员。根据审核反馈修改分析条目，提升质量。

返回纯 JSON（不要 markdown）：
{
  "analyses": [
    {
      "summary": "修改后的摘要",
      "tech_highlights": ["亮点1", "亮点2"],
      "relevance_score": 8,
      "reason": "评分理由",
      "suggested_tags": ["tag1", "tag2"],
      "audience": ["developer"],
      "risks": []
    }
  ],
  "changes_summary": "一句话说明做了哪些修改"
}

修改要求：
- 根据 feedback 中的 issues 逐条修复
- summary 不超过 100 字，保留英文术语
- tech_highlights 必须具体，含数据或技术细节
- tags 精细、小写英文
- 不改动原始数据结构"""


def _build_revision_prompt(
    analyses: list[dict[str, Any]],
    feedback: dict[str, Any],
) -> str:
    """Build a revision prompt with current analyses and review feedback."""
    issues = feedback.get("issues", [])
    comment = feedback.get("overall_comment", "")
    computed = feedback.get("_computed", {})

    return json.dumps(
        {
            "original_analyses": analyses,
            "review_issues": issues,
            "overall_comment": comment,
            "computed_scores": computed,
        },
        ensure_ascii=False,
        indent=2,
    )


def revise_node(state: KBState, provider: str | None = None) -> KBState:
    """Apply reviewer feedback to improve analyses via LLM.

    Args:
        state: Current workflow state, must contain ``analyses`` and
               ``review_feedback``.
        provider: Optional LLM provider override.

    Returns:
        Updated state with ``analyses`` replaced by improved versions
        and ``cost_tracker`` advanced.  Returns ``{}`` (empty dict) when
        analyses or feedback are missing/empty.
    """
    analyses: list[dict[str, Any]] = state.get("analyses", [])
    feedback: dict[str, Any] = state.get("review_feedback", {})

    if not analyses:
        logger.info("Reviser: no analyses found, skipping")
        return {}  # type: ignore[return-value]

    if not feedback:
        logger.info("Reviser: no review feedback, skipping")
        return {}  # type: ignore[return-value]

    cost_tracker: dict[str, Any] = dict(state.get("cost_tracker") or {})

    try:
        from workflows.reviewer import accumulate_usage, chat_json

        prompt = _build_revision_prompt(analyses, feedback)
        revised, usage = chat_json(
            prompt=prompt,
            system=REVISION_SYSTEM,
            temperature=0.4,
            provider=provider,
        )
        cost_tracker = accumulate_usage(cost_tracker, usage)

        improved = revised.get("analyses", analyses)
        changes = revised.get("changes_summary", "")
        logger.info("Reviser: %d analyses revised — %s", len(improved), changes)

    except Exception:
        logger.warning("Reviser: LLM call failed, returning original analyses", exc_info=True)
        improved = analyses

    return {
        **state,  # type: ignore[typeddict-item]
        "analyses": improved,
        "cost_tracker": cost_tracker,
    }
