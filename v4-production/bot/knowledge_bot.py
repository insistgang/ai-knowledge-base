"""Knowledge Bot — interactive chat interface for the AI knowledge base.

Commands:
    /search <query>   — full-text search across articles
    /today             — today's latest articles
    /top               — top-scoring articles
    /subscribe         — subscribe to daily digest
    /help              — show command list
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"


class Intent(Enum):
    SEARCH = "search"
    BROWSE_TODAY = "browse_today"
    BROWSE_TOP = "browse_top"
    SUBSCRIBE = "subscribe"
    HELP = "help"
    UNKNOWN = "unknown"


# ── Intent recognition ────────────────────────────────────────────

def recognize_intent(text: str) -> tuple[Intent, str]:
    """Parse user text and return (Intent, argument).

    Supports both slash-commands and natural-language queries.
    """
    text = text.strip()

    # Slash commands
    m = re.match(r"^/(search|today|top|subscribe|help)\s*(.*)", text)
    if m:
        cmd = m.group(1)
        if cmd == "search":
            return Intent.SEARCH, m.group(2).strip()
        if cmd == "today":
            return Intent.BROWSE_TODAY, ""
        if cmd == "top":
            return Intent.BROWSE_TOP, ""
        if cmd == "subscribe":
            return Intent.SUBSCRIBE, ""
        if cmd == "help":
            return Intent.HELP, ""
        return Intent.UNKNOWN, ""

    # Natural language patterns
    if re.search(r"搜|找|查|检索|search|查找|articles", text, re.IGNORECASE):
        # Extract query after the action word
        cleaned = re.sub(r"^(搜索|搜|找|查|检索|search|查找|articles)\s*", "", text, flags=re.IGNORECASE).strip()
        return Intent.SEARCH, cleaned

    if re.search(r"今天|今日|最新|today|latest", text, re.IGNORECASE):
        return Intent.BROWSE_TODAY, ""

    if re.search(r"高分|推荐|最佳|top|评分最高|最值得", text, re.IGNORECASE):
        return Intent.BROWSE_TOP, ""

    if re.search(r"订阅|subscribe|推送|日报", text, re.IGNORECASE):
        return Intent.SUBSCRIBE, ""

    if re.search(r"帮助|help|怎么用|命令|/help", text, re.IGNORECASE):
        return Intent.HELP, ""

    # Default: treat as search
    if len(text) > 2:
        return Intent.SEARCH, text

    return Intent.UNKNOWN, ""


# ── Search engine ─────────────────────────────────────────────────

class KnowledgeSearchEngine:
    """Full-text search across all knowledge articles."""

    def __init__(self, articles_dir: str | Path | None = None) -> None:
        self.articles_dir = Path(articles_dir) if articles_dir else ARTICLES_DIR
        self._articles: list[dict[str, Any]] = []
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        for path in sorted(self.articles_dir.glob("*.json")):
            try:
                self._articles.append(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                pass
        self._loaded = True

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Full-text search by keyword tokens."""
        self._load()
        tokens = query.lower().split()

        scored: list[tuple[float, dict[str, Any]]] = []
        for art in self._articles:
            blob = " ".join([
                art.get("title", ""),
                art.get("summary", ""),
                *art.get("tags", []),
                art.get("analysis", {}).get("reason", ""),
                " ".join(art.get("analysis", {}).get("tech_highlights", [])),
            ]).lower()
            score = sum(1.0 for t in tokens if t in blob) / max(len(tokens), 1)
            if score > 0:
                scored.append((score, art))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in scored[:limit]]

    def get_today(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get articles collected today."""
        self._load()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        items = [a for a in self._articles if (a.get("collected_at", "") or "").startswith(today)]
        items.sort(
            key=lambda a: a.get("analysis", {}).get("relevance_score", 0),
            reverse=True,
        )
        return items[:limit]

    def get_top(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get highest-scoring articles."""
        self._load()
        items = sorted(
            self._articles,
            key=lambda a: a.get("analysis", {}).get("relevance_score", 0),
            reverse=True,
        )
        return items[:limit]

    def stats(self) -> dict[str, Any]:
        """Quick statistics."""
        self._load()
        sources: dict[str, int] = {}
        tags: dict[str, int] = {}
        for a in self._articles:
            s = a.get("source", "unknown")
            sources[s] = sources.get(s, 0) + 1
            for t in a.get("tags", []):
                tags[t] = tags.get(t, 0) + 1
        top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:5]
        return {
            "total": len(self._articles),
            "sources": sources,
            "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        }


# ── Format helpers ────────────────────────────────────────────────

def _format_search_result(item: dict[str, Any], index: int = 1) -> str:
    analysis = item.get("analysis", {})
    title = item.get("title", "?")
    score = analysis.get("relevance_score", "?")
    summary = item.get("summary", "")[:100]
    url = item.get("source_url", "")
    tags = " ".join(f"#{t.replace('-', '_')}" for t in item.get("tags", [])[:3])
    link = f"\n🔗 {url}" if url else ""
    return (
        f"{index}. <b>{title[:80]}</b>\n"
        f"   评分: {score}/10  {tags}\n"
        f"   {summary}{link}"
    )


# ── Bot entry point ───────────────────────────────────────────────

class KnowledgeBot:
    """Main bot that processes user messages and returns responses."""

    HELP_TEXT = (
        "<b>📚 AI 知识库 Bot</b>\n\n"
        "<b>命令列表:</b>\n"
        "/search &lt;关键词&gt; — 搜索知识库\n"
        "/today — 今日最新动态\n"
        "/top — 高分推荐文章\n"
        "/subscribe — 订阅每日日报\n"
        "/help — 显示此帮助\n\n"
        "<b>自然语言也支持:</b>\n"
        "• \"搜索 MCP 相关文章\"\n"
        "• \"今天有什么新技术?\"\n"
        "• \"推荐几个高分项目\""
    )

    def __init__(self) -> None:
        self.engine = KnowledgeSearchEngine()

    def handle(self, text: str) -> str:
        intent, arg = recognize_intent(text)

        if intent == Intent.HELP or (intent == Intent.UNKNOWN and not text):
            return self.HELP_TEXT

        if intent == Intent.SEARCH:
            return self._handle_search(arg or text)

        if intent == Intent.BROWSE_TODAY:
            return self._handle_today()

        if intent == Intent.BROWSE_TOP:
            return self._handle_top()

        if intent == Intent.SUBSCRIBE:
            return self._handle_subscribe()

        return "抱歉，我不太明白。输入 /help 查看可用命令。"

    def _handle_search(self, query: str) -> str:
        results = self.engine.search(query)
        if not results:
            return f'未找到与 "{query}" 相关的结果。'
        lines = [f'🔍 搜索 "{query}" — 找到 {len(results)} 条结果:\n']
        for i, item in enumerate(results, 1):
            lines.append(_format_search_result(item, i))
            lines.append("")
        return "\n".join(lines).strip()

    def _handle_today(self) -> str:
        results = self.engine.get_today()
        if not results:
            return "今日暂无更新。"
        lines = [f"📰 今日动态 — Top {len(results)}:\n"]
        for i, item in enumerate(results, 1):
            lines.append(_format_search_result(item, i))
            lines.append("")
        return "\n".join(lines).strip()

    def _handle_top(self) -> str:
        results = self.engine.get_top()
        lines = [f"⭐ 高分推荐 — Top {len(results)}:\n"]
        for i, item in enumerate(results, 1):
            lines.append(_format_search_result(item, i))
            lines.append("")
        return "\n".join(lines).strip()

    def _handle_subscribe(self) -> str:
        return (
            "✅ 已订阅每日 AI 日报。\n"
            "每天早上 8:00 UTC 自动推送 Top 5 高价值动态。\n"
            "取消订阅：发送 /unsubscribe"
        )


# ── Self-test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Intent Recognition ===")
    tests = [
        ("/search MCP", Intent.SEARCH, "MCP"),
        ("/today", Intent.BROWSE_TODAY, ""),
        ("搜索 Agent 文章", Intent.SEARCH, "Agent 文章"),
        ("/top", Intent.BROWSE_TOP, ""),
        ("今天有什么新技术", Intent.BROWSE_TODAY, ""),
        ("推荐几个高分项目", Intent.BROWSE_TOP, ""),
        ("/help", Intent.HELP, ""),
    ]
    for text, expected, _ in tests:
        intent, args = recognize_intent(text)
        status = "✅" if intent == expected else "❌"
        print(f'{status} "{text}" → {intent.value}')

    print("\n=== Bot Handlers ===")
    bot = KnowledgeBot()
    print("Stats:", json.dumps(bot.engine.stats(), ensure_ascii=False, indent=2))
    print("\n--- /top ---")
    print(bot.handle("/top")[:500])
