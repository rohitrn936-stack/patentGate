"""Turn Agent 1's structured output into focused patent-search queries.

We search on the *extracted technical features* (feature names, components,
mechanisms, interfaces, technical concepts) rather than the raw product
description, so the queries stay concept-dense instead of marketing-heavy.
"""

from __future__ import annotations

import re

_STOP_WORDS = frozenset(
    """a an and or the to of in on for with without using via be is are as at by from into
    that this these those it its their his her our your my we you they i system device
    apparatus method product widget thing smart new improved based able allow allows provide
    provides feature features function functions user users data using use used than then
    which what when where while also may can could would should will shall each any some
    one two three more most much very core main key overall general various multiple""".split()
)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-]*")


def _tokens(text: str) -> list[str]:
    return [
        t
        for t in _TOKEN_RE.findall((text or "").lower())
        if len(t) > 2 and t not in _STOP_WORDS
    ]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(value.strip())
    return out


def _phrases(agent1: dict) -> list[str]:
    """Ordered, most-specific-first list of concept phrases."""

    phrases: list[str] = []

    for feature in agent1.get("features", []) or []:
        name = (feature.get("name") or "").strip()
        if name:
            phrases.append(name)
        func = (feature.get("function") or "").strip()
        if func and len(func.split()) <= 6:
            phrases.append(func)

    for key in ("mechanisms", "technical_concepts", "components", "interfaces"):
        for item in agent1.get(key, []) or []:
            name = (item.get("name") or "").strip()
            if name:
                phrases.append(name)

    analysis = agent1.get("analysis", {}) or {}
    for concept in analysis.get("similar_known_concepts", []) or []:
        name = (concept.get("name") or "").strip()
        if name:
            phrases.append(name)
    phrases.extend(analysis.get("potentially_overlapping_areas", []) or [])

    return _unique(phrases)


def feature_tokens(agent1: dict) -> list[str]:
    """Flat token vocabulary used for relevance scoring."""

    text_parts: list[str] = []
    for phrase in _phrases(agent1):
        text_parts.append(phrase)
    product = agent1.get("product", {}) or {}
    text_parts.append(product.get("summary", ""))
    return _unique(_tokens(" ".join(text_parts)))


def build_queries(agent1: dict, *, limit: int = 5) -> list[str]:
    """Three to five multi-term queries built from the extracted features."""

    phrases = _phrases(agent1)
    queries: list[str] = []

    # 1. Pairs of the most specific concept phrases keep queries tight.
    for i in range(0, min(len(phrases), limit * 2), 2):
        pair = phrases[i : i + 2]
        query = " ".join(pair).strip()
        if len(_tokens(query)) >= 2:
            queries.append(query)

    # 2. A broad token query as a safety net.
    tokens = feature_tokens(agent1)
    if tokens:
        queries.append(" ".join(tokens[:6]))

    # 3. Fall back to the product summary if we somehow have nothing.
    if not queries:
        product = agent1.get("product", {}) or {}
        summary_tokens = _tokens(product.get("summary", ""))
        if summary_tokens:
            queries.append(" ".join(summary_tokens[:6]))

    return _unique(queries)[:limit]


__all__ = ["build_queries", "feature_tokens"]
