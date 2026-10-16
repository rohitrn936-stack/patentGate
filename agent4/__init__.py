"""Agent 4 - Design-Around Engineer (alternative design generation)."""

from __future__ import annotations

from .agent import DesignEngineer
from .models import (
    AlternativeDesign,
    DefenderOutput,
    DesignOutput,
    DesignRequest,
    Product,
    ProsecutorOutput,
)

__all__ = [
    "DesignEngineer",
    "Product",
    "ProsecutorOutput",
    "DefenderOutput",
    "DesignRequest",
    "AlternativeDesign",
    "DesignOutput",
]
