"""Agent 3 - Defender package."""

from .agent import Defender
from .schemas import (
    AnalyzeRequest,
    DefenderResponse,
    DefenseAnalysis,
    Distinction,
    PriorArtGap,
    WeakClaimElement,
)

__all__ = [
    "Defender",
    "DefenseAnalysis",
    "DefenderResponse",
    "Distinction",
    "PriorArtGap",
    "WeakClaimElement",
    "AnalyzeRequest",
]