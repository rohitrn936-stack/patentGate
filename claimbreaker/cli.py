"""JSON-out command line wrapper for ClaimBreaker Agent 1."""
from __future__ import annotations

import argparse
from .feature_extractor import extract_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract patent-searchable product features")
    parser.add_argument("description", help="Natural-language product description")
    parser.add_argument("--image", help="Optional JPEG, PNG, or WebP product image")
    args = parser.parse_args()
    print(extract_features(args.description, args.image).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
