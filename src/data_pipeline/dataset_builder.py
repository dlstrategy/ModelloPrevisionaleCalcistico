"""Costruzione dataset interno da partite normalizzate."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from src.data_pipeline.scope import DataScope, scope_metadata_dict
from src.domain.enums import ParticipantLocation
from src.domain.match import Match


@dataclass
class MatchDataset:
    league_id: int
    season_id: int | None
    matches: list[Match] = field(default_factory=list)

    def finished_before(self, as_of: datetime) -> list[Match]:
        return sorted(
            [
                m
                for m in self.matches
                if m.is_finished and m.starting_at < as_of
            ],
            key=lambda m: m.starting_at,
        )

    def upcoming_on(self, date_str: str) -> list[Match]:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        return sorted(
            [
                m
                for m in self.matches
                if m.starting_at.date() == target and not m.is_finished
            ],
            key=lambda m: m.starting_at,
        )

    def team_history(self, team_id: int, as_of: datetime) -> list[Match]:
        history: list[Match] = []
        for match in self.finished_before(as_of):
            if any(p.team_id == team_id for p in match.participants):
                history.append(match)
        return history

    def team_goals(self, team_id: int, match: Match) -> tuple[int, int]:
        if match.score is None:
            raise ValueError("Match without score")
        for participant in match.participants:
            if participant.team_id == team_id:
                if participant.location == ParticipantLocation.HOME:
                    return match.score.home, match.score.away
                return match.score.away, match.score.home
        raise ValueError(f"Team {team_id} not in match {match.id}")

    def save(self, path: Path) -> None:
        scope = DataScope.from_dataset(self)
        payload = {
            "league_id": self.league_id,
            "season_id": self.season_id,
            "data_scope": scope_metadata_dict(scope),
            "matches": [
                {
                    "id": m.id,
                    "league_id": m.league_id,
                    "season_id": m.season_id,
                    "starting_at": m.starting_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "round_id": m.round_id,
                    "state_id": m.state_id,
                    "participants": [
                        {
                            "team_id": p.team_id,
                            "team_name": p.team_name,
                            "location": p.location.value,
                        }
                        for p in m.participants
                    ],
                    "score": (
                        {"home": m.score.home, "away": m.score.away} if m.score else None
                    ),
                }
                for m in self.matches
            ],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> MatchDataset:
        from src.domain.enums import ParticipantLocation
        from src.domain.match import MatchParticipant, Score

        payload = json.loads(path.read_text(encoding="utf-8"))
        matches: list[Match] = []
        for item in payload["matches"]:
            participants = [
                MatchParticipant(
                    team_id=int(p["team_id"]),
                    team_name=str(p["team_name"]),
                    location=ParticipantLocation(p["location"]),
                )
                for p in item["participants"]
            ]
            score = None
            if item.get("score"):
                score = Score(home=int(item["score"]["home"]), away=int(item["score"]["away"]))
            matches.append(
                Match(
                    id=int(item["id"]),
                    league_id=int(item["league_id"]),
                    season_id=int(item["season_id"]),
                    starting_at=datetime.strptime(item["starting_at"], "%Y-%m-%d %H:%M:%S"),
                    participants=participants,
                    round_id=item.get("round_id"),
                    state_id=item.get("state_id"),
                    score=score,
                )
            )
        return cls(
            league_id=int(payload["league_id"]),
            season_id=payload.get("season_id"),
            matches=matches,
        )
