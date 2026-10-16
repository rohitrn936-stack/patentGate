"""Patent search layer - prior-art retrieval from Agent 1's extracted features.

    from patent_search import PatentSearchService

    result = PatentSearchService().search(agent1_output_dict)
    for hit in result.patents:      # up to 5, relevance-ranked
        ...

Sources are tried in priority order (PatentsView -> Google Patents -> Tavily)
and a concept-derived fallback guarantees a non-empty result offline.
"""

from __future__ import annotations

from .query import build_queries, feature_tokens
from .schemas import PatentHit, PatentSearchResult
from .service import PatentSearchService

__all__ = [
    "PatentSearchService",
    "PatentHit",
    "PatentSearchResult",
    "build_queries",
    "feature_tokens",
]
