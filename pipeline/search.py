"""
search.py -- DuckDuckGo Web Search
No API key needed. Detects when a query needs live info
and fetches results to inject into the LLM context.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Keywords that signal the user wants current/live info
LIVE_TRIGGERS = [
    "current", "today", "now", "latest", "recent", "right now",
    "this week", "this month", "this year", "2024", "2025", "2026",
    "price", "stock", "news", "weather", "score", "result",
    "who won", "what happened", "update", "live", "breaking",
    "how much is", "what is the", "tell me about",
]


def needs_search(query: str) -> bool:
    """Detect if a query likely needs live web data."""
    q = query.lower()
    return any(trigger in q for trigger in LIVE_TRIGGERS)


def search(query: str, max_results: int = 4) -> list[dict]:
    """
    Search DuckDuckGo and return clean results.
    Returns list of {"title": ..., "snippet": ..., "url": ...}
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        cleaned = []
        for r in results:
            cleaned.append({
                "title":   r.get("title", "").strip(),
                "snippet": r.get("body",  "").strip(),
                "url":     r.get("href",  "").strip(),
            })
        logger.info("DuckDuckGo search for '%s' returned %d results.", query, len(cleaned))
        return cleaned
    except ImportError:
        logger.error("duckduckgo_search not installed. Run: pip install duckduckgo-search")
        return []
    except Exception as e:
        logger.warning("Search failed: %s", e)
        return []


def format_results_for_llm(query: str, results: list[dict]) -> str:
    """
    Format search results into a context block to prepend to the LLM prompt.
    """
    if not results:
        return ""
    lines = [
        f"[Web search results for: '{query}']",
        "Use the following information to answer the user's question accurately.\n",
    ]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['title']}")
        lines.append(f"   {r['snippet']}")
        lines.append(f"   Source: {r['url']}\n")
    lines.append("[End of search results]\n")
    return "\n".join(lines)


def search_and_format(query: str, max_results: int = 4) -> str:
    """Convenience: search + format in one call."""
    results = search(query, max_results)
    return format_results_for_llm(query, results)