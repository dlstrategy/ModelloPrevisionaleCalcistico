"""Mapper offline-first Sportmonks JSON → strutture interne."""

from src.sportmonks.mappers.coach_mapper import (
    extract_coach_statistics,
    extract_current_fixture_coaches,
    map_coach_to_profile,
    map_coaches_payload_to_registry,
)
from src.sportmonks.mappers.lineup_mapper import (
    extract_fixture_lineups,
    extract_starting_xi_player_ids,
    map_lineups_to_player_companion,
    map_lineups_to_tactical_companion,
)
from src.sportmonks.mappers.player_mapper import (
    extract_player_skill_vector,
    map_player_statistics_to_snapshot,
    map_players_payload_to_careers,
)
from src.sportmonks.mappers.standings_mapper import (
    map_standings_payload,
    map_standings_to_companion,
)
from src.sportmonks.mappers.statistics_mapper import (
    extract_fixture_statistics,
    map_statistics_payload_to_companions,
    map_statistics_to_shots_companion,
    map_statistics_to_xg_companion,
)

__all__ = [
    "extract_coach_statistics",
    "extract_current_fixture_coaches",
    "extract_fixture_lineups",
    "extract_fixture_statistics",
    "extract_player_skill_vector",
    "extract_starting_xi_player_ids",
    "map_coach_to_profile",
    "map_coaches_payload_to_registry",
    "map_lineups_to_player_companion",
    "map_lineups_to_tactical_companion",
    "map_player_statistics_to_snapshot",
    "map_players_payload_to_careers",
    "map_standings_payload",
    "map_standings_to_companion",
    "map_statistics_payload_to_companions",
    "map_statistics_to_shots_companion",
    "map_statistics_to_xg_companion",
]
