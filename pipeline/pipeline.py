"""Four-step knowledge-base automation pipeline.

    collect -> analyze -> organize -> save

Usage:
    python pipeline/pipeline.py --sources github --limit 5
    python pipeline/pipeline.py --sources github --limit 5 --dry-run
    python pipeline/pipeline.py --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Project root discovery ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
KNOWLEDGE_RAW = PROJECT_ROOT / "knowledge" / "raw"
KNOWLEDGE_ARTICLES = PROJECT_ROOT / "knowledge" / "articles"
KNOWLEDGE_METRICS = PROJECT_ROOT / "knowledge" / "metrics"
DEFAULT_DAILY_BUDGET_USD = 0.10
DEFAULT_MODEL_ROUTES = {
    "normal": "deepseek-v4-flash",
    "deep": "deepseek-v4-pro",
}


def ensure_dirs() -> None:
    """Ensure raw and articles directories exist."""
    KNOWLEDGE_RAW.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_ARTICLES.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_METRICS.mkdir(parents=True, exist_ok=True)


def read_daily_budget(default: float = DEFAULT_DAILY_BUDGET_USD) -> float:
    """Read the daily LLM budget from env, falling back to the default."""
    raw = os.getenv("AI_KB_DAILY_BUDGET_USD", "").strip()
    if not raw:
        return default

    try:
        budget = float(raw)
    except ValueError:
        logger.warning(
            "Invalid AI_KB_DAILY_BUDGET_USD=%r; using default %.2f",
            raw,
            default,
        )
        return default

    if budget < 0:
        logger.warning(
            "Negative AI_KB_DAILY_BUDGET_USD=%r; using default %.2f",
            raw,
            default,
        )
        return default

    return budget


def read_model_routes() -> dict[str, str]:
    """Read model routing config from environment variables."""
    normal_model = (
        os.getenv("AI_KB_ANALYSIS_MODEL")
        or os.getenv("DEEPSEEK_ANALYSIS_MODEL")
        or DEFAULT_MODEL_ROUTES["normal"]
    ).strip()
    deep_model = (
        os.getenv("AI_KB_DEEP_ANALYSIS_MODEL")
        or os.getenv("DEEPSEEK_DEEP_ANALYSIS_MODEL")
        or DEFAULT_MODEL_ROUTES["deep"]
    ).strip()

    return {
        "normal": normal_model or DEFAULT_MODEL_ROUTES["normal"],
        "deep": deep_model or DEFAULT_MODEL_ROUTES["deep"],
    }


def normalize_analysis_depth(depth: str) -> str:
    """Normalize analysis depth to a known model route."""
    normalized = depth.strip().lower()
    if normalized in DEFAULT_MODEL_ROUTES:
        return normalized

    logger.warning("Unknown analysis depth %r; using normal", depth)
    return "normal"


def select_analysis_model(
    depth: str,
    routes: dict[str, str] | None = None,
) -> str:
    """Select the model for a given analysis depth."""
    model_routes = routes or read_model_routes()
    return model_routes[normalize_analysis_depth(depth)]


# ══════════════════════════════════════════════════════════════════════
# Step 1: Collect
# ══════════════════════════════════════════════════════════════════════

GITHUB_SEARCH_QUERIES = [
    "AI agent framework stars:>50",
    "LLM tool use stars:>50",
    "MCP server stars:>50",
    "RAG application stars:>50",
]


def collect_github(limit: int = 5) -> list[dict[str, Any]]:
    """Collect trending AI/LLM/Agent repos from GitHub Search API."""
    import httpx

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for query in GITHUB_SEARCH_QUERIES:
        if len(items) >= limit:
            break
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(limit, 10),
            }
            headers = {"Accept": "application/vnd.github+json"}
            token = os.getenv("GITHUB_TOKEN", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

            resp = httpx.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()

            for repo in data.get("items", []):
                name = repo.get("full_name", "")
                if name in seen:
                    continue
                seen.add(name)

                items.append({
                    "name": name,
                    "url": repo.get("html_url", ""),
                    "summary": repo.get("description") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "unknown",
                    "topics": repo.get("topics", []),
                })
                if len(items) >= limit:
                    break
        except Exception:
            logger.warning("GitHub search query '%s' failed", query, exc_info=True)

    logger.info("Collected %d GitHub repos", len(items))
    return items


def collect_rss(limit: int = 5) -> list[dict[str, Any]]:
    """Collect AI/LLM articles from RSS feeds (placeholder)."""
    logger.info("RSS collection not yet implemented, returning empty list")
    return []


COLLECTORS = {
    "github": collect_github,
    "rss": collect_rss,
}


# ══════════════════════════════════════════════════════════════════════
# Step 2: Analyze
# ══════════════════════════════════════════════════════════════════════

ANALYSIS_SYSTEM_PROMPT = """你是一个 AI 技术分析助手。分析给定的 GitHub 项目，返回纯 JSON（不要 markdown，不要解释）。

