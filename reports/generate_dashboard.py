"""Generate a static HTML dashboard from knowledge article JSON files."""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "dashboard.html"


def parse_datetime(value: str) -> datetime:
    """Parse an ISO datetime string, falling back to epoch on invalid input."""
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Invalid datetime: %s", value)
        return datetime.fromtimestamp(0, tz=timezone.utc)


def safe_score(value: Any) -> int:
    """Normalize a relevance score into the 0-10 range."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, score))


def normalize_list(value: Any) -> list[str]:
    """Normalize a JSON value into a clean list of strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def load_articles(articles_dir: Path) -> list[dict[str, Any]]:
    """Load and normalize all article JSON files from a directory."""
    articles: list[dict[str, Any]] = []

    for path in sorted(articles_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSON: %s", path)
            continue

        analysis = raw.get("analysis") if isinstance(raw.get("analysis"), dict) else {}
        collected_at = str(raw.get("collected_at", ""))
        score = safe_score(analysis.get("relevance_score"))

        articles.append({
            "id": str(raw.get("id", path.stem)),
            "file": str(path.relative_to(PROJECT_ROOT)),
            "title": str(raw.get("title", "Untitled")),
            "source": str(raw.get("source", "unknown")),
            "source_url": str(raw.get("source_url", "")),
            "collected_at": collected_at,
            "date": collected_at[:10] if collected_at else "unknown",
            "summary": str(raw.get("summary", "")),
            "score": score,
            "reason": str(analysis.get("reason", "")),
            "tech_highlights": normalize_list(analysis.get("tech_highlights")),
            "risks": normalize_list(analysis.get("risks")),
            "tags": normalize_list(raw.get("tags")),
            "audience": normalize_list(raw.get("audience")),
            "status": str(raw.get("status", "draft")),
        })

    articles.sort(
        key=lambda item: (parse_datetime(item["collected_at"]), item["score"]),
        reverse=True,
    )
    return articles


def build_stats(articles: list[dict[str, Any]]) -> dict[str, Any]:
    """Build dashboard-level aggregate statistics."""
    source_counts = Counter(article["source"] for article in articles)
    tag_counts = Counter(
        tag for article in articles for tag in article.get("tags", [])
    )
    status_counts = Counter(article["status"] for article in articles)
    score_counts = Counter(article["score"] for article in articles)
    daily_counts: dict[str, int] = defaultdict(int)

    for article in articles:
        daily_counts[article["date"]] += 1

    latest_date = max(daily_counts.keys(), default="-")
    latest_count = daily_counts.get(latest_date, 0)
    total = len(articles)
    score_sum = sum(article["score"] for article in articles)

    return {
        "total": total,
        "latest_date": latest_date,
        "latest_count": latest_count,
        "avg_score": round(score_sum / total, 1) if total else 0,
        "high_score_count": sum(1 for article in articles if article["score"] >= 9),
        "source_counts": dict(source_counts),
        "status_counts": dict(status_counts),
        "score_counts": {str(score): score_counts.get(score, 0) for score in range(10, -1, -1)},
        "top_tags": tag_counts.most_common(16),
        "daily_counts": dict(sorted(daily_counts.items(), reverse=True)),
    }


def data_timestamp(articles: list[dict[str, Any]]) -> str:
    """Return a stable timestamp based on the newest article data."""
    if not articles:
        return "-"

    latest = max(parse_datetime(article["collected_at"]) for article in articles)
    return latest.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def json_for_script(payload: dict[str, Any]) -> str:
    """Serialize JSON safely for embedding inside a script tag."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def render_html(payload: dict[str, Any]) -> str:
    """Render the static dashboard HTML."""
    data_json = json_for_script(payload)
    generated_at = payload["generated_at"]
    latest_date = payload["stats"]["latest_date"]

    template = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Knowledge Base Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --surface: #ffffff;
      --surface-soft: #eef2f7;
      --border: #d9e0ea;
      --text: #172033;
      --muted: #617085;
      --blue: #2563a9;
      --green: #1f7a57;
      --amber: #a66a10;
      --red: #b4233a;
      --shadow: 0 12px 30px rgba(23, 32, 51, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    a {
      color: var(--blue);
      text-decoration: none;
    }

    a:hover {
      text-decoration: underline;
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      padding: 28px 32px;
      border-bottom: 1px solid var(--border);
      background: var(--surface);
    }

    .eyebrow {
      margin: 0 0 6px;
      color: var(--green);
      font-size: 13px;
      font-weight: 700;
    }

    h1, h2, h3, p {
      margin-top: 0;
    }

    h1 {
      margin-bottom: 8px;
      font-size: 38px;
      line-height: 1.1;
    }

    .subtitle {
      max-width: 760px;
      margin-bottom: 0;
      color: var(--muted);
      font-size: 15px;
    }

    .meta {
      display: grid;
      grid-template-columns: auto auto;
      align-content: start;
      gap: 8px 14px;
      min-width: 280px;
      padding-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }

    .meta strong {
      color: var(--text);
      font-weight: 700;
      text-align: right;
    }

    main {
      width: min(1440px, calc(100vw - 32px));
      margin: 24px auto 48px;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 14px;
      margin-bottom: 18px;
    }

    .metric {
      min-height: 112px;
      padding: 18px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .metric span {
      display: block;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 13px;
    }

    .metric strong {
      display: block;
      font-size: 34px;
      line-height: 1;
    }

    .metric small {
      display: block;
      margin-top: 10px;
      color: var(--muted);
    }

    .workspace {
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }

    .panel,
    .article {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .panel {
      padding: 18px;
      margin-bottom: 14px;
    }

    .panel h2,
    .section-title h2 {
      margin-bottom: 14px;
      font-size: 17px;
    }

    label {
      display: block;
      margin: 12px 0 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
    }

    input,
    select {
      width: 100%;
      height: 40px;
      padding: 0 11px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      font: inherit;
    }

    input:focus,
    select:focus {
      outline: 2px solid rgba(37, 99, 169, 0.18);
      border-color: var(--blue);
    }

    .tag-cloud {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .tag-button,
    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 9px;
      border: 1px solid var(--border);
      border-radius: 999px;
      background: var(--surface-soft);
      color: var(--text);
      font-size: 12px;
      line-height: 1.2;
    }

    .tag-button {
      cursor: pointer;
    }

    .tag-button.active {
      border-color: var(--green);
      background: #e8f5ef;
      color: var(--green);
      font-weight: 700;
    }

    .score-bars {
      display: grid;
      gap: 8px;
    }

    .score-row {
      display: grid;
      grid-template-columns: 32px 1fr 28px;
      gap: 8px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
    }

    .bar-track {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: var(--surface-soft);
    }

    .bar-fill {
      height: 100%;
      border-radius: inherit;
      background: var(--blue);
    }

    .section-title {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 12px;
    }

    .section-title p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .article-list {
      display: grid;
      gap: 12px;
    }

    .article {
      padding: 18px;
    }

    .article-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 14px;
      align-items: start;
    }

    .article h3 {
      margin-bottom: 8px;
      font-size: 18px;
      line-height: 1.35;
    }

    .score {
      display: inline-grid;
      place-items: center;
      width: 52px;
      height: 52px;
      border-radius: 8px;
      color: #fff;
      font-size: 22px;
      font-weight: 800;
    }

    .score.high {
      background: var(--green);
    }

    .score.mid {
      background: var(--amber);
    }

    .score.low {
      background: var(--red);
    }

    .summary {
      margin-bottom: 12px;
      color: #2f3a4d;
    }

    .article-meta,
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .article-meta {
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 13px;
    }

    .highlights {
      margin: 14px 0 0;
      padding-left: 18px;
      color: #2f3a4d;
    }

    .highlights li {
      margin-bottom: 6px;
    }

    .reason {
      margin-top: 12px;
      padding: 12px;
      border-left: 3px solid var(--blue);
      background: #edf4fb;
      color: #2f3a4d;
      font-size: 14px;
    }

    .empty {
      padding: 32px;
      border: 1px dashed var(--border);
      border-radius: 8px;
      color: var(--muted);
      text-align: center;
      background: var(--surface);
    }

    @media (max-width: 980px) {
      .topbar,
      .workspace {
        grid-template-columns: 1fr;
      }

      .topbar {
        display: grid;
      }

      .metrics {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .meta strong {
        text-align: left;
      }
    }

    @media (max-width: 620px) {
      .topbar {
        padding: 22px 18px;
      }

      main {
        width: min(100vw - 20px, 1440px);
      }

      .metrics {
        grid-template-columns: 1fr;
      }

      h1 {
        font-size: 30px;
      }

      .article-header {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div>
      <p class="eyebrow">AI Knowledge Base</p>
      <h1>知识库 Dashboard</h1>
      <p class="subtitle">每日 AI/LLM/Agent 技术动态与评分汇总。</p>
    </div>
    <div class="meta">
      <span>数据时间 UTC</span><strong>__GENERATED_AT__</strong>
      <span>最新批次</span><strong>__LATEST_DATE__</strong>
    </div>
  </header>

  <main>
    <section class="metrics" aria-label="overview metrics">
      <div class="metric"><span>知识条目</span><strong id="metricTotal">0</strong><small>全部已归档 JSON</small></div>
      <div class="metric"><span>最新批次</span><strong id="metricLatest">0</strong><small id="metricLatestDate">-</small></div>
      <div class="metric"><span>平均评分</span><strong id="metricAverage">0</strong><small>relevance_score</small></div>
      <div class="metric"><span>高价值条目</span><strong id="metricHigh">0</strong><small>评分 9-10</small></div>
    </section>

    <section class="workspace">
      <aside>
        <div class="panel">
          <h2>筛选</h2>
          <label for="query">关键词</label>
          <input id="query" type="search" placeholder="搜索标题、摘要、标签">

          <label for="sourceFilter">来源</label>
          <select id="sourceFilter"></select>

          <label for="scoreFilter">最低评分</label>
          <select id="scoreFilter">
            <option value="0">全部评分</option>
            <option value="9">9 分以上</option>
            <option value="8">8 分以上</option>
            <option value="7">7 分以上</option>
            <option value="5">5 分以上</option>
          </select>

          <label for="statusFilter">状态</label>
          <select id="statusFilter"></select>
        </div>

        <div class="panel">
          <h2>热门标签</h2>
          <div class="tag-cloud" id="tagCloud"></div>
        </div>

        <div class="panel">
          <h2>分数分布</h2>
          <div class="score-bars" id="scoreBars"></div>
        </div>
      </aside>

      <section>
        <div class="section-title">
          <h2>知识条目</h2>
          <p id="visibleCount">0 条</p>
        </div>
        <div class="article-list" id="articleList"></div>
      </section>
    </section>
  </main>

  <script id="dashboard-data" type="application/json">__DATA__</script>
  <script>
    const payload = JSON.parse(document.getElementById("dashboard-data").textContent);
    const state = { tag: "all" };

    const queryInput = document.getElementById("query");
    const sourceFilter = document.getElementById("sourceFilter");
    const scoreFilter = document.getElementById("scoreFilter");
    const statusFilter = document.getElementById("statusFilter");
    const tagCloud = document.getElementById("tagCloud");
    const scoreBars = document.getElementById("scoreBars");
    const articleList = document.getElementById("articleList");
    const visibleCount = document.getElementById("visibleCount");

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function scoreClass(score) {
      if (score >= 9) return "high";
      if (score >= 7) return "mid";
      return "low";
    }

    function option(value, label) {
      const item = document.createElement("option");
      item.value = value;
      item.textContent = label;
      return item;
    }

    function setupMetrics() {
      document.getElementById("metricTotal").textContent = payload.stats.total;
      document.getElementById("metricLatest").textContent = payload.stats.latest_count;
      document.getElementById("metricLatestDate").textContent = payload.stats.latest_date;
      document.getElementById("metricAverage").textContent = payload.stats.avg_score;
      document.getElementById("metricHigh").textContent = payload.stats.high_score_count;
    }

    function setupFilters() {
      const sources = [...new Set(payload.articles.map((article) => article.source))].sort();
      sourceFilter.appendChild(option("all", "全部来源"));
      sources.forEach((source) => sourceFilter.appendChild(option(source, source)));

      const statuses = [...new Set(payload.articles.map((article) => article.status))].sort();
      statusFilter.appendChild(option("all", "全部状态"));
      statuses.forEach((status) => statusFilter.appendChild(option(status, status)));

      [queryInput, sourceFilter, scoreFilter, statusFilter].forEach((item) => {
        item.addEventListener("input", renderArticles);
      });
    }

    function setupTags() {
      tagCloud.innerHTML = "";
      const all = document.createElement("button");
      all.className = "tag-button active";
      all.type = "button";
      all.textContent = "全部";
      all.addEventListener("click", () => setTag("all"));
      tagCloud.appendChild(all);

      payload.stats.top_tags.forEach(([tag, count]) => {
        const button = document.createElement("button");
        button.className = "tag-button";
        button.type = "button";
        button.dataset.tag = tag;
        button.textContent = `${tag} ${count}`;
        button.addEventListener("click", () => setTag(tag));
        tagCloud.appendChild(button);
      });
    }

    function setTag(tag) {
      state.tag = tag;
      document.querySelectorAll(".tag-button").forEach((button) => {
        button.classList.toggle("active", (button.dataset.tag || "all") === tag);
      });
      renderArticles();
    }

    function setupScoreBars() {
      const maxCount = Math.max(1, ...Object.values(payload.stats.score_counts));
      scoreBars.innerHTML = Object.entries(payload.stats.score_counts)
        .map(([score, count]) => {
          const width = Math.round((count / maxCount) * 100);
          return `
            <div class="score-row">
              <span>${escapeHtml(score)} 分</span>
              <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
              <span>${escapeHtml(count)}</span>
            </div>
          `;
        })
        .join("");
    }

    function articleMatches(article) {
      const query = queryInput.value.trim().toLowerCase();
      const source = sourceFilter.value;
      const minScore = Number(scoreFilter.value);
      const status = statusFilter.value;
      const haystack = [
        article.title,
        article.summary,
        article.reason,
        article.source,
        article.status,
        ...(article.tags || []),
        ...(article.tech_highlights || [])
      ].join(" ").toLowerCase();

      if (query && !haystack.includes(query)) return false;
      if (source !== "all" && article.source !== source) return false;
      if (status !== "all" && article.status !== status) return false;
      if (article.score < minScore) return false;
      if (state.tag !== "all" && !(article.tags || []).includes(state.tag)) return false;
      return true;
    }

    function renderArticle(article) {
      const tags = (article.tags || [])
        .map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`)
        .join("");
      const highlights = (article.tech_highlights || [])
        .map((item) => `<li>${escapeHtml(item)}</li>`)
        .join("");
      const sourceLink = article.source_url
        ? `<a href="${escapeHtml(article.source_url)}" target="_blank" rel="noreferrer">打开来源</a>`
        : "";

      return `
        <article class="article">
          <div class="article-header">
            <div>
              <h3>${escapeHtml(article.title)}</h3>
              <div class="article-meta">
                <span>${escapeHtml(article.date)}</span>
                <span>${escapeHtml(article.source)}</span>
                <span>${escapeHtml(article.status)}</span>
                ${sourceLink}
              </div>
            </div>
            <div class="score ${scoreClass(article.score)}">${escapeHtml(article.score)}</div>
          </div>
          <p class="summary">${escapeHtml(article.summary)}</p>
          <div class="chips">${tags}</div>
          ${highlights ? `<ul class="highlights">${highlights}</ul>` : ""}
          ${article.reason ? `<div class="reason">${escapeHtml(article.reason)}</div>` : ""}
        </article>
      `;
    }

    function renderArticles() {
      const visible = payload.articles.filter(articleMatches);
      visibleCount.textContent = `${visible.length} 条`;

      if (!visible.length) {
        articleList.innerHTML = '<div class="empty">没有匹配的知识条目</div>';
        return;
      }

      articleList.innerHTML = visible.map(renderArticle).join("");
    }

    setupMetrics();
    setupFilters();
    setupTags();
    setupScoreBars();
    renderArticles();
  </script>
</body>
</html>
"""
    return (
        template.replace("__DATA__", data_json)
        .replace("__GENERATED_AT__", generated_at)
        .replace("__LATEST_DATE__", latest_date)
    )


def generate_dashboard(articles_dir: Path, output_path: Path) -> Path:
    """Generate the dashboard HTML file and return its path."""
    articles = load_articles(articles_dir)
    payload = {
        "generated_at": data_timestamp(articles),
        "articles": articles,
        "stats": build_stats(articles),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(payload), encoding="utf-8")
    logger.info("Generated dashboard: %s (%d articles)", output_path, len(articles))
    return output_path


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(description="Generate AI knowledge dashboard")
    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=ARTICLES_DIR,
        help="Directory containing article JSON files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Dashboard HTML output path",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the dashboard generator."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    generate_dashboard(args.articles_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
