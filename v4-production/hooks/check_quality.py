"""Quality scoring for knowledge article JSON files. Outputs A/B/C grades per article."""

import json
import sys
import os
import re
from typing import Dict, List, Tuple

# ——— Hollow / filler words to penalize ———
HOLLOW_WORDS = re.compile(
    r"非常|很多|各种|一些|某种|等等|优化|提升|改进"
    r"|强大|强大功能|充分|显著|极大|卓越|优秀"
)

# ——— Good specificity signals ———
SPECIFIC_PATTERNS = re.compile(
    r"\d+[kKmM]|BM25|FTS5|SQLite|MCP|RAG|GPU|API|SDK|PoW|arXiv|CLI|[A-Z]{2,}|MB|GB|token"
)

# ——— Dimensions and weights ———
WEIGHTS = {
    "summary_quality": 0.25,
    "tech_depth": 0.30,
    "format_compliance": 0.20,
    "tag_precision": 0.10,
    "hollow_word_penalty": 0.15,
}


def score_summary(summary: str) -> Tuple[float, List[str]]:
    """Score summary quality 0–1.0. Notes explain deductions."""
    notes = []
    score = 1.0

    length = len(summary)
    if length < 15:
        notes.append(f"摘要过短 ({length} 字)")
        score -= 0.3
    elif length > 200:
        notes.append(f"摘要过长 ({length} 字)")
        score -= 0.15

    if re.search(r"[a-zA-Z]", summary) is None:
        notes.append("缺少英文术语")
        score -= 0.2

    hollow = len(re.findall(HOLLOW_WORDS, summary))
    if hollow > 2:
        notes.append(f"摘要空洞词过多 ({hollow})")
        score -= 0.3
    elif hollow > 0:
        notes.append(f"摘要含空洞词 ({hollow})")
        score -= 0.1

    specifics = len(re.findall(SPECIFIC_PATTERNS, summary))
    if specifics < 1:
        notes.append("摘要缺少具体技术指标")
        score -= 0.15

    return max(0, score), notes


def score_tech_depth(highlights: list, summary: str, score_reason: str) -> Tuple[float, List[str]]:
    """Score technical depth 0–1.0 based on highlight quality."""
    notes = []
    score = 1.0

    if not isinstance(highlights, list):
        return 0.2, ["tech_highlights 非数组"]

    n = len(highlights)
    if n < 2:
        notes.append(f"亮点数过少 ({n})")
        score -= 0.4
    elif n > 4:
        notes.append(f"亮点数过多 ({n})")
        score -= 0.1

    vague_count = 0
    spec_count = 0
    for h in highlights:
        if not isinstance(h, str):
            notes.append("亮点包含非字符串值")
            score -= 0.3
            continue
        if len(re.findall(HOLLOW_WORDS, h)) > 0:
            vague_count += 1
        if len(re.findall(SPECIFIC_PATTERNS, h)) > 0:
            spec_count += 1

    if spec_count < 2:
        notes.append("亮点缺乏具体数据/技术术语")
        score -= 0.2

    if vague_count >= n - 1:
        notes.append("亮点空洞，缺乏实质内容")
        score -= 0.4
    elif vague_count > 0:
        score -= 0.15

    # Score reason should explain the number
    reason_len = len(score_reason) if score_reason else 0
    if reason_len < 20:
        notes.append("评分理由过短")
        score -= 0.15

    return max(0, score), notes


def score_format(entry: dict) -> Tuple[float, List[str]]:
    """Score format compliance 0–1.0."""
    notes = []
    score = 1.0

    required = ["id", "title", "source", "source_url", "collected_at", "summary", "tags", "status"]
    missing = [f for f in required if f not in entry]
    if missing:
        notes.append(f"缺少顶层字段: {missing}")
        score -= 0.3 * len(missing)

    valid_statuses = {"draft", "reviewed", "published", "archived"}
    if entry.get("status") not in valid_statuses:
        notes.append(f"status 无效: {entry.get('status')}")
        score -= 0.2

    analysis = entry.get("analysis")
    if isinstance(analysis, dict):
        req = ["tech_highlights", "relevance_score", "reason"]
        for f in req:
            if f not in analysis:
                notes.append(f"analysis 缺少 {f}")
                score -= 0.2

        s = analysis.get("relevance_score")
        if s is not None and (not isinstance(s, (int, float)) or s < 1 or s > 10):
            notes.append(f"score 超范围: {s}")
            score -= 0.2
    else:
        notes.append("缺少 analysis")
        score -= 0.5

    tags = entry.get("tags")
    if isinstance(tags, list):
        if len(tags) < 2:
            notes.append("tags 过少")
            score -= 0.1
        if len(tags) > 8:
            notes.append("tags 过多")
            score -= 0.1

    return max(0, score), notes


