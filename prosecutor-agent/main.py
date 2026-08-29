import json
import sys

from agent import analyze_product


def load_input():
    """Load product and patent information from input.json."""

    try:
        with open("input.json", "r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError:
        print("ERROR: input.json was not found.")
        sys.exit(1)

    except json.JSONDecodeError:
        print("ERROR: input.json contains invalid JSON.")
        sys.exit(1)

    if "product" not in data:
        print("ERROR: input.json is missing 'product'.")
        sys.exit(1)

    if "patents" not in data:
        print("ERROR: input.json is missing 'patents'.")
        sys.exit(1)

    if not isinstance(data["patents"], list):
        print("ERROR: 'patents' must be a list.")
        sys.exit(1)

    return data


def save_output(result):
    """Save structured agent output to output.json."""

    with open("output.json", "w", encoding="utf-8") as file:
        json.dump(
            result.model_dump(),
            file,
            indent=2,
            ensure_ascii=False
        )


def display_result(result):
    """Display the prosecutor analysis in the terminal."""

    print()
    print("=" * 70)
    print("PROSECUTOR AGENT")
    print("=" * 70)

    # --------------------------------------------------------
    # RISK CLAIMS
    # --------------------------------------------------------

    print()
    print("RISK CLAIMS")
    print("-" * 70)

    if not result.risk_claims:
        print("No potentially risky claims identified.")

    for claim in result.risk_claims:
        print(f"Patent: {claim.patent_id}")
        print(f"Claim: {claim.claim_id}")
        print(f"Risk Level: {claim.risk_level}")
        print(f"Reason: {claim.reason}")
        print()

    # --------------------------------------------------------
    # CLAIM ELEMENT MAPPINGS
    # --------------------------------------------------------

    print()
    print("CLAIM ELEMENT MAPPINGS")
    print("-" * 70)

    if not result.claim_element_mappings:
        print("No claim-to-product mappings identified.")

    for mapping in result.claim_element_mappings:
        print(f"Patent: {mapping.patent_id}")
        print(f"Claim: {mapping.claim_id}")
        print(f"Claim Element: {mapping.claim_element}")
        print(f"Product Feature: {mapping.product_feature}")
        print(f"Strength: {mapping.strength}")
        print(f"Explanation: {mapping.explanation}")
        print()

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    print()
    print("CONFIDENCE PER PATENT")
    print("-" * 70)

    for confidence in result.confidence_per_patent:
        print(f"Patent: {confidence.patent_id}")
        print(f"Confidence: {confidence.confidence}")
        print(f"Explanation: {confidence.explanation}")
        print()

    print("=" * 70)


def main():
    # Load input
    data = load_input()

    product = data["product"]
    patents = data["patents"]

    # Check patent count
    if len(patents) != 5:
        print(
            f"WARNING: Expected 5 patents, "
            f"but received {len(patents)} patents."
        )

    print()
    print("Running Prosecutor Agent...")
    print("Model: gpt-5-nano")
    print("Search: Disabled")
    print()

    try:
        # Run agent
        result = analyze_product(product, patents)

    except Exception as error:
        print()
        print("ERROR: Prosecutor Agent failed.")
        print()
        print(error)
        sys.exit(1)

    # Display result
    display_result(result)

    # Save JSON output
    save_output(result)

    print()
    print("Structured output saved to: output.json")
    print()


if __name__ == "__main__":
    main()