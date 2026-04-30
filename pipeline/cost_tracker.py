"""Cost tracking utilities for LLM-powered pipeline runs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pipeline.model_client import Usage, estimate_cost


@dataclass(frozen=True)
class CostEntry:
    """One successful LLM call cost record."""

    source: str
    item_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        """Convert this cost entry to a JSON-serializable dictionary."""
        return {
            "source": self.source,
            "item_name": self.item_name,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 8),
        }


class CostTracker:
    """Collect and summarize LLM cost entries for one pipeline run."""

    def __init__(self) -> None:
        self._entries: list[CostEntry] = []

    @property
    def entries(self) -> list[CostEntry]:
        """Return recorded entries."""
        return list(self._entries)

    def add_call(
        self,
        source: str,
        item_name: str,
        model: str,
        usage: Usage,
    ) -> None:
        """Record one successful LLM call."""
        normalized_model = model or "unknown"
        self._entries.append(
            CostEntry(
                source=source,
                item_name=item_name,
                model=normalized_model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost_usd=estimate_cost(normalized_model, usage),
            )
        )

    def summarize_runs(self) -> list[dict[str, Any]]:
        """Summarize costs by source and model."""
        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        )

        for entry in self._entries:
            row = grouped[(entry.source, entry.model)]
            row["source"] = entry.source
            row["model"] = entry.model
            row["calls"] += 1
            row["prompt_tokens"] += entry.prompt_tokens
            row["completion_tokens"] += entry.completion_tokens
            row["total_tokens"] += entry.total_tokens
            row["estimated_cost_usd"] += entry.estimated_cost_usd

        runs = []
        for row in grouped.values():
            row["estimated_cost_usd"] = round(row["estimated_cost_usd"], 8)
            runs.append(row)

        return sorted(runs, key=lambda item: (item["source"], item["model"]))

    def total(self) -> dict[str, Any]:
        """Return total costs across all recorded calls."""
        prompt_tokens = sum(entry.prompt_tokens for entry in self._entries)
        completion_tokens = sum(entry.completion_tokens for entry in self._entries)
        total_tokens = sum(entry.total_tokens for entry in self._entries)
        estimated_cost = sum(entry.estimated_cost_usd for entry in self._entries)

        return {
            "calls": len(self._entries),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost, 8),
        }

    def to_daily_payload(self, date_str: str, generated_at: str) -> dict[str, Any]:
        """Build the daily cost metrics JSON payload."""
        return {
            "date": date_str,
            "generated_at": generated_at,
            "runs": self.summarize_runs(),
            "total": self.total(),
            "calls": [entry.to_dict() for entry in self._entries],
        }
