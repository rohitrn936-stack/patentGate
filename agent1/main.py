"""PatentGate - Agent 1 CLI demo.

Usage:
    python main.py "DESCRIPTION" [--image PATH]
    python main.py                      # interactive prompt

Example:
    python main.py "Create a water bottle that measures the temperature of
    the liquid using a sensor in the cap and sends the temperature to a
    smartphone using Bluetooth."

The resulting structured JSON (features + knowledge-based similarity analysis)
is written to stdout. A frontend will replace this CLI later.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from agent1 import run_agent1

RESULTS_FILE = "results.json"
# The project root (parent of the agent1/ package), where results.json lives.
RESULTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PatentGate Agent 1: technical feature extraction "
        "and knowledge-based similar-concept analysis."
    )
    parser.add_argument(
        "description",
        nargs="?",
        help="Product description. If omitted, you are prompted interactively.",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Optional path to a product image (PNG or JPG).",
    )
    parser.add_argument(
        "--no-env",
        action="store_true",
        help="Do not load the .env file (useful for scripting).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.no_env:
        load_env = False
    else:
        load_env = True
        load_dotenv()

    description = (args.description or "").strip()
    if not description:
        try:
            description = input("Describe your product: ").strip()
        except EOFError:
            print("No product description provided.", file=sys.stderr)
            sys.exit(1)

    try:
        result = run_agent1(description, image_path=args.image, load_env=load_env)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    payload = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
    print(payload)

    results_path = os.path.join(RESULTS_DIR, RESULTS_FILE)
    with open(results_path, "w", encoding="utf-8") as handle:
        handle.write(payload + "\n")
    print(f"Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    main()