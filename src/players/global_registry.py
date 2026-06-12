"""Registry globale carriere giocatori (offline mock)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import FIXTURES_DIR

PLAYER_CAREERS_PATH = FIXTURES_DIR / "players" / "player_careers.json"


@dataclass(frozen=True)
class PlayerLeagueSnapshot:
    player_id: int
    player_name: str
    league_id: int
    season_id: int | None
    team_id: int | None
    position: str | None
    minutes: int
    rating: float
    rating_percentile: float
    sample_confidence: float


@dataclass(frozen=True)
class PlayerCareer:
    player_id: int
    player_name: str
    snapshots: tuple[PlayerLeagueSnapshot, ...]


def _snapshot_from_dict(data: dict) -> PlayerLeagueSnapshot:
    return PlayerLeagueSnapshot(
        player_id=int(data["player_id"]),
        player_name=str(data["player_name"]),
        league_id=int(data["league_id"]),
        season_id=int(data["season_id"]) if data.get("season_id") is not None else None,
        team_id=int(data["team_id"]) if data.get("team_id") is not None else None,
        position=str(data["position"]) if data.get("position") is not None else None,
        minutes=int(data.get("minutes", 0)),
        rating=float(data["rating"]),
        rating_percentile=float(data.get("rating_percentile", 0.5)),
        sample_confidence=float(data.get("sample_confidence", 0.5)),
    )


def _career_from_dict(data: dict) -> PlayerCareer:
    snapshots = tuple(_snapshot_from_dict(s) for s in data.get("snapshots", ()))
    return PlayerCareer(
        player_id=int(data["player_id"]),
        player_name=str(data["player_name"]),
        snapshots=snapshots,
    )


def load_player_careers(
    league_id: int | None = None,
    *,
    path: Path | None = None,
) -> dict[int, PlayerCareer]:
    """Carica carriere mock. Se league_id è impostato, filtra snapshot per quella lega."""
    source = path or PLAYER_CAREERS_PATH
    if not source.exists():
        return {}
    payload = json.loads(source.read_text(encoding="utf-8"))
    careers: dict[int, PlayerCareer] = {}
    for item in payload.get("players", ()):
        career = _career_from_dict(item)
        if league_id is None:
            careers[career.player_id] = career
            continue
        filtered = tuple(s for s in career.snapshots if s.league_id == league_id)
        if filtered:
            careers[career.player_id] = PlayerCareer(
                player_id=career.player_id,
                player_name=career.player_name,
                snapshots=filtered,
            )
    return careers


def get_latest_snapshot(
    player_id: int,
    *,
    before_league_id: int | None = None,
    careers: dict[int, PlayerCareer] | None = None,
) -> PlayerLeagueSnapshot | None:
    registry = careers if careers is not None else load_player_careers()
    career = registry.get(player_id)
    if career is None or not career.snapshots:
        return None
    snapshots = career.snapshots
    if before_league_id is not None:
        snapshots = tuple(s for s in snapshots if s.league_id != before_league_id)
    if not snapshots:
        return None
    return max(snapshots, key=lambda s: (s.minutes, s.rating))


def get_player_snapshot_for_league(
    player_id: int,
    league_id: int,
    *,
    careers: dict[int, PlayerCareer] | None = None,
) -> PlayerLeagueSnapshot | None:
    registry = careers if careers is not None else load_player_careers()
    career = registry.get(player_id)
    if career is None:
        return None
    league_snapshots = [s for s in career.snapshots if s.league_id == league_id]
    if not league_snapshots:
        return None
    return max(league_snapshots, key=lambda s: (s.minutes, s.rating))
