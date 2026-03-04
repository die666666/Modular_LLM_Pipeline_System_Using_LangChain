"""
chains.py -- Domain Chains
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel
from langchain_ollama import ChatOllama

from pipeline.prompts import PromptLibrary

logger = logging.getLogger(__name__)


# ── Pydantic Schemas ──────────────────────────────────────────────────

class FinancialReport(BaseModel):
    company: Optional[str] = Field(None)
    revenue: Optional[str] = Field(None)
    net_income: Optional[str] = Field(None)
    ebitda: Optional[str] = Field(None)
    key_metrics: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    outlook: Optional[str] = Field(None)

class SummaryOutput(BaseModel):
    key_points: list[str] = Field(default_factory=list)
    critical_findings: str = ""
    recommended_actions: list[str] = Field(default_factory=list)
    raw_summary: str = ""

class ReasoningOutput(BaseModel):
    problem: str
    steps: str
    final_answer: str
    critique: str
    confidence: str = "Medium"


# ── Helpers ───────────────────────────────────────────────────────────

def _chunk_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.8:
        truncated = truncated[:last_period + 1]
    logger.warning("Document truncated from %d to %d chars.", len(text), len(truncated))
    return truncated


def _safe_parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(l for l in lines if not l.strip().startswith("```"))
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM output:\n{text[:300]}")
    return json.loads(text[start:end])


def _extract_from_plain_text(text: str) -> FinancialReport:
    """
    Fallback extractor: pull financial fields from plain prose / bullet output.
    Used when small models ignore JSON instructions.
    """
    def find(patterns):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip().rstrip(".,")
        return None

    def find_list(patterns):
        items = []
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                val = m.group(1).strip().rstrip(".,")
                if val and val not in items:
                    items.append(val)
        return items[:6]

    company = find([
        r"([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*),?\s+Inc\.",
        r"([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*),?\s+Corp\.",
        r"([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*),?\s+Ltd\.",
        r"(?:company|firm)[:\s]+([A-Z][A-Za-z0-9\s]+?)(?:\n|,|\.)",
    ])

    revenue = find([
        r"(?:total\s+)?revenue[s]?\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
        r"(?:net\s+)?sales\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
    ])

    net_income = find([
        r"net\s+income\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
        r"net\s+(?:profit|loss)\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
    ])

    ebitda = find([
        r"ebitda\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
        r"operating\s+income\s*(?:of|was|were|:)?\s*\$?([\d\.,]+\s*(?:billion|million|B|M)?)",
    ])

    bullets = re.findall(r"[*\-•]\s+(.+)", text)
    key_metrics = [b.strip() for b in bullets if len(b.strip()) > 10][:5]

    risks = find_list([
        r"risk[s]?[:\s]+([^\n\.\*]{10,80})",
        r"challenge[s]?[:\s]+([^\n\.\*]{10,80})",
        r"headwind[s]?[:\s]+([^\n\.\*]{10,80})",
    ])

    outlook = find([
        r"(?:outlook|guidance|forecast)[:\s]+([^\n\.]{10,150})",
        r"(?:expect[s]?|project[s]?|anticipate[s]?)[:\s]+([^\n\.]{10,150})",
    ])

    if not outlook:
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 20]
        if sentences:
            outlook = sentences[-1][:200]

    return FinancialReport(
        company=company,
        revenue=revenue,
        net_income=net_income,
        ebitda=ebitda,
        key_metrics=key_metrics,
        risks=risks,
        outlook=outlook,
    )


# ── FinancialChain ────────────────────────────────────────────────────

class FinancialChain:
    """
    Extracts structured financial data from free-form text.
    1. Prompt -> LLM -> try JSON parse
    2. If JSON fails -> plain-text regex fallback
    3. If still empty -> retry regex on raw source document
    """

    def __init__(self, llm: ChatOllama, use_alt_prompt: bool = False):
        prompt = (
            PromptLibrary.financial_extraction_alt()
            if use_alt_prompt
            else PromptLibrary.financial_extraction_default()
        )
        self._chain = prompt | llm | StrOutputParser()

    def run(self, text: str, max_chars: int = 6000) -> FinancialReport:
        chunk = _chunk_text(text, max_chars)
        raw = self._chain.invoke({"text": chunk})
        logger.debug("FinancialChain raw output:\n%s", raw[:500])

        # Try JSON first
        try:
            data = _safe_parse_json(raw)
            return FinancialReport(**data)
        except (ValueError, ValidationError, json.JSONDecodeError):
            pass

        # Fallback 1: regex on LLM response
        logger.warning("JSON parse failed -- using plain-text extractor on LLM response.")
        report = _extract_from_plain_text(raw)

        # Fallback 2: regex on source document if still empty
        if not any([report.company, report.revenue, report.net_income, report.outlook]):
            logger.warning("Retrying plain-text extractor on source document.")
            report = _extract_from_plain_text(chunk)

        return report

    def as_runnable(self):
        return self._chain


# ── SummarizationChain ────────────────────────────────────────────────

class SummarizationChain:

    def __init__(self, llm: ChatOllama, use_alt_prompt: bool = False):
        self._llm = llm
        prompt = (
            PromptLibrary.summarization_alt()
            if use_alt_prompt
            else PromptLibrary.summarization_default()
        )
        self._chain = prompt | llm | StrOutputParser()

    def run(self, document: str, max_chars: int = 6000) -> SummaryOutput:
        chunk = _chunk_text(document, max_chars)
        raw = self._chain.invoke({"document": chunk})
        return SummaryOutput(raw_summary=raw, critical_findings=raw)

    def run_parallel(self, documents: dict[str, str], max_chars: int = 6000) -> dict[str, SummaryOutput]:
        runnable_map = {
            name: (PromptLibrary.summarization_default() | self._llm | StrOutputParser())
            for name in documents
        }
        parallel = RunnableParallel(runnable_map)
        results = parallel.invoke(
            {name: {"document": _chunk_text(text, max_chars)} for name, text in documents.items()}
        )
        return {
            name: SummaryOutput(raw_summary=raw, critical_findings=raw)
            for name, raw in results.items()
        }


# ── ReasoningChain ────────────────────────────────────────────────────

class ReasoningChain:

    def __init__(self, llm: ChatOllama):
        self._llm = llm
        self._str = StrOutputParser()
        self._decompose = PromptLibrary.reasoning_decompose() | llm | self._str
        self._synthesize = PromptLibrary.reasoning_synthesize() | llm | self._str
        self._critique = PromptLibrary.reasoning_critique() | llm | self._str

    def run(self, problem: str) -> ReasoningOutput:
        steps = self._decompose.invoke({"problem": problem})
        final = self._synthesize.invoke({"steps": steps})
        critique = self._critique.invoke({"reasoning": steps + "\n\n" + final})

        confidence = "Medium"
        for level in ("High", "Medium", "Low"):
            if level.lower() in final.lower():
                confidence = level
                break

        return ReasoningOutput(
            problem=problem,
            steps=steps,
            final_answer=final,
            critique=critique,
            confidence=confidence,
        )