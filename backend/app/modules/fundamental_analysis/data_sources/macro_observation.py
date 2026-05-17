"""Wspolny model obserwacji makro dla warstwy data sources."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MacroObservation:
    """Reprezentuje pojedyncza obserwacje wskaznika makro."""

    value: float
    period: date
    source: str
    unit: str = "pct_yoy"
