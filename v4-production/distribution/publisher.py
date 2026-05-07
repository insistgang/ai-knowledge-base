"""Push knowledge-base digests to distribution channels.

Supported channels:
    telegram   — Telegram Bot API (MarkdownV2)
    (console   — local print, for dry-run / debugging)
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Result model ──────────────────────────────────────────────────────

@dataclass
class PublishResult:
    """Outcome of a single publish attempt."""

    channel: str
    success: bool
    message_id: str = ""
    error: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )


# ── Abstract base ─────────────────────────────────────────────────────

class BasePublisher(ABC):
    """Abstract publisher that each channel subclasses."""

    @abstractmethod
    async def send(self, content: str) -> PublishResult:
        """Deliver *content* to the channel."""


# ── Telegram ──────────────────────────────────────────────────────────

class TelegramPublisher(BasePublisher):
    """Publish via Telegram Bot API using MarkdownV2."""

    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._session = None

    async def _get_session(self):
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession()
        return self._session

    async def send(self, content: str) -> PublishResult:
        """Send MarkdownV2-formatted text to the Telegram bot."""
        if not self.token or not self.chat_id:
            return PublishResult(
                channel="telegram",
                success=False,
                error="TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set",
            )

        try:
            import aiohttp
        except ImportError:
            return PublishResult(
                channel="telegram",
                success=False,
                error="aiohttp not installed. Run: pip install aiohttp",
            )

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": content[:4096],  # Telegram message limit
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            session = await self._get_session()
            async with session.post(url, json=payload, timeout=15.0) as resp:
                data = await resp.json()
                if resp.status >= 400 or not data.get("ok"):
                    return PublishResult(
                        channel="telegram",
                        success=False,
                        error=data.get("description", str(resp.status)),
                    )
                return PublishResult(
                    channel="telegram",
                    success=True,
                    message_id=str(data.get("result", {}).get("message_id", "")),
                )
        except Exception as exc:
            return PublishResult(
                channel="telegram", success=False, error=str(exc)
            )

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None


# ── Console (dry-run) ─────────────────────────────────────────────────

class ConsolePublisher(BasePublisher):
    """Print to stdout — useful for testing and dry-run."""

    async def send(self, content: str) -> PublishResult:
        print(f"\n{'='*60}")
        print(f"[CONSOLE] {len(content)} chars")
        print(f"{'='*60}")
        print(content[:500])
        return PublishResult(channel="console", success=True, message_id="dry-run")


# ── Unified entry point ───────────────────────────────────────────────

def _build_digest_header(date: str, count: int) -> str:
    """Header for the daily digest message (HTML)."""
    return (
        f"<b>📰 AI 知识库日报 — {date}</b>\n"
        f"Top {count} 条高价值动态\n"
    )


async def publish_daily_digest(
    date: str | None = None,
    channels: list[str] | None = None,
    top_n: int = 5,
    knowledge_dir: str | None = None,
    dry_run: bool = False,
) -> list[PublishResult]:
    """Generate and push the daily digest to the specified channels.

    Args:
        date: ISO date ``YYYY-MM-DD``; defaults to today UTC.
        channels: List of channel names, e.g. ``["telegram", "console"]``.
        top_n: Articles to include.
        knowledge_dir: Override knowledge base path.
        dry_run: If True, use ConsolePublisher regardless of *channels*.

    Returns:
        List of PublishResult, one per channel.
    """
    from distribution.formatter import generate_daily_digest, json_to_telegram

    if channels is None:
        channels = ["console"]
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kb_dir = Path(knowledge_dir) if knowledge_dir else (PROJECT_ROOT / "knowledge")

    digest = generate_daily_digest(kb_dir, date, top_n)

    header = _build_digest_header(date, digest["count"])
    items_text = "\n\n".join(
        json_to_telegram(item) for item in digest["items"]
    )
    full_text = header + "\n" + items_text

    # Build publisher map
    publisher_map: dict[str, BasePublisher] = {}
    if dry_run or "console" in channels:
        publisher_map["console"] = ConsolePublisher()
    if "telegram" in channels and not dry_run:
        publisher_map["telegram"] = TelegramPublisher()

    results: list[PublishResult] = []
    for ch in channels:
        pub = publisher_map.get(ch)
        if pub is None:
            results.append(
                PublishResult(channel=ch, success=False, error=f"Unknown channel: {ch}")
            )
            continue
        result = await pub.send(full_text)
        results.append(result)
        if isinstance(pub, TelegramPublisher):
            await pub.close()

    return results
