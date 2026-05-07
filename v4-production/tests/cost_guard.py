"""CostGuard — multi-agent budget sentinel with triple protection.

Records every LLM call, checks against a yuan-denominated budget,
and raises BudgetExceededError when the alert threshold is crossed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Price USD per 1K tokens (rough estimates, easy to update)
PRICE_TABLE: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.00027, "output": 0.00110},
    "deepseek-v4-flash": {"input": 0.00027, "output": 0.00110},
    "deepseek-v4-pro": {"input": 0.00055, "output": 0.00219},
    "qwen-plus": {"input": 0.00040, "output": 0.00120},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
}
DEFAULT_PRICE = {"input": 0.00100, "output": 0.00300}

# Approximate USD to CNY rate (for display)
USD_TO_CNY = 7.2


# ── Exceptions ────────────────────────────────────────────────────────

class BudgetExceededError(RuntimeError):
    """Raised when the budget check crosses the alert or hard limit."""

    def __init__(self, message: str, report: dict[str, Any]) -> None:
        super().__init__(message)
        self.report = report


# ── Data model ────────────────────────────────────────────────────────

@dataclass
class CostRecord:
    """A single LLM invocation cost snapshot."""

    node_name: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    cost_cny: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )


# ── CostGuard ─────────────────────────────────────────────────────────

class CostGuard:
    """Triple protection: record → check → report.

    Parameters
    ----------
    budget_yuan : float
        Hard budget ceiling in CNY (default 1.0).
    alert_threshold : float
        Fraction of *budget_yuan* at which a BudgetExceededError is
        raised on ``check()`` (default 0.8 → 80 %).
    """

    def __init__(
        self,
        budget_yuan: float = 1.0,
        alert_threshold: float = 0.8,
    ) -> None:
        self.budget_yuan = budget_yuan
        self.alert_threshold = alert_threshold
        self._records: list[CostRecord] = []

    # ── record ──────────────────────────────────────────────────────
    def record(
        self,
        node_name: str,
        usage: dict[str, Any],
        model: str = "",
    ) -> CostRecord:
        """Register a single LLM call.

        Args:
            node_name: Pipeline node that made the call (e.g. ``analyze``).
            usage: Token usage dict with at least ``prompt_tokens``
                and ``completion_tokens``.
            model: Model identifier for price lookup.
        """
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)

        prices = PRICE_TABLE.get(model, DEFAULT_PRICE)
        cost_usd = (prompt / 1000 * prices["input"]) + (
            completion / 1000 * prices["output"]
        )

        record = CostRecord(
            node_name=node_name,
            model=model or "unknown",
            prompt_tokens=prompt,
            completion_tokens=completion,
            cost_usd=round(cost_usd, 8),
            cost_cny=round(cost_usd * USD_TO_CNY, 6),
        )
        self._records.append(record)
        return record

    # ── check ───────────────────────────────────────────────────────
    def check(self) -> dict[str, Any]:
        """Check budget status; raises BudgetExceededError if over
        ``alert_threshold``.

        Returns a status dict with ``total_cny``, ``remaining_cny``,
        ``alert_ratio``, and ``record_count``.
        """
        total_cny = round(sum(r.cost_cny for r in self._records), 6)
        alert_ratio = total_cny / self.budget_yuan if self.budget_yuan > 0 else 0.0

        report = {
            "total_cny": total_cny,
            "budget_cny": self.budget_yuan,
            "remaining_cny": round(self.budget_yuan - total_cny, 6),
            "alert_ratio": round(alert_ratio, 4),
            "record_count": len(self._records),
            "threshold": self.alert_threshold,
        }

        if alert_ratio >= self.alert_threshold:
            raise BudgetExceededError(
                f"Budget alert: {alert_ratio:.1%} of {self.budget_yuan} CNY spent "
                f"({total_cny:.4f} CNY)",
                report,
            )

        return report

    # ── get_report ──────────────────────────────────────────────────
    def get_report(self) -> dict[str, Any]:
        """Generate a cost report grouped by node.

        Returns a dict suitable for JSON serialisation.
        """
        by_node: dict[str, dict[str, Any]] = {}
        total_cny = 0.0
        total_prompt = 0
        total_completion = 0

        for r in self._records:
            total_cny += r.cost_cny
            total_prompt += r.prompt_tokens
            total_completion += r.completion_tokens

            node = by_node.setdefault(r.node_name, {
                "calls": 0,
                "total_cny": 0.0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "models": {},
            })
            node["calls"] += 1
            node["total_cny"] += r.cost_cny
            node["total_prompt_tokens"] += r.prompt_tokens
            node["total_completion_tokens"] += r.completion_tokens
            node["models"][r.model] = node["models"].get(r.model, 0) + 1

        return {
            "summary": {
                "total_calls": len(self._records),
                "total_cny": round(total_cny, 6),
                "budget_cny": self.budget_yuan,
                "budget_remaining": round(self.budget_yuan - total_cny, 6),
                "budget_used_pct": round(
                    total_cny / self.budget_yuan * 100, 2
                ) if self.budget_yuan > 0 else 0.0,
                "total_tokens": total_prompt + total_completion,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
            },
            "by_node": by_node,
            "records": [r.__dict__ for r in self._records],
            "generated_at": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

    def persist_report(self, path: Path | str | None = None) -> Path:
        """Write the report to a JSON file under knowledge/metrics/."""
        report = self.get_report()
        if path is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            out_dir = (
                Path(__file__).resolve().parent.parent
                / "knowledge" / "metrics"
            )
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"cost-{date_str}.json"
        out = Path(path)
        out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return out


# ── Self-test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    guard = CostGuard(budget_yuan=1.0, alert_threshold=0.8)

    # Simulate a few LLM calls
    guard.record("analyze", {"prompt_tokens": 500, "completion_tokens": 200}, "deepseek-chat")
    guard.record("analyze", {"prompt_tokens": 300, "completion_tokens": 150}, "deepseek-chat")
    guard.record("review", {"prompt_tokens": 200, "completion_tokens": 100}, "deepseek-v4-pro")
    guard.record("revise", {"prompt_tokens": 400, "completion_tokens": 250}, "deepseek-chat")

    status = guard.check()
    print("Check:", json.dumps(status, indent=2))

    report = guard.get_report()
    print("\nReport summary:")
    for k, v in report["summary"].items():
        print(f"  {k}: {v}")
    print("\nBy node:")
    for node, info in report["by_node"].items():
        print(f"  {node}: {info['calls']} calls, {info['total_cny']:.6f} CNY")

    # Trigger alert
    big_guard = CostGuard(budget_yuan=0.001, alert_threshold=0.5)
    big_guard.record("analyze", {"prompt_tokens": 100000, "completion_tokens": 50000}, "deepseek-v4-pro")
    try:
        big_guard.check()
        print("\nERROR: should have raised BudgetExceededError")
    except BudgetExceededError as exc:
        print(f"\nBudgetExceededError caught: {exc}")
        print(f"  Ratio: {exc.report['alert_ratio']}")
