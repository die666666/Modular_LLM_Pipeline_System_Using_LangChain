"""
core.py — PipelineEngine
Handles LLM lifecycle: initialization, retry logic, timeout, fallback model.
"""

from __future__ import annotations

import time
import logging
from functools import wraps
from typing import Any, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Retry + Timeout decorator
# ─────────────────────────────────────────────────────────────

def with_retry(max_retries: int = 3, delay: float = 1.5, timeout: float = 60.0):
    """
    Decorator factory that wraps any callable with:
      - Configurable retry count
      - Exponential back-off
      - Per-call timeout guard (raises TimeoutError if exceeded)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_retries + 1):
                start = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    elapsed = time.monotonic() - start
                    if elapsed > timeout:
                        raise TimeoutError(
                            f"Call to '{fn.__name__}' exceeded timeout "
                            f"({elapsed:.1f}s > {timeout}s)"
                        )
                    return result
                except TimeoutError:
                    raise  # don't retry timeouts
                except Exception as exc:
                    last_exc = exc
                    wait = delay * (2 ** (attempt - 1))
                    logger.warning(
                        "Attempt %d/%d failed for '%s': %s — retrying in %.1fs",
                        attempt, max_retries, fn.__name__, exc, wait,
                    )
                    time.sleep(wait)
            raise RuntimeError(
                f"All {max_retries} retries exhausted for '{fn.__name__}'"
            ) from last_exc
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────
# LLM factory
# ─────────────────────────────────────────────────────────────

def build_llm(
    model: str = "llama3.1",
    temperature: float = 0.0,
    num_ctx: int = 4096,
) -> ChatOllama:
    """Instantiate a ChatOllama with the given configuration."""
    return ChatOllama(
        model=model,
        temperature=temperature,
        num_ctx=num_ctx,
    )


# ─────────────────────────────────────────────────────────────
# PipelineEngine
# ─────────────────────────────────────────────────────────────

class PipelineEngine:
    """
    Central orchestrator for the AutoChain pipeline.

    Responsibilities:
      • Owns primary and fallback LLM instances.
      • Exposes a safe `invoke()` that applies retry + fallback.
      • Tracks cumulative token usage across all calls.

    Parameters
    ----------
    primary_model   : Ollama model tag for the main LLM.
    fallback_model  : Ollama model tag used when primary fails all retries.
    temperature     : Sampling temperature (default 0 for determinism).
    max_retries     : Number of retry attempts before switching to fallback.
    timeout         : Per-call wall-clock timeout in seconds.
    """

    def __init__(
        self,
        primary_model: str = "llama3.1",
        fallback_model: str = "llama3.2",
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        self.primary_llm = build_llm(primary_model, temperature)
        self.fallback_llm = build_llm(fallback_model, temperature)

        self._token_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        logger.info(
            "PipelineEngine ready | primary=%s | fallback=%s | temp=%.2f",
            primary_model, fallback_model, temperature,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_llm(self, temperature: Optional[float] = None) -> ChatOllama:
        """Return the primary LLM, optionally with a different temperature."""
        if temperature is not None and temperature != self.temperature:
            return build_llm(self.primary_model, temperature)
        return self.primary_llm

    def invoke(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """
        Invoke *chain* with *inputs*, applying retry logic.
        Falls back to the fallback LLM if the primary exhausts all retries.
        Accumulates token usage metadata when available.
        """
        try:
            result = self._invoke_with_retry(chain, inputs)
        except RuntimeError as primary_err:
            logger.error("Primary chain failed: %s — switching to fallback", primary_err)
            result = self._invoke_fallback(inputs)

        self._record_tokens(result)
        return result

    @property
    def token_usage(self) -> dict[str, int]:
        """Cumulative token usage across all invocations."""
        return dict(self._token_usage)

    def reset_token_usage(self) -> None:
        for k in self._token_usage:
            self._token_usage[k] = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @with_retry(max_retries=3, delay=1.5, timeout=120.0)
    def _invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        return chain.invoke(inputs)

    def _invoke_fallback(self, inputs: dict[str, Any]) -> BaseMessage:
        """Direct fallback: send the raw input text to the fallback LLM."""
        text = " ".join(str(v) for v in inputs.values())
        logger.warning("Fallback LLM (%s) handling request.", self.fallback_model)
        return self.fallback_llm.invoke(text)

    def _record_tokens(self, result: Any) -> None:
        meta = getattr(result, "usage_metadata", None)
        if meta:
            self._token_usage["prompt_tokens"] += meta.get("input_tokens", 0)
            self._token_usage["completion_tokens"] += meta.get("output_tokens", 0)
            self._token_usage["total_tokens"] += meta.get("total_tokens", 0)