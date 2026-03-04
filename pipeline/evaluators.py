"""
evaluators.py -- PipelineEvaluator
Evaluation harness that:
  * Runs chains across temperature variants (0 vs 0.7)
  * Runs chains across prompt variants (default vs alt)
  * Logs token usage per run
  * Produces a structured metrics table (list of dicts, printable as DataFrame)
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from langchain_ollama import ChatOllama
from pipeline.core import build_llm

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class EvalResult:
    run_id: str
    chain_name: str
    temperature: float
    prompt_variant: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_seconds: float
    output_preview: str
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "chain": self.chain_name,
            "temp": self.temperature,
            "prompt": self.prompt_variant,
            "in_tokens": self.input_tokens,
            "out_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_s": round(self.latency_seconds, 2),
            "output_preview": self.output_preview[:120],
            "error": self.error or "",
        }


@dataclass
class EvalSuite:
    name: str
    chain_factory: Callable[[ChatOllama, bool], Any]
    invoke_fn: Callable[[Any, str], Any]
    sample_input: str
    temperatures: list[float] = field(default_factory=lambda: [0.0, 0.7])
    prompt_variants: list[str] = field(default_factory=lambda: ["default", "alt"])


# ──────────────────────────────────────────────────────────────────────
# PipelineEvaluator
# ──────────────────────────────────────────────────────────────────────

class PipelineEvaluator:
    """
    Runs evaluation suites and aggregates results into a metrics table.

    Usage:
        evaluator = PipelineEvaluator(model="llama3.1")
        evaluator.register(suite)
        results = evaluator.run_all()
        evaluator.print_table(results)
    """

    def __init__(self, model: str = "llama3.1"):
        self.model = model
        self._suites: list[EvalSuite] = []

    def register(self, suite: EvalSuite) -> None:
        self._suites.append(suite)

    def run_all(self) -> list[EvalResult]:
        results: list[EvalResult] = []
        for suite in self._suites:
            for temp in suite.temperatures:
                for variant in suite.prompt_variants:
                    result = self._run_one(suite, temp, variant)
                    results.append(result)
                    logger.info(
                        "[%s] temp=%.1f variant=%-7s | tokens=%d | %.2fs | err=%s",
                        suite.name, temp, variant,
                        result.total_tokens, result.latency_seconds,
                        result.error or "none",
                    )
        return results

    def _run_one(self, suite: EvalSuite, temp: float, variant: str) -> EvalResult:
        use_alt = variant == "alt"
        llm = build_llm(self.model, temperature=temp)
        chain = suite.chain_factory(llm, use_alt)

        run_id = f"{suite.name}|t={temp}|{variant}"
        start = time.monotonic()
        error = None
        output_preview = ""
        in_tok = out_tok = total_tok = 0

        try:
            result = suite.invoke_fn(chain, suite.sample_input)
            # get string preview
            if hasattr(result, "raw_summary"):
                output_preview = result.raw_summary
            elif hasattr(result, "final_answer"):
                output_preview = result.final_answer
            elif hasattr(result, "outlook"):
                output_preview = str(result)
            else:
                output_preview = str(result)
        except Exception as exc:
            error = str(exc)
            logger.error("Eval run '%s' failed: %s", run_id, exc)

        latency = time.monotonic() - start

        return EvalResult(
            run_id=run_id,
            chain_name=suite.name,
            temperature=temp,
            prompt_variant=variant,
            input_tokens=in_tok,
            output_tokens=out_tok,
            total_tokens=total_tok,
            latency_seconds=latency,
            output_preview=output_preview,
            error=error,
        )

    @staticmethod
    def print_table(results: list[EvalResult]) -> None:
        """Pretty-print metrics table to stdout."""
        rows = [r.to_dict() for r in results]
        if not rows:
            print("No results.")
            return

        cols = list(rows[0].keys())
        widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}

        header = " | ".join(c.ljust(widths[c]) for c in cols)
        sep = "-+-".join("-" * widths[c] for c in cols)
        print("\n" + header)
        print(sep)
        for row in rows:
            print(" | ".join(str(row[c]).ljust(widths[c]) for c in cols))
        print()

        # Summary stats
        if results:
            avg_latency = sum(r.latency_seconds for r in results) / len(results)
            total_tokens = sum(r.total_tokens for r in results)
            errors = sum(1 for r in results if r.error)
            print(f"  Runs: {len(results)}  |  Avg latency: {avg_latency:.2f}s  "
                  f"|  Total tokens: {total_tokens}  |  Errors: {errors}")