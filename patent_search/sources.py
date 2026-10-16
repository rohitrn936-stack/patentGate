"""Prior-art sources for the patent search layer.

Each function takes a list of query strings plus an ``httpx``-compatible client
and returns a list of :class:`~patent_search.schemas.PatentHit`. Sources never
raise: recoverable problems are appended to the shared ``warnings`` list and an
empty (or partial) result is returned so the service can fall through to the
next source.

Priority order (see :mod:`patent_search.service`):
    1. PatentsView Search API  - needs a free ``PATENTSVIEW_API_KEY``
    2. Google Patents          - unofficial, credential-free XHR endpoint
    3. Tavily web search       - needs ``TAVILY_API_KEY``
    4. concept-derived stubs   - offline fallback, built from Agent 1 output
"""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Protocol
from urllib.parse import quote_plus

from .schemas import PatentHit

PATENTSVIEW_URL = "https://search.patentsview.org/api/v1/patent/"
GOOGLE_PATENTS_URL = "https://patents.google.com/xhr/query"
TAVILY_URL = "https://api.tavily.com/search"

_PATENT_NUMBER_RE = re.compile(r"\b([A-Z]{2}\d{5,}(?:[A-Z]\d?)?)\b")
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class HttpClient(Protocol):
    def get(self, url: str, **kwargs: Any) -> Any: ...
    def post(self, url: str, **kwargs: Any) -> Any: ...


def _clean(value: Any) -> str:
    text = _HTML_TAG_RE.sub("", unescape(str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------------------------------- #
# PatentsView Search API
# --------------------------------------------------------------------------- #
def search_patentsview(
    queries: list[str],
    *,
    api_key: str,
    client: HttpClient,
    warnings: list[str],
    per_query: int = 5,
) -> list[PatentHit]:
    if not api_key:
        return []

    fields = [
        "patent_id",
        "patent_title",
        "patent_abstract",
        "patent_date",
        "patent_earliest_application_date",
        "assignees.assignee_organization",
        "inventors.inventor_name_first",
        "inventors.inventor_name_last",
    ]
    hits: list[PatentHit] = []
    for query in queries:
        terms = query.strip()
        if not terms:
            continue
        q = {"_text_any": {"patent_abstract": terms}}
        params = {
            "q": json.dumps(q),
            "f": json.dumps(fields),
            "o": json.dumps({"size": per_query}),
        }
        try:
            resp = client.get(
                PATENTSVIEW_URL,
                params=params,
                headers={"X-Api-Key": api_key},
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001 - recoverable, fall through
            warnings.append(f"PatentsView query failed ({terms!r}): {exc}")
            continue

        for row in payload.get("patents", []) or []:
            number = _clean(row.get("patent_id"))
            if not number:
                continue
            inventors = [
                _clean(f"{p.get('inventor_name_first', '')} {p.get('inventor_name_last', '')}")
                for p in row.get("inventors", []) or []
            ]
            assignees = [
                _clean(a.get("assignee_organization"))
                for a in row.get("assignees", []) or []
                if _clean(a.get("assignee_organization"))
            ]
            hits.append(
                PatentHit(
                    patent_number=number,
                    title=_clean(row.get("patent_title")),
                    abstract=_clean(row.get("patent_abstract")),
                    filing_date=_clean(row.get("patent_earliest_application_date")) or None,
                    publication_date=_clean(row.get("patent_date")) or None,
                    inventors=[i for i in inventors if i],
                    assignee=assignees[0] if assignees else None,
                    source="patentsview",
                    source_url=f"https://patents.google.com/patent/{number}",
                )
            )
    return hits


# --------------------------------------------------------------------------- #
# Google Patents (unofficial, no key)
# --------------------------------------------------------------------------- #
def search_google_patents(
    queries: list[str],
    *,
    client: HttpClient,
    warnings: list[str],
) -> list[PatentHit]:
    hits: list[PatentHit] = []
    for query in queries:
        terms = query.strip()
        if not terms:
            continue
        try:
            resp = client.get(
                GOOGLE_PATENTS_URL,
                params={"url": f"q={quote_plus(terms)}", "exp": ""},
                headers={"User-Agent": "PatentGate/0.2 (research)"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Google Patents query failed ({terms!r}): {exc}")
            continue

        clusters = (
            payload.get("results", {}).get("cluster", [])
            if isinstance(payload, dict)
            else []
        )
        for cluster in clusters:
            for entry in cluster.get("result", []) if isinstance(cluster, dict) else []:
                patent = entry.get("patent", {}) if isinstance(entry, dict) else {}
                number = _clean(patent.get("publication_number"))
                if not number:
                    result_id = _clean(entry.get("id"))
                    if result_id.startswith("patent/"):
                        number = result_id.split("/")[1]
                title = _clean(patent.get("title"))
                if not number or not title:
                    continue
                hits.append(
                    PatentHit(
                        patent_number=number,
                        title=title,
                        abstract=_clean(patent.get("snippet")),
                        publication_date=_clean(patent.get("publication_date")) or None,
                        filing_date=_clean(patent.get("filing_date")) or None,
                        inventors=[_clean(patent.get("inventor"))]
                        if _clean(patent.get("inventor"))
                        else [],
                        assignee=_clean(patent.get("assignee")) or None,
                        source="google_patents",
                        source_url=f"https://patents.google.com/patent/{number}/en",
                    )
                )
    return hits


# --------------------------------------------------------------------------- #
# Tavily web search
# --------------------------------------------------------------------------- #
def search_tavily(
    queries: list[str],
    *,
    api_key: str,
    client: HttpClient,
    warnings: list[str],
    per_query: int = 5,
) -> list[PatentHit]:
    if not api_key:
        return []

    hits: list[PatentHit] = []
    for query in queries:
        terms = query.strip()
        if not terms:
            continue
        try:
            resp = client.post(
                TAVILY_URL,
                json={
                    "api_key": api_key,
                    "query": f"{terms} patent",
                    "max_results": per_query,
                    "search_depth": "basic",
                    "include_domains": [
                        "patents.google.com",
                        "patents.justia.com",
                        "freepatentsonline.com",
                    ],
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Tavily query failed ({terms!r}): {exc}")
            continue

        for row in payload.get("results", []) or []:
            url = _clean(row.get("url"))
            title = _clean(row.get("title"))
            match = _PATENT_NUMBER_RE.search(url) or _PATENT_NUMBER_RE.search(title)
            number = match.group(1) if match else ""
            if not number and not title:
                continue
            hits.append(
                PatentHit(
                    patent_number=number,
                    title=title,
                    abstract=_clean(row.get("content"))[:1200],
                    source="tavily",
                    source_url=url,
                )
            )
    return hits


__all__ = [
    "HttpClient",
    "search_patentsview",
    "search_google_patents",
    "search_tavily",
    "PATENTSVIEW_URL",
    "GOOGLE_PATENTS_URL",
    "TAVILY_URL",
]