JSON 格式:
{
  "summary": "中文摘要，不超过 80 字",
  "tech_highlights": ["亮点 1", "亮点 2"],
  "relevance_score": 8,
  "reason": "评分理由",
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "audience": ["developer", "researcher"]
}

评分标准:
- 9-10: 改变技术格局
- 7-8: 对开发/研究有直接帮助
- 5-6: 值得了解，短期价值有限
- 1-4: 可略过"""


def analyze_item(
    item: dict[str, Any],
    provider_name: str | None = None,
    source: str = "unknown",
    cost_tracker: Any | None = None,
    model_name: str | None = None,
) -> dict[str, Any] | None:
    """Use LLM to analyze a collected item and produce structured output."""
    from pipeline.model_client import chat_with_retry, create_provider

    if cost_tracker is not None and cost_tracker.is_budget_exceeded():
        logger.warning(
            "Daily LLM budget exceeded before analyzing %s; using fallback",
            item.get("name"),
        )
        return None

    prompt = json.dumps({
        "name": item.get("name", ""),
        "url": item.get("url", ""),
        "description": item.get("summary", ""),
        "language": item.get("language", ""),
        "topics": item.get("topics", []),
    }, ensure_ascii=False)

    provider = None
    try:
        provider = create_provider(provider_name, model_override=model_name)
        response = chat_with_retry(
            provider,
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"分析以下 GitHub 项目：\n{prompt}"},
            ],
            temperature=0.2,
            max_tokens=512,
        )

        if cost_tracker is not None:
            cost_tracker.add_call(
                source=source,
                item_name=str(item.get("name", "")),
                model=response.model or provider.model,
                usage=response.usage,
            )

        raw = response.content.strip()
        # Strip possible markdown code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        return parsed
    except Exception:
        logger.warning("Analysis failed for %s", item.get("name"), exc_info=True)
        return None
    finally:
        if provider is not None:
            provider.close()


def analyze_fallback(item: dict[str, Any]) -> dict[str, Any]:
    """Heuristic analysis without LLM call, used when API is unavailable."""
    name = item.get("name", "")
    desc = item.get("summary", "") or name
    topics = item.get("topics", [])
    stars = item.get("stars", 0)

    tech_highlights = [f"{item.get('language', 'N/A')} 项目, {stars} stars"]
    if topics:
        tech_highlights.append(f"标签: {', '.join(topics[:3])}")

    score = 7 if stars > 5000 else 6 if stars > 1000 else 5

    return {
        "summary": f"GitHub 项目 {name}，{desc[:60]}",
        "tech_highlights": tech_highlights,
        "relevance_score": score,
        "reason": f"基于热度({stars} stars)和标签({', '.join(topics[:3])})的启发式评分。",
        "suggested_tags": topics[:5] if topics else ["open-source"],
        "audience": ["developer"],
    }


def analyze(
    source: str,
    items: list[dict[str, Any]],
    provider: str | None = None,
    cost_tracker: Any | None = None,
    model_name: str | None = None,
) -> list[dict[str, Any]]:
    """Analyze collected items. Uses LLM if available, falls back to heuristic."""
    analyzed: list[dict[str, Any]] = []

    # Try LLM analysis for the first item to check connectivity
    if items:
        result = analyze_item(
            items[0],
            provider_name=provider,
            source=source,
            cost_tracker=cost_tracker,
            model_name=model_name,
        )
        if result is not None:
            # LLM works – use it for all
            logger.info("LLM analysis available, analyzing %d items", len(items))
            for i, item in enumerate(items):
                if i == 0:
                    analyzed.append(result)
                else:
                    if cost_tracker is not None and cost_tracker.is_budget_exceeded():
                        logger.warning(
                            "Daily LLM budget exceeded; fallback analysis for %s",
                            item.get("name"),
                        )
                        analyzed.append(analyze_fallback(item))
                        continue

                    r = analyze_item(
                        item,
                        provider_name=provider,
                        source=source,
                        cost_tracker=cost_tracker,
                        model_name=model_name,
                    )
                    if r:
                        analyzed.append(r)
                    else:
                        analyzed.append(analyze_fallback(item))
                time.sleep(0.5)  # Rate limit courtesy
        else:
            logger.info("LLM analysis unavailable, using heuristic for %d items", len(items))
            for item in items:
                analyzed.append(analyze_fallback(item))
    else:
        logger.warning("No items to analyze")

    logger.info("Analyzed %d items from source=%s", len(analyzed), source)
    return analyzed


# ══════════════════════════════════════════════════════════════════════
# Step 3: Organize
# ══════════════════════════════════════════════════════════════════════

SLUG_PATTERN = re.compile(r"[^a-z0-9-]")
REPO_TO_SLUG: dict[str, int] = {}


def make_slug(name: str) -> str:
    """Convert 'owner/repo' to a filename-safe slug."""
    slug = SLUG_PATTERN.sub("-", name.lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")

    # Deduplicate slugs within a run
    base = slug
    if slug in REPO_TO_SLUG:
        REPO_TO_SLUG[slug] += 1
        slug = f"{base}-{REPO_TO_SLUG[slug]}"
    else:
        REPO_TO_SLUG[slug] = 0
    return slug


def make_article_id(source: str, date_str: str, slug: str) -> str:
    """Build a stable article id that will not collide across pipeline runs."""
    source_prefix = "github" if source == "github" else source.replace(":", "-")
    compact_date = date_str.replace("-", "")
    return f"{source_prefix}-{compact_date}-{slug}"


def organize(
    source: str,
    collected_at: str,
    raw_items: list[dict[str, Any]],
    analyzed: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Transform raw items + analysis into standard article format."""
    articles: list[dict[str, Any]] = []
    date_str = collected_at[:10]
    source_short = "github-trending" if source == "github" else source

    for i, (raw, ana) in enumerate(zip(raw_items, analyzed), start=1):
        slug = make_slug(raw["name"])
        article_id = make_article_id(source, date_str, slug)

        article = {
            "id": article_id,
            "title": f"{raw['name']}: {ana.get('summary', 'AI 开源项目')[:60]}",
            "source": source_short,
            "source_url": raw["url"],
            "collected_at": collected_at,
            "summary": ana.get("summary", raw.get("summary", "")),
            "analysis": {
                "tech_highlights": ana.get("tech_highlights", []),
                "relevance_score": ana.get("relevance_score", 5),
                "reason": ana.get("reason", ""),
                "risks": ana.get("risks", []),
            },
            "tags": ana.get("suggested_tags", raw.get("topics", [])),
            "audience": ana.get("audience", ["developer"]),
            "status": "draft",
            "_slug": slug,
        }
        articles.append(article)
        logger.info("Organized: %s -> %s", raw["name"], slug)

    return articles


