"""Tests for the OpenAI-compatible LLM client."""

from __future__ import annotations

import os
import unittest
from typing import Any
from unittest.mock import patch

from pipeline.model_client import Usage, create_provider, estimate_cost


class StubResponse:
    """Minimal successful HTTP response used by the provider tests."""

    def raise_for_status(self) -> None:
        """Match the httpx response contract for a successful request."""

    def json(self) -> dict[str, Any]:
        """Return a DeepSeek V4-compatible chat completion payload."""
        return {
            "model": "deepseek-v4-flash",
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {
                "prompt_tokens": 100,
                "prompt_cache_hit_tokens": 40,
                "prompt_cache_miss_tokens": 60,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        }


class RecordingClient:
    """Record one outgoing request without contacting an external API."""

    def __init__(self) -> None:
        self.url = ""
        self.payload: dict[str, Any] = {}

    def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> StubResponse:
        """Capture the request and return a deterministic response."""
        del headers
        self.url = url
        self.payload = json
        return StubResponse()

    def close(self) -> None:
        """Match the httpx client close contract."""


class DeepSeekV4ConfigurationTest(unittest.TestCase):
    """Verify that fresh DeepSeek configuration uses the current V4 API."""

    def test_default_provider_uses_v4_flash_and_current_base_url(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "test-key"},
            clear=True,
        ):
            provider = create_provider("deepseek")

        try:
            self.assertEqual(provider.model, "deepseek-v4-flash")
            self.assertEqual(provider.base_url, "https://api.deepseek.com")
        finally:
            provider.close()

    def test_default_request_disables_thinking_for_structured_output(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "test-key"},
            clear=True,
        ):
            provider = create_provider("deepseek")

        provider.client.close()
        recording_client = RecordingClient()
        provider.client = recording_client  # type: ignore[assignment]

        try:
            response = provider.chat(
                messages=[{"role": "user", "content": "Return JSON"}],
                max_tokens=64,
            )
        finally:
            provider.close()

        self.assertEqual(
            recording_client.url,
            "https://api.deepseek.com/chat/completions",
        )
        self.assertEqual(
            recording_client.payload["thinking"],
            {"type": "disabled"},
        )
        self.assertEqual(response.usage.prompt_cache_hit_tokens, 40)
        self.assertEqual(response.usage.prompt_cache_miss_tokens, 60)

    def test_request_can_explicitly_enable_thinking(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "test-key"},
            clear=True,
        ):
            provider = create_provider("deepseek")

        provider.client.close()
        recording_client = RecordingClient()
        provider.client = recording_client  # type: ignore[assignment]

        try:
            provider.chat(
                messages=[{"role": "user", "content": "Think carefully"}],
                max_tokens=64,
                thinking=True,
            )
        finally:
            provider.close()

        self.assertEqual(
            recording_client.payload["thinking"],
            {"type": "enabled"},
        )

    def test_retired_model_aliases_fail_with_migration_guidance(self) -> None:
        for retired_model in ("deepseek-chat", "deepseek-reasoner"):
            with (
                self.subTest(model=retired_model),
                patch.dict(
                    os.environ,
                    {
                        "DEEPSEEK_API_KEY": "test-key",
                        "DEEPSEEK_MODEL": retired_model,
                    },
                    clear=True,
                ),
                self.assertRaisesRegex(
                    ValueError,
                    "deepseek-v4-flash.*deepseek-v4-pro",
                ),
            ):
                create_provider("deepseek")


class DeepSeekV4CostTest(unittest.TestCase):
    """Verify cache-aware cost estimates against current V4 USD prices."""

    def test_flash_cost_uses_cache_hit_and_miss_token_rates(self) -> None:
        usage = Usage(
            prompt_tokens=1000,
            prompt_cache_hit_tokens=250,
            prompt_cache_miss_tokens=750,
            completion_tokens=500,
        )

        cost = estimate_cost("deepseek-v4-flash", usage)

        expected = 250 / 1_000_000 * 0.0028
        expected += 750 / 1_000_000 * 0.14
        expected += 500 / 1_000_000 * 0.28
        self.assertAlmostEqual(cost, expected)

    def test_missing_cache_breakdown_is_billed_at_cache_miss_rate(self) -> None:
        usage = Usage(prompt_tokens=1000, completion_tokens=500)

        cost = estimate_cost("deepseek-v4-flash", usage)

        expected = 1000 / 1_000_000 * 0.14
        expected += 500 / 1_000_000 * 0.28
        self.assertAlmostEqual(cost, expected)


if __name__ == "__main__":
    unittest.main()
