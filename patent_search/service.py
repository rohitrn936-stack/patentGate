"""The patent search layer entry point.

``PatentSearchService.search(agent1_output)`` builds queries from Agent 1's
extracted features, runs the configured sources in priority order, then
de-duplicates, scores and trims to the top five results. It never raises: a
fully offline run still returns five concept-derived stubs so the pipeline can
continue.

Configuration (all optional, read from the environment):
    PATENTSVIEW_API_KEY       enable the PatentsView Search API source
    TAVILY_API_KEY            enable the Tavily web-search source
    PATENT_SEARCH_ENABLED     set to "false" to skip every network source
    PATENT_SEARCH_ALLOW_SCRAPE  set to "false" to skip the Google Patents source
    PATENT_SEARCH_TIMEOUT     per-request timeout in seconds (default 12)
"""

from __future__ import annotations

import os
import re

from .query import build_queries, feature_tokens
from .schemas import PatentHit, PatentSearchResult
from .sources import search_google_patents, search_patentsview, search_tavily

_TRUE = {"1", "true", "yes", "on"}
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+\-]*")


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


class PatentSearchService:
    def __init__(self, *, client=None, config: dict | None = None) -> None:
        cfg = config or {}
        self._client = client
        self.patentsview_key = cfg.get("patentsview_api_key", os.getenv("PATENTSVIEW_API_KEY", ""))
        self.tavily_key = cfg.get("tavily_api_key", os.getenv("TAVILY_API_KEY", ""))
        # An explicitly injected client means the caller wants search to run
        # (used by tests with a fake transport); otherwise honour the env flag.
        self.enabled = cfg.get("enabled", client is not None or _flag("PATENT_SEARCH_ENABLED", True))
        self.allow_scrape = cfg.get("allow_scrape", _flag("PATENT_SEARCH_ALLOW_SCRAPE", True))
        self.timeout = float(cfg.get("timeout", os.getenv("PATENT_SEARCH_TIMEOUT", "12")))
        self.top_n = int(cfg.get("top_n", 5))

    # -- client -----------------------------------------------------------
    def _get_client(self):
        if self._client is not None:
            return self._client, False
        import httpx

        return httpx.Client(timeout=self.timeout, follow_redirects=True), True

    # -- public API -----------------------------------------------------
    def search(self, agent1_output: dict) -> PatentSearchResult:
        queries = build_queries(agent1_output)
        warnings: list[str] = []
        sources_used: list[str] = []
        raw: list[PatentHit] = []

        if self.enabled and queries:
            client, owns = self._get_client()
            try:
                if self.patentsview_key:
                    got = search_patentsview(
                        queries, api_key=self.patentsview_key, client=client, warnings=warnings
                    )
                    if got:
                        sources_used.append("patentsview")
                        raw.extend(got)
                if len(raw) < self.top_n and self.allow_scrape:
                    got = search_google_patents(queries, client=client, warnings=warnings)
                    if got:
                        sources_used.append("google_patents")
                        raw.extend(got)
                if len(raw) < self.top_n and self.tavily_key:
                    got = search_tavily(
                        queries, api_key=self.tavily_key, client=client, warnings=warnings
                    )
                    if got:
                        sources_used.append("tavily")
                        raw.extend(got)
            finally:
                if owns:
                    client.close()
        elif not self.enabled:
            warnings.append("Network patent search disabled; using concept-derived results.")

        deduped = _dedupe(raw)
        ranked = _rank(deduped, agent1_output)
        top = ranked[: self.top_n]

        if len(top) < self.top_n:
            stubs = _derived_stubs(agent1_output, want=self.top_n - len(top))
            if stubs:
                sources_used.append("derived")
            top.extend(stubs)

        return PatentSearchResult(
            queries=queries,
            patents=top[: self.top_n],
            sources_used=_unique(sources_used),
            warnings=warnings,
        )


