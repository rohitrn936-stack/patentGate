"""Agent 3 - Defender package."""

from .agent import Defender
from .schemas import (
    AnalyzeRequest,
    DefenseAnalysis,
    DefenderResponse,
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