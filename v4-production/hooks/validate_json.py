"""Validate knowledge article JSON files against the standard schema."""

import json
import sys
import os
import re
from typing import Optional

REQUIRED_FIELDS = [
    "id", "title", "source", "source_url",
    "collected_at", "summary", "tags", "status"
]
VALID_STATUSES = {"draft", "reviewed", "published", "archived"}
REQUIRED_ANALYSIS_FIELDS = ["tech_highlights", "relevance_score", "reason"]
OPTIONAL_ANALYSIS_FIELDS = ["risks"]

FILE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})-([a-z0-9_-]+)-([a-z0-9_-]+)\.json$"
)


def validate_file(path: str) -> list[str]:
    """Validate a single article JSON file. Returns list of error messages."""
    errors: list[str] = []
    basename = os.path.basename(path)

    # --- Check file naming convention ---
    if not FILE_PATTERN.match(basename):
        errors.append(f"文件名不符合规范: {basename}")
    else:
        groups = FILE_PATTERN.match(basename).groups()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", groups[0]):
            errors.append(f"日期格式错误: {groups[0]}")

    # --- Load JSON ---
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"JSON 解析失败: {e}")
        return errors

    if not isinstance(data, dict):
        errors.append("根对象必须是 JSON Object")
        return errors

    # --- Required top-level fields ---
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"缺少必填字段: {field}")

    # --- Validate status ---
    if data.get("status") not in VALID_STATUSES:
        errors.append(
            f"status 无效: {data.get('status')}，可选值: {sorted(VALID_STATUSES)}"
        )

    # --- Validate source_url ---
    url = data.get("source_url", "")
    if url and not url.startswith("http"):
        errors.append(f"source_url 格式无效: {url}")

    # --- Validate tags ---
    tags = data.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            errors.append("tags 必须为字符串数组")
        elif len(tags) == 0:
            errors.append("tags 不能为空")

    # --- Validate audience ---
    audience = data.get("audience")
    if audience is not None:
        if not isinstance(audience, list) or not all(isinstance(a, str) for a in audience):
            errors.append("audience 必须为字符串数组")

    # --- Validate collected_at ---
    collected_at = data.get("collected_at", "")
    if collected_at and not re.search(r"\d{4}-\d{2}-\d{2}", str(collected_at)):
        errors.append(f"collected_at 格式无效: {collected_at}")

    # --- Validate analysis ---
    analysis = data.get("analysis")
    if analysis is None:
        errors.append("缺少 analysis 对象")
    elif isinstance(analysis, dict):
        for field in REQUIRED_ANALYSIS_FIELDS:
            if field not in analysis:
                errors.append(f"analysis 缺少必填字段: {field}")

        score = analysis.get("relevance_score")
        if score is not None and (not isinstance(score, (int, float)) or score < 1 or score > 10):
            errors.append(f"relevance_score 超出范围 (1-10): {score}")

        highlights = analysis.get("tech_highlights")
        if highlights is not None:
            if not isinstance(highlights, list) or len(highlights) == 0:
                errors.append("analysis.tech_highlights 必须为非空数组")

        # Check for unknown analysis fields
        known_fields = set(REQUIRED_ANALYSIS_FIELDS + OPTIONAL_ANALYSIS_FIELDS)
        unknown = set(analysis.keys()) - known_fields
        if unknown:
            errors.append(f"analysis 包含未知字段: {sorted(unknown)}")

    # --- Check for unexpected top-level fields ---
    known_top = {
        "id", "title", "source", "source_url", "collected_at",
        "summary", "analysis", "tags", "audience", "status"
    }
    unknown_top = set(data.keys()) - known_top
    if unknown_top:
        errors.append(f"根对象包含未知字段: {sorted(unknown_top)}")

    # --- Summary length check (warn only) ---
    summary = data.get("summary", "")
    if len(summary) > 200:
        errors.append(f"summary 过长 ({len(summary)} 字符), 建议不超过 100 字")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("用法: python3 hooks/validate_json.py knowledge/articles/*.json", file=sys.stderr)
        return 2

    files = argv[1:]
    total_errors = 0
    total_ok = 0
    total_failed = 0

    for path in sorted(files):
        if not os.path.isfile(path):
            print(f"[SKIP] {path} (not a file)")
            continue

        errors = validate_file(path)
        if errors:
            total_failed += 1
            total_errors += len(errors)
            print(f"[FAIL] {path}")
            for e in errors:
                print(f"       {e}")
        else:
            total_ok += 1
            print(f"[ OK ] {path}")

    print()
    print(f"结果: {total_ok} OK, {total_failed} FAIL, {total_errors} errors")
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
