"""Canonical article selection for read-facing knowledge-base views.

Historical JSON files remain immutable audit records.  MCP and Dashboard use
the helpers in this module to collapse repeated source URLs without deleting
the underlying files.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def normalize_source_url(url: str) -> str:
    """Normalize a source URL for stable duplicate comparisons.

    Args:
        url: Source URL from an article or collector candidate.

    Returns:
        Canonical URL without query, fragment, or a trailing slash.
    """
    raw_url = str(url or "").strip()
    if not raw_url:
        return ""
    if "://" not in raw_url:
        raw_url = f"https://{raw_url.lstrip('/')}"

    try:
        parts = urlsplit(raw_url)
        hostname = (parts.hostname or "").lower()
        parsed_port = parts.port
    except ValueError:
        return ""

    scheme = parts.scheme.lower() or "https"
    if not hostname:
        return ""

    port = f":{parsed_port}" if parsed_port is not None else ""
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/")
    if hostname == "github.com":
        scheme = "https"
        path = path.lower()

    return urlunsplit((scheme, f"{hostname}{port}", path, "", ""))


def _canonical_key(article: dict[str, Any], index: int) -> str:
    """Return the identity used to collapse one article."""
    source_url = normalize_source_url(str(article.get("source_url", "")))
    if source_url:
        return f"url:{source_url}"

    article_id = str(article.get("id", "")).strip()
    if article_id:
        return f"id:{article_id}"

    return f"anonymous:{index}"


def _freshness_key(article: dict[str, Any], index: int) -> tuple[str, str, int]:
    """Return a deterministic newest-first comparison key."""
    return (
        str(article.get("collected_at", "")),
        str(article.get("id", "")),
        index,
    )


def select_canonical_articles(
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select the newest record for every normalized source URL.

    Args:
        articles: Parsed article objects. They are not mutated.

    Returns:
        A newest-first list containing one canonical record per source URL.
    """
    selected: dict[str, tuple[tuple[str, str, int], dict[str, Any]]] = {}

    for index, article in enumerate(articles):
        identity = _canonical_key(article, index)
        freshness = _freshness_key(article, index)
        current = selected.get(identity)
        if current is None or freshness > current[0]:
            selected[identity] = (freshness, article)

    ordered = sorted(selected.values(), key=lambda item: item[0], reverse=True)
    return [article for _, article in ordered]
