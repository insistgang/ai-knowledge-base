"""Knowledge article formatter — JSON → Markdown / MarkdownV2 / digest."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def json_to_markdown(article: dict[str, Any]) -> str:
    """Render a single article as readable Markdown.

    Example::

        ### claude-context — MCP 语义代码搜索
        **评分**: 8/10  |  **标签**: mcp, rag, semantic-search
        **适用**: developer

        摘要: MCP 语义代码搜索，混合 BM25+向量检索。

        #### 技术亮点
        - BM25 + 密集向量混合检索
        - AST 级代码分块 + Merkle 树增量索引

        🔗 [GitHub](https://github.com/zilliztech/claude-context)
    """
    analysis = article.get("analysis", {})
    title = article.get("title", "Untitled")
    score = analysis.get("relevance_score", "?")
    tags = ", ".join(article.get("tags", [])) or "—"
    audience = ", ".join(article.get("audience", [])) or "—"
    summary = article.get("summary", "")
    highlights = analysis.get("tech_highlights", [])
    reason = analysis.get("reason", "")
    url = article.get("source_url", "")
    source = article.get("source", "")

    lines = [f"### {title}"]
    lines.append(f"**评分**: {score}/10  |  **标签**: {tags}")
    lines.append(f"**适用**: {audience}  |  **来源**: {source}")

    if summary:
        lines.append(f"\n摘要: {summary}")

    if highlights:
        lines.append("\n#### 技术亮点")
        for h in highlights[:3]:
            lines.append(f"- {h}")

    if reason:
        lines.append(f"\n评审意见: {reason}")

    if url:
        lines.append(f"\n🔗 [{url.split('/')[-2]}/{url.split('/')[-1]}]({url})")

    return "\n".join(lines)


def json_to_telegram(article: dict[str, Any]) -> str:
    """Render a single article for Telegram (HTML parse mode)."""
    import html

    analysis = article.get("analysis", {})
    title = html.escape(article.get("title", "Untitled")[:80])
    score = analysis.get("relevance_score", "?")
    summary = html.escape((article.get("summary") or "")[:150])
    tags = " ".join(f"#{t.replace('-', '_').replace(' ', '_')}" for t in article.get("tags", [])[:4])
    url = article.get("source_url", "")

    score_emoji = "🟢" if score >= 9 else "🔵" if score >= 7 else "🟡" if score >= 5 else "⚪"

    lines = [
        f"{score_emoji} <b>{title}</b>",
        f"评分: {score}/10  {tags}",
        "",
        summary,
    ]

    highlights = analysis.get("tech_highlights", [])
    if highlights:
        lines.append("")
        for h in highlights[:2]:
            lines.append(f"  • {html.escape(h[:120])}")

    if url:
        lines.append("")
        lines.append(f'<a href="{url}">🔗 查看源码</a>')

    return "\n".join(lines)


def generate_daily_digest(
    knowledge_dir: str | Path,
    date: str | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """Generate a daily AI knowledge digest from stored articles.

    Args:
        knowledge_dir: Path to ``knowledge/`` (contains ``articles/``).
        date: ISO date string ``YYYY-MM-DD``, defaults to today UTC.
        top_n: Number of top-scoring articles to include.

    Returns:
        Dict with ``date``, ``count``, and ``items`` (list of articles).
    """
    articles_dir = Path(knowledge_dir) / "articles"
    if not articles_dir.is_dir():
        return {"date": date or "", "count": 0, "items": []}

    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    items: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    # Collect URLs from all PREVIOUS days for dedup
    for path in sorted(articles_dir.glob("*.json")):
        fname = path.name[:10]  # YYYY-MM-DD prefix
        if fname >= date:
            continue  # skip current and future dates
        try:
            prev = json.loads(path.read_text(encoding="utf-8"))
            url = prev.get("source_url", "")
            if url:
                seen_urls.add(url)
        except (json.JSONDecodeError, OSError):
            pass

    # Load today's articles, skip duplicates
    for path in sorted(articles_dir.glob(f"{date}-*.json")):
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
            url = article.get("source_url", "")
            if url and url in seen_urls:
                continue  # already appeared on a previous day
            seen_urls.add(url)
            items.append(article)
        except (json.JSONDecodeError, OSError):
            pass

    # Sort by relevance_score desc
    items.sort(
        key=lambda a: a.get("analysis", {}).get("relevance_score", 0),
        reverse=True,
    )

    return {
        "date": date,
        "total_available": len(items),
        "count": min(len(items), top_n),
        "items": items[:top_n],
    }
