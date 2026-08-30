from typing import List

from .schemas import (
    RiskItem,
    RiskLevel,
    RiskMatrixRequest,
    RiskMatrixResponse,
)


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
        findings: List[dict],
    ) -> List[dict]:
        """
        Find Agent 3 findings that appear related to
        the claim element.

        This is intentionally simple for the first version.
        """

        claim_lower = claim_element.lower()

        matches = []

        for finding in findings:

            text = str(finding).lower()

            if claim_lower in text:
                matches.append(finding)

        return matches

    def _has_distinction(
        self,
        findings: List[dict],
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
        findings: List[dict],
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
        redesign_options: List[dict],
    ) -> bool:

        element_words = set(
            claim_element.lower().split()
        )

        for option in redesign_options:

            option_text = str(option).lower()

            option_words = set(
                option_text.split()
            )

            if element_words.intersection(option_words):
                return True

        return False

    def generate(
        self,
        request: RiskMatrixRequest,
    ) -> RiskMatrixResponse:

        risks: List[RiskItem] = []

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