"""Interfaccia comune modelli previsionali."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.models import OutcomeProbabilities
from src.features.match_context import MatchContext


class BaseModel(ABC):
    name: str

    @abstractmethod
    def predict(self, context: MatchContext) -> OutcomeProbabilities:
        """Restituisce probabilità 1/X/2 per la partita."""

    def is_ready(self) -> bool:
        return True
