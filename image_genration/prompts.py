from .schemas import DesignOption


def build_before_after_prompt(
    product_description: str,
    original_concept: str | None,
    risky_elements: list[str],
    option: DesignOption,
) -> str:
    """
    Build the image-generation prompt for one Agent 4 redesign option.
    """

    original = original_concept or product_description

    # Agent 4 may hand us a ready-made DALL-E prompt; use it as the base and
    # still append the guard-rails so no image claims legal validity.
    if option.prompt_override and option.prompt_override.strip():
        return (
            option.prompt_override.strip()
            + "\n\nRender as a clean side-by-side BEFORE vs AFTER technical "
            "concept illustration. This is a conceptual engineering "
            "visualization only - not a legally valid patent drawing. Do not "
            "add patent numbers, legal claims, or attorney statements."
        )

    risky_text = "\n".join(
        f"- {item}"
        for item in risky_elements
    )

    changes_text = "\n".join(
        f"- {change}"
        for change in option.key_changes
    )

    prompt = f"""
Create a professional technical engineering concept illustration
showing a BEFORE vs AFTER comparison for a product redesign.

IMPORTANT:
This is a conceptual engineering visualization only.
Do not present it as a legally valid patent drawing.
Do not make legal conclusions.
Do not add fake patent numbers, legal claims, or attorney statements.

ORIGINAL PRODUCT:
{product_description}

ORIGINAL CONCEPT — BEFORE:
{original}

POTENTIALLY RISKY CLAIM ELEMENTS:
{risky_text if risky_text else "- No specific risky elements supplied"}

REDESIGN OPTION:
Option {option.option_id}: {option.title}

REDESIGNED CONCEPT — AFTER:
{option.description}

KEY ENGINEERING CHANGES:
{changes_text if changes_text else "- Show the differences described in the redesign"}

VISUAL REQUIREMENTS:

1. Create a clean side-by-side BEFORE and AFTER technical illustration.

2. The LEFT side must be labeled:
   "BEFORE"

3. The RIGHT side must be labeled:
   "AFTER — OPTION {option.option_id}"

4. Show the original system/product on the BEFORE side.

5. Show the redesigned system/product on the AFTER side.

6. Clearly visualize the engineering differences between the two.

7. Use arrows, component callouts, and simple labels to highlight
   important changes.

8. Use a professional engineering diagram style.

9. Use clean technical line-art aesthetics.

10. Keep the background simple and uncluttered.

11. Make the components visually understandable.

12. Avoid excessive decorative elements.

13. Make the BEFORE and AFTER layouts visually comparable.

14. Emphasize functional engineering changes rather than marketing
    language.

15. Do not include people unless they are necessary to demonstrate
    the engineering change.

16. Do not invent technical components that contradict the supplied
    redesign description.

The final image should look like a clear engineering concept sketch
that a product engineer could use to visually understand the
difference between the original design and the proposed alternative.
"""

    return prompt.strip()