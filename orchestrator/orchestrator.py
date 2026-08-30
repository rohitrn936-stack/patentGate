"""Orchestrator core logic.

Coordinates the Agent 2 -> Agent 3 -> Agent 4 pipeline over HTTP/JSON and
decides whether to iterate again or stop. It communicates with agents strictly
via HTTP and never imports their internal classes.

Configuration (environment variables):

- ``AGENT2_URL`` - base URL of Agent 2 (default ``http://127.0.0.1:8002``)
- ``AGENT3_URL`` - base URL of Agent 3 (default ``http://127.0.0.1:8003``)
- ``AGENT4_URL`` - base URL of Agent 4 (default ``http://127.0.0.1:8004``)
- ``MAX_ITERATIONS`` - maximum refinement iterations (default 3)
- ``HTTP_TIMEOUT`` - per-request timeout in seconds (default 60)

The stop decision is driven by structured risk information in the agents'
responses:
- Agent 2 reports ``risk_claims`` with a ``risk_level`` and
  ``confidence_per_patent`` with a ``confidence`` value.
- Agent 3 reports ``weak_claim_elements`` with a ``risk`` severity and an
  overall ``confidence`` value.

Refinement is requested when no sufficiently strong distinction is found and
risk remains high, up to ``MAX_ITERATIONS``. The orchestrator never claims a
result is legally patentable.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .schemas import IterationRecord, RunResult

DEFAULT_AGENT2_URL = "http://127.0.0.1:8002"
DEFAULT_AGENT3_URL = "http://127.0.0.1:8003"
DEFAULT_AGENT4_URL = "http://127.0.0.1:8004"
DEFAULT_MAX_ITERATIONS = 3
DEFAULT_HTTP_TIMEOUT = 60.0

# Risk severities that are considered "high" (case-insensitive).
_HIGH_RISK = {"high", "critical", "severe"}


def _get_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _max_confidence_per_patent(agent2_output: Any) -> float:
    """Highest confidence across Agent 2's confidence_per_patent (0.0 default)."""
    conf = 0.0
    if isinstance(agent2_output, dict):
        for entry in agent2_output.get("confidence_per_patent", []) or []:
            if isinstance(entry, dict):
                conf = max(conf, _get_float(entry.get("confidence"), 0.0))
    return conf


def _has_high_risk_claims(agent2_output: Any) -> bool:
    """True if any of Agent 2's risk_claims has a high/medium-high risk level."""
    if isinstance(agent2_output, dict):
        for claim in agent2_output.get("risk_claims", []) or []:
            if isinstance(claim, dict):
                level = str(claim.get("risk_level", "")).lower()
                if any(word in level for word in ("high", "critical", "severe", "medium")):
                    return True
    return False


def _high_weak_element_count(agent3_output: Any) -> int:
    """Count Agent 3's weak_claim_elements whose risk is high/critical."""
    count = 0
    da = agent3_output if isinstance(agent3_output, dict) else {}
    # Agent 3 wraps its analysis under "defense_analysis".
    analysis = da.get("defense_analysis", da) if isinstance(da, dict) else {}
    if isinstance(analysis, dict):
        for weak in analysis.get("weak_claim_elements", []) or []:
            if isinstance(weak, dict):
                risk = str(weak.get("risk", "")).lower()
                if risk in _HIGH_RISK:
                    count += 1
    return count


