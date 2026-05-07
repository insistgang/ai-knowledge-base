"""Unified LLM client for OpenAI-compatible providers.

The pipeline layer calls this module directly. OpenCode is only used to write
and maintain the code; it is not part of the runtime path.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class Usage:
    """Token usage returned by a chat completion call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Return total token count."""
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict[str, int]:
        """Convert usage to a serializable dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """Provider-independent response returned by the model client."""

    content: str
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert response to a serializable dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict(),
        }


# Prices are USD per 1K tokens. They are rough estimates for local cost tracking
# and are intentionally easy to update as provider pricing changes.
PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.00027, "output": 0.00110},
    "deepseek-reasoner": {"input": 0.00055, "output": 0.00219},
    "deepseek-v4-flash": {"input": 0.00027, "output": 0.00110},
    "deepseek-v4-pro": {"input": 0.00055, "output": 0.00219},
    "qwen-plus": {"input": 0.00040, "output": 0.00120},
    "qwen-turbo": {"input": 0.00005, "output": 0.00020},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.00060},
    "gpt-4o": {"input": 0.00500, "output": 0.01500},
}


def estimate_cost(model: str, usage: Usage) -> float:
    """Estimate one call cost in USD.

    Args:
        model: Model name returned by or sent to the provider.
        usage: Token usage for the call.

    Returns:
        Estimated cost in USD.
    """
    prices = PRICING.get(model, {"input": 0.00100, "output": 0.00300})
    return (
        usage.prompt_tokens / 1000 * prices["input"]
        + usage.completion_tokens / 1000 * prices["output"]
    )


class LLMProvider(ABC):
    """Abstract base class for chat providers."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.Client(timeout=60.0)

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Send a chat completion request."""

    def close(self) -> None:
        """Close underlying HTTP resources."""
        self.client.close()


class OpenAICompatibleProvider(LLMProvider):
    """Provider implementation for OpenAI-compatible chat APIs."""

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Call `/chat/completions` and normalize the provider response."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        message = data["choices"][0]["message"]
        content = message.get("content") or ""
        reasoning_content = message.get("reasoning_content") or ""
        # Reasoning models may spend all max_tokens on reasoning
        # and leave content empty; surface reasoning as content in that case.
        if not content and reasoning_content:
            content = reasoning_content
            reasoning_content = ""
        usage_data = data.get("usage", {})
        usage = Usage(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0) or 0),
            completion_tokens=int(usage_data.get("completion_tokens", 0) or 0),
        )
        return LLMResponse(
            content=content,
            usage=usage,
            model=data.get("model", self.model),
        )


PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
        "default_base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url_env": "QWEN_BASE_URL",
        "model_env": "QWEN_MODEL",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url_env": "OPENAI_BASE_URL",
        "model_env": "OPENAI_MODEL",
        "default_base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
}


def create_provider(
    provider_name: str | None = None,
    model_override: str | None = None,
) -> LLMProvider:
    """Create an LLM provider from environment variables.

    Args:
        provider_name: Provider id: `deepseek`, `qwen`, or `openai`.
            Defaults to `LLM_PROVIDER`, then `deepseek`.
        model_override: Optional model name for this provider instance.

    Returns:
        Configured provider instance.

    Raises:
        ValueError: If the provider is unknown.
        RuntimeError: If the provider API key is missing.
    """
    name = (provider_name or os.getenv("LLM_PROVIDER", "deepseek")).lower()
    if name not in PROVIDER_CONFIG:
        known = ", ".join(sorted(PROVIDER_CONFIG))
        raise ValueError(f"Unknown LLM provider: {name}. Known: {known}")

    config = PROVIDER_CONFIG[name]
    api_key = os.getenv(config["api_key_env"], "")
    if not api_key:
        raise RuntimeError(f"Missing API key env var: {config['api_key_env']}")

    base_url = os.getenv(config["base_url_env"], config["default_base_url"])
    model = model_override or os.getenv(config["model_env"], config["default_model"])

    logger.info("Creating LLM provider: provider=%s model=%s", name, model)
    return OpenAICompatibleProvider(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def chat_with_retry(
    provider: LLMProvider,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries: int = 3,
    backoff_base: float = 2.0,
) -> LLMResponse:
    """Call chat with retry and exponential backoff.

    Args:
        provider: Configured provider instance.
        messages: OpenAI-style chat messages.
        temperature: Sampling temperature.
        max_tokens: Maximum generated tokens.
        max_retries: Maximum attempts, including the first call.
        backoff_base: Exponential backoff base in seconds.

    Returns:
        Normalized LLM response.
    """
    last_error: Exception | None = None
    retryable = (
        httpx.HTTPStatusError,
        httpx.ConnectError,
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        httpx.RemoteProtocolError,
    )

    for attempt in range(1, max_retries + 1):
        try:
            return provider.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except retryable as exc:
            last_error = exc
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
                if status not in {408, 409, 429, 500, 502, 503, 504}:
                    raise

            if attempt == max_retries:
                break

            wait_time = backoff_base ** (attempt - 1)
            logger.warning(
                "LLM call failed on attempt %s/%s; retrying in %.1fs: %s",
                attempt,
                max_retries,
                wait_time,
                exc,
            )
            time.sleep(wait_time)

    if last_error is None:
        raise RuntimeError("LLM call failed without an exception")
    raise last_error


def quick_chat(
    prompt: str,
    system: str = "你是一个 AI 技术分析助手。",
    provider_name: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
) -> str:
    """Call the configured model with one prompt and return text only."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    provider = create_provider(provider_name, model_override=model)
    try:
        response = chat_with_retry(
            provider,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cost = estimate_cost(response.model or provider.model, response.usage)
        logger.info(
            "Token usage: prompt=%s completion=%s total=%s estimated_cost=$%.6f",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            response.usage.total_tokens,
            cost,
        )
        return response.content
    finally:
        provider.close()


def chat(
    prompt: str,
    system: str = "你是一个 AI 技术分析助手。",
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 512,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Convenience function returning content and usage as a dictionary."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    llm = create_provider(provider, model_override=model)
    try:
        response = chat_with_retry(
            llm,
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            max_retries=max_retries,
        )
        result = response.to_dict()
        result["estimated_cost_usd"] = estimate_cost(
            response.model or llm.model,
            response.usage,
        )
        return result
    finally:
        llm.close()


def main() -> int:
    """Run a minimal connectivity test for the configured provider."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    provider = os.getenv("LLM_PROVIDER", "deepseek")
    logger.info("Running model client test with provider=%s", provider)

    try:
        result = chat(
            "用一句话解释什么是 AI Agent。",
            max_tokens=128,
        )
    except Exception:
        logger.exception("Model client test failed")
        return 1

    logger.info("Response: %s", result["content"])
    logger.info("Usage: %s", result["usage"])
    logger.info("Estimated cost: $%.6f", result["estimated_cost_usd"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
