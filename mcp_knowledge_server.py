"""MCP Knowledge Base Server — JSON-RPC 2.0 over stdio.

Three tools:
    search_articles(keyword, limit=5)  – full-text search across articles
    get_article(article_id)            – retrieve a single article by id
    knowledge_stats()                  – summary statistics of the knowledge base

Run:
    python mcp_knowledge_server.py
    # Reads from stdin, writes JSON-RPC responses to stdout.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ARTICLES_DIR = Path(__file__).resolve().parent / "knowledge" / "articles"

# ─── Article Cache ───────────────────────────────────────────────────
_articles: list[dict[str, Any]] = []
_articles_by_id: dict[str, dict[str, Any]] = {}


def _load_articles() -> None:
    """Load all article JSON files from knowledge/articles/ into memory."""
    global _articles, _articles_by_id
    if _articles:
        return
    _articles = []
    _articles_by_id = {}
    if not ARTICLES_DIR.is_dir():
        return
    for path in sorted(ARTICLES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _articles.append(data)
            aid = data.get("id", "")
            if aid:
                _articles_by_id[aid] = data
        except (json.JSONDecodeError, OSError):
            pass


def _score_item(article: dict[str, Any], keyword: str) -> float:
    """Simple full-text relevance score against keyword tokens."""
    tokens = keyword.lower().split()
    if not tokens:
        return 0.0

    text_fields = [
        article.get("title", ""),
        article.get("summary", ""),
        *article.get("tags", []),
        article.get("analysis", {}).get("reason", ""),
        *(article.get("analysis", {}).get("tech_highlights", [])),
    ]
    blob = " ".join(text_fields).lower()

    score = sum(1.0 for t in tokens if t in blob)
    score /= len(tokens)
    return score


# ─── Tool Handlers ────────────────────────────────────────────────────

TOOL_SEARCH = "search_articles"
TOOL_GET = "get_article"
TOOL_STATS = "knowledge_stats"


def handle_search_articles(params: dict[str, Any]) -> dict[str, Any]:
    """Search articles by keyword, return ranked results."""
    _load_articles()
    keyword = (params.get("keyword") or "").strip()
    limit = max(1, min(int(params.get("limit", 5)), 50))

    if not keyword:
        return {"items": [], "total": len(_articles)}

    scored = [(_score_item(a, keyword), a) for a in _articles]
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, article in scored:
        if score <= 0:
            continue
        results.append({
            "id": article.get("id"),
            "title": article.get("title"),
            "summary": article.get("summary"),
            "source": article.get("source"),
            "source_url": article.get("source_url"),
            "relevance_score": article.get("analysis", {}).get("relevance_score"),
            "tags": article.get("tags", []),
            "status": article.get("status"),
            "search_score": round(score, 2),
        })
        if len(results) >= limit:
            break

    return {"items": results, "total": len(results), "keyword": keyword}


def handle_get_article(params: dict[str, Any]) -> dict[str, Any]:
    """Retrieve a single article by id."""
    _load_articles()
    article_id = (params.get("article_id") or "").strip()
    article = _articles_by_id.get(article_id)
    if article is None:
        return {"error": f"Article not found: {article_id}"}
    return article


def handle_knowledge_stats(_params: dict[str, Any]) -> dict[str, Any]:
    """Return summary statistics of the knowledge base."""
    _load_articles()
    sources: dict[str, int] = {}
    tags: dict[str, int] = {}
    scores: list[int] = []
    statuses: dict[str, int] = {}

    for a in _articles:
        src = a.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

        for t in a.get("tags", []):
            tags[t] = tags.get(t, 0) + 1

        s = a.get("analysis", {}).get("relevance_score")
        if isinstance(s, (int, float)):
            scores.append(int(s))

        st = a.get("status", "unknown")
        statuses[st] = statuses.get(st, 0) + 1

    top_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_articles": len(_articles),
        "by_source": sources,
        "by_status": statuses,
        "score_distribution": {
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
            "avg": round(sum(scores) / len(scores), 1) if scores else 0,
        },
        "top_tags": [{"tag": t, "count": c} for t, c in top_tags],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


TOOL_DEFINITIONS = [
    {
        "name": TOOL_SEARCH,
        "description": "搜索本地知识库文章，按关键词匹配返回排序结果。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，支持空格分隔多个词。",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量上限，默认 5，最大 50。",
                    "default": 5,
                },
            },
            "required": ["keyword"],
        },
    },
    {
        "name": TOOL_GET,
        "description": "按 ID 获取单篇知识文章全文。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "article_id": {
                    "type": "string",
                    "description": "文章的 id 字段，如 github-20260429-001。",
                },
            },
            "required": ["article_id"],
        },
    },
    {
        "name": TOOL_STATS,
        "description": "获取知识库统计信息：总数、来源分布、评分分布、热门标签。",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]

TOOL_HANDLERS = {
    TOOL_SEARCH: handle_search_articles,
    TOOL_GET: handle_get_article,
    TOOL_STATS: handle_knowledge_stats,
}

# ─── JSON-RPC 2.0 Dispatcher ──────────────────────────────────────────

SERVER_NAME = "ai-knowledge-base-mcp"
SERVER_VERSION = "0.1.0"


def make_response(id_: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def make_error(id_: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle_request(req: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a single JSON-RPC request. Returns None for notifications."""
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    # ── initialize ──
    if method == "initialize":
        return make_response(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "capabilities": {"tools": {}},
        })

    # ── notifications (no id) ──
    if req_id is None:
        if method == "notifications/initialized":
            return None
        return None

    # ── tools/list ──
    if method == "tools/list":
        return make_response(req_id, {"tools": TOOL_DEFINITIONS})

    # ── tools/call ──
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = TOOL_HANDLERS.get(tool_name)
        if handler is None:
            return make_error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(arguments)
            return make_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
            })
        except Exception as exc:
            return make_error(req_id, -32603, f"Tool error: {exc}")

    # ── Unknown method ──
    return make_error(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    """Run the MCP server via stdio JSON-RPC 2.0."""
    # Stderr for server logs, stdout for JSON-RPC
    log = sys.stderr

    log.write(f"[{SERVER_NAME} v{SERVER_VERSION}] Starting...\n")
    log.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            log.write(f"Invalid JSON: {line[:100]}\n")
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    log.write(f"[{SERVER_NAME}] Shutting down.\n")
    log.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
