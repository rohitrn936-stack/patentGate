"""Small, credential-free Google Patents discovery and ranking layer."""
from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
from typing import Any, Protocol
from urllib.parse import quote_plus

import httpx

from .models import FeatureExtractionResult, PatentResult, PatentSearchResult

GOOGLE_PATENTS_SEARCH_URL = "https://patents.google.com/xhr/query"
_STOP_WORDS = frozenset("a an and are as at by for from in into is it of on or the to using with smart device system product method apparatus wearable sensor".split())


class HttpClient(Protocol):
    def get(self, url: str, *, params: dict[str, str]) -> Any: ...


@dataclass(frozen=True)
class _Candidate:
    patent_id: str
    title: str
    url: str
    publication_date: str | None
    snippet: str | None


def generate_queries(extraction: FeatureExtractionResult, limit: int = 5) -> list[str]:
    """Generate three to five focused concept combinations from Agent 1 output."""
    feature_concepts = [feature.name for feature in extraction.features]
    for feature in extraction.features:
        feature_concepts.extend(feature.technical_components)
    preferred = _unique([*extraction.search_terms, *extraction.technical_keywords, *feature_concepts])
    tokens = _unique([token for concept in preferred for token in _tokens(concept)])
    focused: list[str] = []
    for start in range(min(len(tokens), limit)):
        terms = tokens[start:start + 5]
        if len(terms) >= 3:
            focused.append(" ".join(terms))
    if not focused:
        focused = [" ".join(extraction.domain)]
    return _unique(focused)[:limit]


class GooglePatentsSearch:
    """Queries the public Google Patents search endpoint; no key is required."""

    def __init__(self, client: HttpClient | None = None):
        self._client = client

    def search(self, extraction: FeatureExtractionResult) -> PatentSearchResult:
        queries = generate_queries(extraction)
        candidates: list[_Candidate] = []
        warnings: list[str] = []
        client = self._client or httpx.Client(timeout=15.0, follow_redirects=True, headers={"User-Agent": "ClaimBreaker-Hackathon-MVP/0.1"})
        try:
            for query in queries:
                try:
                    response = client.get(GOOGLE_PATENTS_SEARCH_URL, params={"url": f"q={quote_plus(query)}"})
                    response.raise_for_status()
                    candidates.extend(_parse_response(response.json()))
                except httpx.TimeoutException:
                    warnings.append(f"Google Patents request timed out for query: {query}")
                except httpx.HTTPError as exc:
                    warnings.append(f"Google Patents request failed for query '{query}': {exc}")
                except (TypeError, ValueError) as exc:
                    warnings.append(f"Google Patents returned malformed results for query '{query}': {exc}")
        finally:
            if self._client is None:
                client.close()

        unique = _deduplicate(candidates)
        ranked = [result for candidate in unique if (result := _rank(candidate, extraction)).relevance_score > 0]
        ranked.sort(key=lambda result: (-result.relevance_score, result.patent_id))
        return PatentSearchResult(queries=queries, results=ranked[:5], warnings=warnings)


def _parse_response(payload: Any) -> list[_Candidate]:
    if not isinstance(payload, dict):
        raise ValueError("response is not a JSON object")
    results = payload.get("results")
    if not isinstance(results, dict):
        raise ValueError("results is not an object")
    clusters = results.get("cluster", [])
    if not isinstance(clusters, list):
        raise ValueError("results.cluster is not a list")
    parsed: list[_Candidate] = []
    for cluster in clusters:
        for entry in cluster.get("result", []) if isinstance(cluster, dict) else []:
            patent = entry.get("patent", {}) if isinstance(entry, dict) else {}
            if not isinstance(patent, dict):
                continue
            patent_id = _clean(patent.get("publication_number"))
            result_id = _clean(entry.get("id"))
            if not patent_id and result_id.startswith("patent/"):
                patent_id = result_id.split("/")[1]
            title = _clean(patent.get("title"))
            if not patent_id or not title:
                continue
            url = f"https://patents.google.com/patent/{patent_id}/en"
            parsed.append(_Candidate(patent_id, title, url, _clean(patent.get("publication_date")) or None, _clean(patent.get("snippet")) or None))
    return parsed


def _deduplicate(candidates: list[_Candidate]) -> list[_Candidate]:
    seen: set[tuple[str, str]] = set()
    result: list[_Candidate] = []
    for candidate in candidates:
        keys = (("id", candidate.patent_id.lower()), ("url", _normalize_url(candidate.url)), ("title", _normalize_title(candidate.title)))
        if any(key in seen for key in keys):
            continue
        seen.update(keys)
        result.append(candidate)
    return result


def _rank(candidate: _Candidate, extraction: FeatureExtractionResult) -> PatentResult:
    text = f"{candidate.title} {candidate.snippet or ''}".lower()
    terms = _unique([*extraction.search_terms, *extraction.technical_keywords])
    matched_terms = [term for term in terms if _term_matches(term, text)]
    matched_features = [feature.id for feature in extraction.features if _feature_matches(feature.name, feature.technical_components, text)]
    # Combination matches matter more than isolated broad terms.
    score = float(len(matched_terms) * 2 + len(matched_features) * 3)
    if len(matched_terms) > 1:
        score += float(len(matched_terms) * (len(matched_terms) - 1))
    title_terms = sum(_term_matches(term, candidate.title.lower()) for term in terms)
    score += float(title_terms * 2)
    return PatentResult(patent_id=candidate.patent_id, title=candidate.title, url=candidate.url, publication_date=candidate.publication_date, snippet=candidate.snippet, relevance_score=score, matched_features=matched_features, matched_terms=matched_terms)


def _feature_matches(name: str, components: list[str], text: str) -> bool:
    tokens = _tokens(" ".join([name, *components]))
    return bool(tokens) and sum(token in text for token in tokens) >= min(2, len(tokens))


def _term_matches(term: str, text: str) -> bool:
    tokens = _tokens(term)
    return bool(tokens) and all(token in text for token in tokens)


def _tokens(value: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9][a-z0-9-]*", value.lower()) if len(word) > 2 and word not in _STOP_WORDS]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", unescape(str(value or "")))).strip()


def _normalize_url(value: str) -> str:
    return value.split("?", 1)[0].rstrip("/").lower()


def _normalize_title(value: str) -> str:
    return " ".join(_tokens(value))


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if isinstance(value, str) and value.strip()))
