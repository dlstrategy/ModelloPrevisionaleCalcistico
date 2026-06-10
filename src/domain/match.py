"""Entità partita."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.enums import MatchOutcome, ParticipantLocation


@dataclass(frozen=True)
class Score:
    home: int
    away: int

    @property
    def outcome(self) -> MatchOutcome:
        if self.home > self.away:
            return MatchOutcome.HOME
        if self.home < self.away:
            return MatchOutcome.AWAY
        return MatchOutcome.DRAW


@dataclass(frozen=True)
class MatchParticipant:
    team_id: int
    team_name: str
    location: ParticipantLocation


@dataclass
class Match:
    id: int
    league_id: int
    season_id: int
    starting_at: datetime
    participants: list[MatchParticipant]
    round_id: int | None = None
    state_id: int | None = None
    score: Score | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def home(self) -> MatchParticipant:
        for participant in self.participants:
            if participant.location == ParticipantLocation.HOME:
                return participant
        raise ValueError(f"Home participant not found for match {self.id}")

    @property
    def away(self) -> MatchParticipant:
        for participant in self.participants:
            if participant.location == ParticipantLocation.AWAY:
                return participant
        raise ValueError(f"Away participant not found for match {self.id}")

    @property
    def is_finished(self) -> bool:
        return self.score is not None

    @property
    def actual_outcome(self) -> MatchOutcome | None:
        if self.score is None:
            return None
        return self.score.outcome
