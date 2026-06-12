"""Scope esplicito per isolamento dati per campionato/stagione."""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.match import Match


@dataclass(frozen=True)
class DataScope:
    """Identità logica di un dataset o artifact legato a lega (e opzionalmente stagione)."""

    league_id: int
    season_id: int | None = None

    @property
    def league_key(self) -> str:
        return f"league_{self.league_id}"

    @property
    def season_key(self) -> str | None:
        if self.season_id is None:
            return None
        return f"season_{self.season_id}"

    @property
    def dataset_key(self) -> str:
        if self.season_id is None:
            return self.league_key
        return f"{self.league_key}_season_{self.season_id}"

    @property
    def label(self) -> str:
        if self.season_id is None:
            return f"Lega {self.league_id}"
        return f"Lega {self.league_id}, stagione {self.season_id}"

    def validate_match(self, match: Match) -> None:
        if match.league_id != self.league_id:
            raise ValueError(
                f"Match league mismatch: scope league {self.league_id}, match league {match.league_id}"
            )

    @classmethod
    def from_dataset(cls, dataset) -> DataScope:
        return cls(league_id=dataset.league_id, season_id=dataset.season_id)


def scope_metadata_dict(scope: DataScope) -> dict:
    """Metadati scope serializzabili per JSON report/artifact."""
    payload = {
        "league_id": scope.league_id,
        "league_key": scope.league_key,
        "dataset_key": scope.dataset_key,
    }
    if scope.season_id is not None:
        payload["season_id"] = scope.season_id
        payload["season_key"] = scope.season_key
    return payload


def legacy_processed_dataset_filename(scope: DataScope) -> str:
    """Naming file processato attuale (solo league_id, retrocompatibile)."""
    return f"league_{scope.league_id}_dataset.json"


def legacy_feature_trained_artifact_filename(scope: DataScope, model_name: str = "feature_trained") -> str:
    """Naming artifact attuale (solo league_id, retrocompatibile)."""
    return f"{model_name}_{scope.league_id}.json"
