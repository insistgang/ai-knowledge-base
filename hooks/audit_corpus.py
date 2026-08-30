"""Audit cross-file article identity without deleting historical records."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.article_store import normalize_source_url  # noqa: E402

logger = logging.getLogger(__name__)
DEFAULT_ARTICLES_DIR = PROJECT_ROOT / "knowledge" / "articles"


def build_corpus_audit(paths: list[Path]) -> dict[str, Any]:
    """Build a corpus-wide ID and source URL audit.

    Args:
        paths: Article JSON paths to inspect.

    Returns:
        JSON-serializable counts and duplicate groups.
    """
    ids: dict[str, list[str]] = defaultdict(list)
    source_urls: dict[str, list[str]] = defaultdict(list)
    invalid_files: list[dict[str, str]] = []
    valid_count = 0
    without_source_url = 0

    for path in sorted(paths):
        try:
            article = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            invalid_files.append({"path": str(path), "error": str(exc)})
            continue

        if not isinstance(article, dict):
            invalid_files.append({
                "path": str(path),
                "error": "root value is not an object",
            })
            continue

        valid_count += 1
        article_id = str(article.get("id", "")).strip()
        if article_id:
            ids[article_id].append(str(path))

        source_url = normalize_source_url(str(article.get("source_url", "")))
        if source_url:
            source_urls[source_url].append(str(path))
        else:
            without_source_url += 1

    duplicate_ids = {
        value: files for value, files in ids.items() if len(files) > 1
    }
    duplicate_urls = {
        value: files for value, files in source_urls.items() if len(files) > 1
    }

    return {
        "total_files": len(paths),
        "valid_files": valid_count,
        "invalid_files": invalid_files,
        "unique_ids": len(ids),
        "unique_source_urls": len(source_urls),
        "duplicate_ids": duplicate_ids,
        "duplicate_source_urls": duplicate_urls,
        "canonical_articles": len(source_urls) + without_source_url,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the corpus-audit CLI parser."""
    parser = argparse.ArgumentParser(description="Audit knowledge article IDs and URLs")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on-duplicate-id", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the corpus audit."""
    args = build_parser().parse_args(argv)
    paths = args.paths or sorted(DEFAULT_ARTICLES_DIR.glob("*.json"))
    audit = build_corpus_audit(paths)

    if args.as_json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(
            "Corpus audit: "
            f"{audit['valid_files']}/{audit['total_files']} valid, "
            f"{audit['unique_ids']} unique IDs, "
            f"{audit['unique_source_urls']} unique URLs, "
            f"{len(audit['duplicate_ids'])} duplicate ID groups, "
            f"{len(audit['duplicate_source_urls'])} duplicate URL groups"
        )
        for article_id, duplicate_paths in audit["duplicate_ids"].items():
            print(f"  duplicate id {article_id}: {len(duplicate_paths)} files")

    if audit["invalid_files"]:
        return 1
    if args.fail_on_duplicate_id and audit["duplicate_ids"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