def score_tags(tags: list) -> Tuple[float, List[str]]:
    """Score tag precision 0–1.0."""
    notes = []
    score = 1.0

    if not isinstance(tags, list) or len(tags) == 0:
        return 0.0, ["tags 为空"]

    # BAD: overly broad tags
    too_broad = {"ai", "ml", "software", "programming", "code", "python", "javascript", "go", "tool", "tools", "framework", "library", "app", "application", "demo", "example", "tutorial"}
    broad_hits = [t for t in tags if t.lower() in too_broad]
    if broad_hits:
        notes.append(f"标签过宽泛: {broad_hits}")
        score -= 0.15 * len(broad_hits)

    # GOOD: specific compound tags
    has_specific = any("-" in t or len(t) > 12 for t in tags)
    if not has_specific:
        notes.append("缺少复合/精细标签")
        score -= 0.15

    # Check for duplicates / near-duplicates
    lower_tags = [t.lower() for t in tags]
    if len(lower_tags) != len(set(lower_tags)):
        notes.append("标签存在重复")
        score -= 0.3

    return max(0, score), notes


def score_hollow(entry: dict) -> Tuple[float, List[str]]:
    """Detect hollow/filler patterns across all text fields. 0–1.0 (higher = better / cleaner)."""
    notes = []
    score = 1.0

    text_fields = [
        entry.get("summary", ""),
        entry.get("title", ""),
    ]
    analysis = entry.get("analysis", {})
    if isinstance(analysis, dict):
        text_fields.append(analysis.get("reason", ""))
        for h in analysis.get("tech_highlights", []):
            if isinstance(h, str):
                text_fields.append(h)

    combined = " ".join(text_fields)
    hollow_count = len(re.findall(HOLLOW_WORDS, combined))
    total_chars = len(combined) if combined else 1
    density = hollow_count / (total_chars / 100)

    if density > 5:
        notes.append(f"空洞词密度高 ({density:.1f}/100字)")
        score -= 0.6
    elif density > 3:
        notes.append(f"空洞词密度偏高 ({density:.1f}/100字)")
        score -= 0.35
    elif density > 1.5:
        notes.append(f"有少量空洞词 ({hollow_count})")
        score -= 0.15

    return max(0, score), notes


def grade(total: float) -> str:
    if total >= 0.80:
        return "A"
    elif total >= 0.55:
        return "B"
    else:
        return "C"


def evaluate(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        entry = json.load(f)

    results = {}
    all_notes = []

    s, n = score_summary(entry.get("summary", ""))
    results["summary_quality"] = s
    all_notes.extend(n)

    analysis = entry.get("analysis", {})
    s, n = score_tech_depth(
        analysis.get("tech_highlights", []),
        entry.get("summary", ""),
        analysis.get("reason", "")
    )
    results["tech_depth"] = s
    all_notes.extend(n)

    s, n = score_format(entry)
    results["format_compliance"] = s
    all_notes.extend(n)

    s, n = score_tags(entry.get("tags", []))
    results["tag_precision"] = s
    all_notes.extend(n)

    s, n = score_hollow(entry)
    results["hollow_word_penalty"] = s
    all_notes.extend(n)

    total = sum(WEIGHTS[k] * results[k] for k in WEIGHTS)
    return {
        "path": path,
        "title": entry.get("title", "?"),
        "dimensions": {k: round(v, 2) for k, v in results.items()},
        "total": round(total, 3),
        "grade": grade(total),
        "notes": all_notes[:5],  # top 5 only
    }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python3 hooks/check_quality.py knowledge/articles/*.json", file=sys.stderr)
        return 2

    files = [f for f in argv[1:] if os.path.isfile(f)]
    if not files:
        print("未找到 JSON 文件", file=sys.stderr)
        return 1

    reports = [evaluate(p) for p in sorted(files)]

    # Print results
    line_fmt = "{:<6} {:<60} {:>4}  {:>5} {:>5} {:>5} {:>5}  {}"
    print(line_fmt.format("Grade", "Title", "Total", "Summ", "Tech", "Fmt", "Tag", "Hollow"))
    print("-" * 120)

    for r in reports:
        d = r["dimensions"]
        print(line_fmt.format(
            r["grade"],
            r["title"][:58],
            r["total"],
            d["summary_quality"],
            d["tech_depth"],
            d["format_compliance"],
            d["tag_precision"],
            d["hollow_word_penalty"],
            r["notes"][0] if r["notes"] else ""
        ))
        for note in r["notes"][1:]:
            print(f"       {' ' * 86}{note}")

    # Summary
    grades = [r["grade"] for r in reports]
    print()
    print(f"分布: A={grades.count('A')}, B={grades.count('B')}, C={grades.count('C')}")
    avg = sum(r["total"] for r in reports) / len(reports) if reports else 0
    print(f"均分: {avg:.3f}")

    c_count = grades.count("C")
    return 1 if c_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
