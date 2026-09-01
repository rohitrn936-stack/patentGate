

def build_risk_matrix_prompt(
    product_description: str,
    claim_elements: list[str],
    risky_elements: list[str],
    prior_art_findings: list[dict],
    redesign_options: list[dict],
) -> str:

    claim_text = "\n".join(
        f"- {element}"
        for element in claim_elements
    )

    risky_text = "\n".join(
        f"- {element}"
        for element in risky_elements
    )

    prior_art_text = "\n".join(
        f"- {finding}"
        for finding in prior_art_findings
    )

    redesign_text = "\n".join(
        f"- {option}"
        for option in redesign_options
    )

    return f"""
You are assisting a patent-risk analysis system.

Your task is to evaluate potentially risky claim elements
using ONLY the evidence supplied below.

IMPORTANT:
- Do not provide legal advice.
- Do not claim that a patent is definitely valid or invalid.
- Do not invent patents.
- Do not invent prior-art evidence.
- Do not treat the risk score as a legal conclusion.
- Risk represents technical/prior-art exposure based on the supplied data.

PRODUCT:
{product_description}

CLAIM ELEMENTS:
{claim_text or "- None provided"}

RISKY ELEMENTS:
{risky_text or "- None provided"}

PRIOR ART FINDINGS:
{prior_art_text or "- None provided"}

REDESIGN OPTIONS:
{redesign_text or "- None provided"}

RISK SCORING:

0-39   = LOW
40-69  = MEDIUM
70-100 = HIGH

Consider:

1. Similarity to the identified prior art.
2. Strength of the distinction identified by Agent 3.
3. How central the element is to the product.
4. Whether Agent 4 provides a meaningful engineering alternative.
5. Whether the evidence supplied is strong or weak.

For every risky claim element provide:

- claim_element
- risk_level
- score
- reason
- supporting_patents
- prior_art_overlap
- distinction
- recommended_action

Return structured JSON only.
""".strip()