# --------------------------------------------------------------------------- #
# ranking + de-duplication
# --------------------------------------------------------------------------- #
def _norm_number(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _norm_title(value: str) -> str:
    return " ".join(_TOKEN_RE.findall((value or "").lower()))


def _dedupe(hits: list[PatentHit]) -> list[PatentHit]:
    seen: set[str] = set()
    out: list[PatentHit] = []
    for hit in hits:
        keys = {k for k in (_norm_number(hit.patent_number), _norm_title(hit.title)) if k}
        if keys & seen:
            # Merge a longer abstract into the kept copy when we can find it.
            for kept in out:
                if _norm_number(kept.patent_number) in keys or _norm_title(kept.title) in keys:
                    if len(hit.abstract) > len(kept.abstract):
                        kept.abstract = hit.abstract
                    if not kept.claims and hit.claims:
                        kept.claims = hit.claims
                    break
            continue
        seen |= keys
        out.append(hit)
    return out


def _rank(hits: list[PatentHit], agent1: dict) -> list[PatentHit]:
    tokens = set(feature_tokens(agent1))
    feature_names = [
        (f.get("id") or "", f.get("name") or "")
        for f in agent1.get("features", []) or []
    ]
    ranked: list[PatentHit] = []
    for hit in hits:
        haystack = f"{hit.title} {hit.abstract}".lower()
        hay_tokens = set(_TOKEN_RE.findall(haystack))
        overlap = tokens & hay_tokens
        matching: list[str] = []
        for fid, fname in feature_names:
            fname_tokens = set(_TOKEN_RE.findall(fname.lower()))
            if fname_tokens and len(fname_tokens & hay_tokens) >= min(2, len(fname_tokens)):
                matching.append(fname or fid)
        score = float(len(overlap) * 2 + len(matching) * 3)
        if len(overlap) > 1:
            score += len(overlap) - 1  # reward concept combinations
        title_hits = len(tokens & set(_TOKEN_RE.findall(hit.title.lower())))
        score += title_hits * 1.5
        if hit.source == "patentsview":
            score += 1.0  # structured, authoritative
        hit.relevance_score = round(score, 2)
        hit.matching_features = matching or _fallback_matches(feature_names)
        ranked.append(hit)
    ranked.sort(key=lambda h: (-h.relevance_score, h.patent_number))
    return ranked


def _fallback_matches(feature_names: list[tuple[str, str]]) -> list[str]:
    return [name or fid for fid, name in feature_names[:2]]


# --------------------------------------------------------------------------- #
# offline fallback - Agent 1's "similar known concepts" as prior-art stubs
# --------------------------------------------------------------------------- #
def _derived_stubs(agent1: dict, *, want: int) -> list[PatentHit]:
    analysis = agent1.get("analysis", {}) or {}
    concepts = analysis.get("similar_known_concepts", []) or []
    feature_names = [f.get("name") or f.get("id") or "" for f in agent1.get("features", []) or []]

    stubs: list[PatentHit] = []
    for i, concept in enumerate(concepts, start=1):
        if len(stubs) >= want:
            break
        name = concept.get("name") or f"Related concept {i}"
        stubs.append(
            PatentHit(
                patent_number=f"CONCEPT-{i}",
                title=name,
                abstract=concept.get("why_similar") or "",
                claims=(
                    f"Known concept: {name}. "
                    f"Overlapping features: {', '.join(concept.get('matching_features', []) or [])}. "
                    f"Reported differences: {concept.get('differences', '') or 'n/a'}"
                ),
                source="derived",
                source_url="",
                relevance_score=round(float(concept.get("similarity_score", 0.0)) * 10, 2),
                matching_features=concept.get("matching_features", []) or feature_names[:2],
            )
        )

    j = len(stubs)
    while len(stubs) < want:
        j += 1
        stubs.append(
            PatentHit(
                patent_number=f"CONCEPT-{j}",
                title=analysis.get("invention") or "General domain prior art",
                abstract=analysis.get("similarity_explanation")
                or "No specific overlapping concept was identified for this element.",
                claims="No specific overlapping claim elements were identified.",
                source="derived",
                relevance_score=0.0,
                matching_features=feature_names[:2],
            )
        )
    return stubs


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


__all__ = ["PatentSearchService"]
