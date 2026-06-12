"""Configurazione centralizzata del progetto."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PREDICTIONS_DIR = DATA_DIR / "predictions"
BACKTESTS_DIR = DATA_DIR / "backtests"
QUALITY_DIR = DATA_DIR / "quality"
CACHE_DB_PATH = DATA_DIR / "cache.db"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

SERIE_A_LEAGUE_ID = 384


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_token: str | None
    base_url: str
    default_league_id: int
    enable_sportmonks_sync: bool
    cache_ttl_fixtures: int
    cache_ttl_standings: int
    cache_ttl_teams: int
    form_window_matches: int
    form_weight: float
    season_weight: float
    home_advantage: float
    poisson_max_goals: int
    dixon_coles_rho: float
    elo_k_factor: float
    elo_home_advantage: float
    elo_initial_rating: float
    min_confidence_threshold: float
    calibration_temperature: float
    ensemble_weight_poisson: float
    ensemble_weight_dixon_coles: float
    ensemble_weight_elo: float
    ensemble_weight_feature: float
    log_level: str
    offline_mode: str

    @property
    def is_offline(self) -> bool:
        if self.offline_mode == "true":
            return True
        if self.offline_mode == "false":
            return False
        return not self.api_token or not self.enable_sportmonks_sync

    @property
    def has_api_token(self) -> bool:
        return bool(self.api_token)

    @property
    def can_sync_api(self) -> bool:
        return self.has_api_token and self.enable_sportmonks_sync


def load_settings(env_file: Path | None = None) -> Settings:
    if env_file is None:
        env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)

    for directory in (DATA_DIR, RAW_DIR, PROCESSED_DIR, PREDICTIONS_DIR, BACKTESTS_DIR, QUALITY_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    token = os.getenv("SPORTMONKS_API_TOKEN", "").strip() or None

    return Settings(
        api_token=token,
        base_url=os.getenv("SPORTMONKS_BASE_URL", "https://api.sportmonks.com/v3/football").rstrip("/"),
        default_league_id=_int("DEFAULT_LEAGUE_ID", SERIE_A_LEAGUE_ID),
        enable_sportmonks_sync=_bool("ENABLE_SPORTMONKS_SYNC", False),
        cache_ttl_fixtures=_int("CACHE_TTL_FIXTURES", 3600),
        cache_ttl_standings=_int("CACHE_TTL_STANDINGS", 86400),
        cache_ttl_teams=_int("CACHE_TTL_TEAMS", 86400),
        form_window_matches=_int("FORM_WINDOW_MATCHES", 5),
        form_weight=_float("FORM_WEIGHT", 0.7),
        season_weight=_float("SEASON_WEIGHT", 0.3),
        home_advantage=_float("HOME_ADVANTAGE", 1.12),
        poisson_max_goals=_int("POISSON_MAX_GOALS", 5),
        dixon_coles_rho=_float("DIXON_COLES_RHO", -0.13),
        elo_k_factor=_float("ELO_K_FACTOR", 20.0),
        elo_home_advantage=_float("ELO_HOME_ADVANTAGE", 65.0),
        elo_initial_rating=_float("ELO_INITIAL_RATING", 1500.0),
        min_confidence_threshold=_float("MIN_CONFIDENCE_THRESHOLD", 0.38),
        calibration_temperature=_float("CALIBRATION_TEMPERATURE", 1.0),
        ensemble_weight_poisson=_float("ENSEMBLE_WEIGHT_POISSON", 0.35),
        ensemble_weight_dixon_coles=_float("ENSEMBLE_WEIGHT_DIXON_COLES", 0.30),
        ensemble_weight_elo=_float("ENSEMBLE_WEIGHT_ELO", 0.20),
        ensemble_weight_feature=_float("ENSEMBLE_WEIGHT_FEATURE", 0.15),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        offline_mode=os.getenv("OFFLINE_MODE", "auto").lower(),
    )