# ══════════════════════════════════════════════════════════════════════
# Step 4: Save
# ══════════════════════════════════════════════════════════════════════


def save_raw(
    source: str,
    collected_at: str,
    items: list[dict[str, Any]],
    dry_run: bool = False,
) -> Path:
    """Save raw collected data to knowledge/raw/."""
    date_str = collected_at[:10]
    raw_path = KNOWLEDGE_RAW / f"{source}-{date_str}.json"
    payload = {
        "source": source,
        "collected_at": collected_at,
        "items": items,
    }
    if dry_run:
        logger.info("[DRY-RUN] Would save raw data: %s (%d items)", raw_path, len(items))
    else:
        raw_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved raw data: %s (%d items)", raw_path, len(items))
    return raw_path


def save_articles(
    source: str,
    collected_at: str,
    articles: list[dict[str, Any]],
    dry_run: bool = False,
) -> list[Path]:
    """Save each article as a JSON file in knowledge/articles/."""
    date_str = collected_at[:10]
    source_short = "github-trending" if source == "github" else source
    paths: list[Path] = []

    for article in articles:
        slug = article.get("_slug", "")
        filename = f"{date_str}-{source_short}-{slug}.json"
        path = KNOWLEDGE_ARTICLES / filename

        if dry_run:
            logger.info("[DRY-RUN] Would save: %s", path)
        else:
            article.pop("_slug", None)
            path.write_text(
                json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Saved article: %s", path)
        paths.append(path)

    return paths


def save_cost_metrics(
    collected_at: str,
    cost_tracker: Any,
    dry_run: bool = False,
) -> Path:
    """Save LLM token usage and estimated cost metrics."""
    date_str = collected_at[:10]
    path = KNOWLEDGE_METRICS / f"cost-{date_str}.json"
    payload = cost_tracker.to_daily_payload(
        date_str=date_str,
        generated_at=collected_at,
    )

    if dry_run:
        logger.info("[DRY-RUN] Would save cost metrics: %s", path)
    else:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(
            "Saved cost metrics: %s (%d calls, $%.6f)",
            path,
            payload["total"]["calls"],
            payload["total"]["estimated_cost_usd"],
        )

    return path


# ══════════════════════════════════════════════════════════════════════
# Pipeline orchestrator
# ══════════════════════════════════════════════════════════════════════


def run_pipeline(
    sources: list[str],
    limit: int = 5,
    dry_run: bool = False,
    provider: str | None = None,
    analysis_depth: str = "normal",
) -> dict[str, Any]:
    """Execute the full collect -> analyze -> organize -> save pipeline."""
    from pipeline.cost_tracker import CostTracker

    ensure_dirs()
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stats: dict[str, Any] = {}
    cost_tracker = CostTracker(budget_usd=read_daily_budget())
    model_routes = read_model_routes()
    normalized_depth = normalize_analysis_depth(analysis_depth)
    analysis_model = select_analysis_model(normalized_depth, model_routes)
    logger.info("Daily LLM budget: $%.2f", cost_tracker.budget_usd)
    logger.info(
        "Analysis model route: depth=%s model=%s",
        normalized_depth,
        analysis_model,
    )

    for source in sources:
        collector = COLLECTORS.get(source)
        if collector is None:
            logger.warning("Unknown source: %s, skipping", source)
            continue

        logger.info("=== Source: %s ===", source)

        # Step 1: Collect
        raw_items = collector(limit=limit)
        if not raw_items:
            logger.warning("No items collected for source=%s", source)
            continue

        # Step 2: Analyze
        analyzed = analyze(
            source,
            raw_items,
            provider=provider,
            cost_tracker=cost_tracker,
            model_name=analysis_model,
        )

        # Step 3: Organize
        articles = organize(source, collected_at, raw_items, analyzed)

        # Step 4: Save
        raw_path = save_raw(source, collected_at, raw_items, dry_run=dry_run)
        article_paths = save_articles(source, collected_at, articles, dry_run=dry_run)

        stats[source] = {
            "collected": len(raw_items),
            "analyzed": len(analyzed),
            "articles": len(articles),
            "raw_path": str(raw_path),
            "article_paths": [str(p) for p in article_paths],
        }

    metrics_path = save_cost_metrics(
        collected_at=collected_at,
        cost_tracker=cost_tracker,
        dry_run=dry_run,
    )
    stats["_cost"] = {
        "metrics_path": str(metrics_path),
        "budget": cost_tracker.budget_status(),
        "total": cost_tracker.total(),
        "runs": cost_tracker.summarize_runs(),
    }
    stats["_model_route"] = {
        "analysis_depth": normalized_depth,
        "analysis_model": analysis_model,
        "routes": model_routes,
    }

    return stats


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Knowledge Base Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["github"],
        choices=["github", "rss"],
        help="Data sources to collect from (default: github)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max items per source (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip writing article files",
    )
    parser.add_argument(
        "--provider",
        choices=["deepseek", "qwen", "openai"],
        default=None,
        help="LLM provider for analysis (default: from env)",
    )
    parser.add_argument(
        "--analysis-depth",
        choices=["normal", "deep"],
        default=os.getenv("AI_KB_ANALYSIS_DEPTH", "normal"),
        help="Analysis model route: normal uses flash, deep uses pro",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting pipeline: sources=%s limit=%s dry_run=%s",
                 args.sources, args.limit, args.dry_run)

    try:
        stats = run_pipeline(
            sources=args.sources,
            limit=args.limit,
            dry_run=args.dry_run,
            provider=args.provider,
            analysis_depth=args.analysis_depth,
        )
    except Exception:
        logger.exception("Pipeline failed")
        return 1

    # Print summary
    source_stats = {src: value for src, value in stats.items() if not src.startswith("_")}
    total_collected = sum(s["collected"] for s in source_stats.values())
    total_articles = sum(s["articles"] for s in source_stats.values())
    print(f"\nPipeline complete: {total_collected} collected, {total_articles} articles")
    for src, s in source_stats.items():
        print(f"  {src}: {s['collected']} items -> {s['articles']} articles "
              f"{'(dry-run)' if args.dry_run else ''}")
        print(f"    raw: {s['raw_path']}")

    model_route = stats.get("_model_route", {})
    if model_route:
        print("  model_route:")
        print(
            "    analysis: "
            f"{model_route['analysis_depth']} -> {model_route['analysis_model']}"
        )

    cost_stats = stats.get("_cost", {})
    if cost_stats:
        total = cost_stats["total"]
        budget = cost_stats["budget"]
        print("  cost:")
        print(f"    metrics: {cost_stats['metrics_path']}")
        print(
            "    budget: "
            f"${budget['budget_usd']:.2f}, remaining ${budget['remaining_usd']:.6f}, "
            f"exceeded={budget['exceeded']}"
        )
        print(
            "    llm_calls: "
            f"{total['calls']} calls, {total['total_tokens']} tokens, "
            f"${total['estimated_cost_usd']:.6f}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
