import re

from .schemas import (
    RiskItem,
    RiskLevel,
    RiskMatrixRequest,
    RiskMatrixResponse,
)

# Words too common to signal that a redesign option actually targets a claim
# element - without this filter almost every option "matches" every element.
_STOP_WORDS = frozenset(
    """a an and or the to of in on for with without using via be is are as at by from into
    that this these those it its their our your system device apparatus method product
    element claim design option alternative change changes original feature features
    reduce reduces overlap risk patent""".split()
)


def _keywords(text: str) -> set[str]:
    return {
        w
        for w in re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (text or "").lower())
        if w not in _STOP_WORDS
    }


class RiskMatrixService:
    """
    Calculates a technical/prior-art risk matrix using
    Agent 2 and Agent 3 findings.

    This service does not make an LLM API call.
    """

    def _calculate_score(
        self,
        risky: bool,
        overlap: bool,
        distinction: bool,
        redesign_available: bool,
    ) -> int:
        """
        Calculate a deterministic risk score.

        Higher score = greater apparent exposure
        based on the supplied evidence.
        """

        score = 20

        if risky:
            score += 25

        if overlap:
            score += 35

        if distinction:
            score -= 15

        if redesign_available:
            score -= 10

        return max(0, min(100, score))

    def _risk_level(self, score: int) -> RiskLevel:
        if score >= 70:
            return RiskLevel.HIGH

        if score >= 40:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _find_matching_prior_art(
        self,
        claim_element: str,
        findings: list[dict],
    ) -> list[dict]:
        """
        Find Agent 3 findings that appear related to
        the claim element.

        This is intentionally simple for the first version.
        """

        claim_lower = claim_element.lower()
        claim_kw = _keywords(claim_element)

        matches = []

        for finding in findings:

            text = str(finding).lower()

            if claim_lower and claim_lower in text:
                matches.append(finding)
                continue

            # Fall back to keyword overlap so slightly reworded findings still
            # attach to the element they describe.
            if claim_kw and len(claim_kw & _keywords(text)) >= min(2, len(claim_kw)):
                matches.append(finding)

        return matches

    def _has_distinction(
        self,
        findings: list[dict],
    ) -> bool:

        for finding in findings:

            text = str(finding).lower()

            if any(
                keyword in text
                for keyword in [
                    "distinction",
                    "different",
                    "gap",
                    "not disclosed",
                    "absent",
                    "novel",
                ]
            ):
                return True

        return False

    def _has_overlap(
        self,
        findings: list[dict],
    ) -> bool:

        for finding in findings:

            text = str(finding).lower()

            if any(
                keyword in text
                for keyword in [
                    "overlap",
                    "similar",
                    "same",
                    "disclosed",
                    "prior art",
                    "anticipat",
                ]
            ):
                return True

        return False

    def _has_redesign(
        self,
        claim_element: str,
        redesign_options: list[dict],
    ) -> bool:

        element_words = _keywords(claim_element)
        if not element_words:
            return False

        for option in redesign_options:

            option_words = _keywords(str(option))

            # Require a real overlap of meaningful terms, not a single stray word.
            if len(element_words & option_words) >= min(2, len(element_words)):
                return True

        return False

    def generate(
        self,
        request: RiskMatrixRequest,
    ) -> RiskMatrixResponse:

        risks: list[RiskItem] = []

        # Use claim elements when available.
        # Otherwise fall back to risky elements.
        elements = (
            request.claim_elements
            if request.claim_elements
            else request.risky_elements
        )

        for element in elements:

            is_risky = (
                element in request.risky_elements
                or not request.risky_elements
            )

            matching_findings = self._find_matching_prior_art(
                element,
                request.prior_art_findings,
            )

            overlap = self._has_overlap(
                matching_findings
            )

            distinction = self._has_distinction(
                matching_findings
            )

            redesign = self._has_redesign(
                element,
                request.redesign_options,
            )

            score = self._calculate_score(
                risky=is_risky,
                overlap=overlap,
                distinction=distinction,
                redesign_available=redesign,
            )

            level = self._risk_level(score)

            supporting_patents = []

            for finding in matching_findings:

                patent_id = (
                    finding.get("patent_id")
                    if isinstance(finding, dict)
                    else None
                )

                if patent_id:
                    supporting_patents.append(
                        str(patent_id)
                    )

            if overlap:
                reason = (
                    "The supplied Agent 3 findings indicate "
                    "potential similarity or overlap with prior art."
                )
            elif distinction:
                reason = (
                    "Agent 3 identified distinctions or gaps "
                    "in the available prior-art evidence."
                )
            else:
                reason = (
                    "Insufficient matching prior-art evidence "
                    "was supplied for this element."
                )

            recommended_action = None

            if level == RiskLevel.HIGH:
                recommended_action = (
                    "Review this element carefully and consider "
                    "the engineering alternatives identified by Agent 4."
                )

            elif level == RiskLevel.MEDIUM:
                recommended_action = (
                    "Evaluate the identified distinctions and "
                    "consider whether the redesign options reduce exposure."
                )

            else:
                recommended_action = (
                    "Continue monitoring this element against "
                    "the available prior-art evidence."
                )

            risks.append(
                RiskItem(
                    claim_element=element,
                    risk_level=level,
                    score=score,
                    reason=reason,
                    supporting_patents=supporting_patents,
                    prior_art_overlap=(
                        "Potential overlap identified."
                        if overlap
                        else None
                    ),
                    distinction=(
                        "Potential distinction identified."
                        if distinction
                        else None
                    ),
                    recommended_action=recommended_action,
                )
            )

        if not risks:
            return RiskMatrixResponse(
                status="success",
                overall_score=0,
                overall_risk=RiskLevel.LOW,
                risks=[],
            )

        overall_score = round(
            sum(item.score for item in risks)
            / len(risks)
        )

        overall_risk = self._risk_level(
            overall_score
        )

        return RiskMatrixResponse(
            status="success",
            overall_score=overall_score,
            overall_risk=overall_risk,
            risks=risks,
        )