"""Tests for LLM model routing."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pipeline.model_client import create_provider
from pipeline.pipeline import read_model_routes, select_analysis_model


class ModelRoutingTest(unittest.TestCase):
    """Verify normal and deep analysis model routing."""

    def test_default_model_routes_use_deepseek_v4_models(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            routes = read_model_routes()

        self.assertEqual(routes["normal"], "deepseek-v4-flash")
        self.assertEqual(routes["deep"], "deepseek-v4-pro")
        self.assertEqual(select_analysis_model("normal", routes), "deepseek-v4-flash")
        self.assertEqual(select_analysis_model("deep", routes), "deepseek-v4-pro")

    def test_model_routes_can_be_overridden_by_env(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_KB_ANALYSIS_MODEL": "cheap-model",
                "AI_KB_DEEP_ANALYSIS_MODEL": "strong-model",
            },
            clear=True,
        ):
            routes = read_model_routes()

        self.assertEqual(routes["normal"], "cheap-model")
        self.assertEqual(routes["deep"], "strong-model")

    def test_create_provider_accepts_model_override(self) -> None:
        with patch.dict(
            os.environ,
            {"DEEPSEEK_API_KEY": "test-key", "DEEPSEEK_MODEL": "deepseek-chat"},
            clear=True,
        ):
            provider = create_provider("deepseek", model_override="deepseek-v4-flash")

        try:
            self.assertEqual(provider.model, "deepseek-v4-flash")
        finally:
            provider.close()


if __name__ == "__main__":
    unittest.main()