class Orchestrator:
    """Runs the Agent 2 -> Agent 3 -> Agent 4 pipeline over HTTP."""

    def __init__(
        self,
        agent2_url: Optional[str] = None,
        agent3_url: Optional[str] = None,
        agent4_url: Optional[str] = None,
        max_iterations: Optional[int] = None,
        timeout: Optional[float] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.agent2_url = (
            (agent2_url or os.getenv("AGENT2_URL") or DEFAULT_AGENT2_URL).rstrip("/")
        )
        self.agent3_url = (
            (agent3_url or os.getenv("AGENT3_URL") or DEFAULT_AGENT3_URL).rstrip("/")
        )
        self.agent4_url = (
            (agent4_url or os.getenv("AGENT4_URL") or DEFAULT_AGENT4_URL).rstrip("/")
        )
        raw_max = os.getenv("MAX_ITERATIONS")
        try:
            self.max_iterations = int(
                max_iterations if max_iterations is not None else raw_max
            )
        except (TypeError, ValueError):
            self.max_iterations = DEFAULT_MAX_ITERATIONS
        self.max_iterations = max(1, self.max_iterations)

        try:
            self.timeout = float(
                timeout if timeout is not None else os.getenv("HTTP_TIMEOUT")
            )
        except (TypeError, ValueError):
            self.timeout = DEFAULT_HTTP_TIMEOUT

        self._client = client

    # -- HTTP helpers --------------------------------------------------------

    def _client_or_new(self) -> httpx.Client:
        if self._client is not None:
            return self._client
        return httpx.Client(timeout=self.timeout)

    def _post(self, url: str, payload: dict) -> dict:
        client = self._client_or_new()
        response = client.post(url, json=payload)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            raise RuntimeError(
                f"Invalid JSON response from {url}: {response.text[:200]}"
            )

    # -- agent calls ---------------------------------------------------------

    def call_agent2(self, product: Any, patents: Any) -> dict:
        """POST Agent 2 /analyze and return its output."""
        return self._post(
            f"{self.agent2_url}/analyze",
            {"product": product, "patents": patents},
        )

    def call_agent3(self, agent2_output: dict) -> dict:
        """POST Agent 3 /analyze, preserving its input contract."""
        return self._post(
            f"{self.agent3_url}/analyze",
            {"agent2_output": agent2_output},
        )

    def call_agent4(self, product: Any, agent2_output: dict, agent3_output: dict) -> dict:
        """POST Agent 4 /design with product + prosecutor + defender."""
        # Agent 3 wrapper shape -> extract the bare defense analysis for Agent 4.
        defender = agent3_output
        if isinstance(agent3_output, dict) and "defense_analysis" in agent3_output:
            defender = agent3_output.get("defense_analysis")

        return self._post(
            f"{self.agent4_url}/design",
            {
                "product": product,
                "prosecutor": agent2_output,
                "defender": defender,
            },
        )

    # -- stop decision -------------------------------------------------------

    def decide_stop(
        self,
        agent2_output: dict,
        agent3_output: dict,
        agent4_output: dict,
        iteration: int,
    ) -> tuple[str, str]:
        """Return (next_step, stop_reason) based on structured risk fields.

        The decision never performs arbitrary string matching; it uses the
        structured ``risk_level``/``confidence``/``risk`` fields.
        """
        if agent2_output is None or agent3_output is None or agent4_output is None:
            return ("refine", "Incomplete agent output; refining.")

        max_conf = _max_confidence_per_patent(agent2_output)
        has_high_risk = _has_high_risk_claims(agent2_output)
        high_weak_count = _high_weak_element_count(agent3_output)

        if has_high_risk and max_conf >= 0.8 and iteration < self.max_iterations:
            return (
                "refine",
                "High patent risk (confidence >= 0.8) with high-risk claims; "
                "a refinement iteration is required.",
            )

        if has_high_risk and high_weak_count > 0 and iteration < self.max_iterations:
            return (
                "refine",
                "High-risk claims remain and Agent 3 identified weak claim "
                "elements; refining to reduce overlap.",
            )

        if iteration >= self.max_iterations:
            return (
                "stop",
                f"Reached MAX_ITERATIONS ({self.max_iterations}).",
            )

        return ("stop", "No high-risk overlap remains; analysis complete.")

    # -- main pipeline -------------------------------------------------------

    def run(self, product: Any, patents: Any) -> RunResult:
        """Execute the Agent 2 -> Agent 3 -> Agent 4 loop."""
        if product is None and patents is None:
            return RunResult(
                final_status="error",
                errors=["Invalid request: 'product' and/or 'patents' is required."],
            )

        history: list[IterationRecord] = []
        last_agent2: Any = None
        last_agent3: Any = None
        last_agent4: Any = None
        stop_reason = ""
        next_step = ""

        for iteration in range(1, self.max_iterations + 1):
            agent2 = self.call_agent2(product, patents)
            agent3 = self.call_agent3(agent2)
            agent4 = self.call_agent4(product, agent2, agent3)

            last_agent2, last_agent3, last_agent4 = agent2, agent3, agent4

            next_step, stop_reason = self.decide_stop(
                agent2, agent3, agent4, iteration
            )

            history.append(
                IterationRecord(
                    iteration=iteration,
                    agent2_output=agent2,
                    agent3_output=agent3,
                    agent4_output=agent4,
                    stop_reason=stop_reason,
                )
            )

            if next_step == "stop":
                break

        return RunResult(
            final_status="ok",
            iteration_count=len(history),
            final_agent2_output=last_agent2,
            final_agent3_output=last_agent3,
            final_agent4_output=last_agent4,
            iteration_history=history,
            next_step=next_step or "stop",
            stop_reason=stop_reason,
        )


__all__ = ["Orchestrator"]