"""Run the Google Patents MVP search from the standard smart-helmet example."""
from __future__ import annotations

from .feature_extractor import extract_features
from .patent_search import GooglePatentsSearch

DESCRIPTION = "A smart helmet detects sudden impacts using sensors and sends an alert to a smartphone after detecting a possible crash."


def main() -> None:
    extraction = extract_features(DESCRIPTION)
    result = GooglePatentsSearch().search(extraction)
    print("Generated queries:")
    for query in result.queries:
        print(f"- {query}")
    print(f"\nResults: {len(result.results)}")
    for patent in result.results:
        print(f"- [{patent.relevance_score:.1f}] {patent.patent_id}: {patent.title}")
        print(f"  {patent.url}")
        print(f"  matched terms: {', '.join(patent.matched_terms) or 'none'}; features: {', '.join(patent.matched_features) or 'none'}")
    for warning in result.warnings:
        print(f"Warning: {warning}")


if __name__ == "__main__":
    main()
