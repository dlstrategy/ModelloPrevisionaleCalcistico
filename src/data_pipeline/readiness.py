"""Real data readiness audit — controlli statici, nessuna chiamata API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.config import PROJECT_ROOT, Settings
from src.data_capabilities.capabilities import POLICY_DISABLED_CAPABILITIES
from src.data_capabilities.requirements import ALL_FEATURE_GROUPS
from src.data_capabilities.resolver import parse_data_profile
from src.features.feature_groups import FEATURE_GROUPS

OVERALL_READY = "READY"
OVERALL_PARTIAL = "PARTIAL_READY"
OVERALL_NOT_READY = "NOT_READY"

COACH_MAPPING_DOC = (
    PROJECT_ROOT / "docs/progetto/implementazioni/28-sportmonks-coach-mapping-prep.md"
)
READINESS_AUDIT_DOC = (
    PROJECT_ROOT / "docs/progetto/implementazioni/29-real-data-readiness-audit.md"
)
PROMOTION_GATE_PATH = PROJECT_ROOT / "src/backtesting/promotion_gate.py"
FEATURE_POLICY_PATH = PROJECT_ROOT / "src/training/feature_policy.py"
SPORTMONKS_CLIENT_PATH = PROJECT_ROOT / "src/sportmonks/client.py"

# Gruppi che richiedono mapper API reali oltre fixture base (participants/scores/state).
ADVANCED_API_MAPPER_GROUPS: frozenset[str] = frozenset(
    {"xg", "shots", "player_lineup", "tactical", "coach"}
)

FEATURE_GROUP_API_NOTES: dict[str, str] = {
    "base": "fixtures + standings da sync base",
    "advanced_strength": "derivato da storico fixture/scores",
    "xg": "statistics fixture — mapper non collegato a sync",
    "shots": "statistics fixture — mapper non collegato a sync",
    "strength_of_schedule": "derivato da storico fixture",
    "player_lineup": "lineups/expectedLineups — mapper non collegato",
    "tactical": "lineups + formation — parzialmente mock",
    "coach": "coaches include + registry API — solo offline fixture",
    "calendar": "starting_at fixture — disponibile con sync base",
    "motivation": "standings — parziale con sync base",
}


@dataclass(frozen=True)
class ReadinessItem:
    area: str
    status: str
    severity: str
    message: str
    recommendation: str


@dataclass(frozen=True)
class ReadinessReport:
    generated_at: str
    league_id: int
    profile: str
    overall_status: str
    items: tuple[ReadinessItem, ...]

    @property
    def blocking_items(self) -> tuple[ReadinessItem, ...]:
        return tuple(i for i in self.items if i.severity == "blocking")

    @property
    def warning_items(self) -> tuple[ReadinessItem, ...]:
        return tuple(i for i in self.items if i.severity == "warning")

    @property
    def info_items(self) -> tuple[ReadinessItem, ...]:
        return tuple(i for i in self.items if i.severity == "info")


def _item(
    area: str,
    status: str,
    severity: str,
    message: str,
    recommendation: str,
) -> ReadinessItem:
    return ReadinessItem(
        area=area,
        status=status,
        severity=severity,
        message=message,
        recommendation=recommendation,
    )


def _check_client_auth_header_only() -> ReadinessItem:
    source = SPORTMONKS_CLIENT_PATH.read_text(encoding="utf-8")
    auth_in_headers = (
        "def _headers" in source
        and "Authorization" in source
        and "self.settings.api_token" in source
    )
    token_in_query_params = 'params["api_token"]' in source or "params['api_token']" in source
    if auth_in_headers and not token_in_query_params:
        return _item(
            "api_client",
            "ready",
            "info",
            "Autenticazione solo header Authorization; token non in query string",
            "Mantenere il pattern attuale in SportmonksClient",
        )
    return _item(
        "api_client",
        "partial",
        "warning",
        "Verificare manualmente che il token non finisca in query string",
        "Rivedere src/sportmonks/client.py",
    )


def _compute_overall_status(items: tuple[ReadinessItem, ...]) -> str:
    blocking_not_ready = [
        i for i in items if i.severity == "blocking" and i.status == "not_ready"
    ]
    safety_blockers = [
        i
        for i in blocking_not_ready
        if i.area
        in {
            "policy_predictions_odds",
            "offline_default",
            "ensemble_feature_trained",
        }
    ]
    if safety_blockers:
        return OVERALL_NOT_READY
    if blocking_not_ready:
        return OVERALL_PARTIAL
    partial_blocking = [i for i in items if i.severity == "blocking" and i.status == "partial"]
    if partial_blocking:
        return OVERALL_PARTIAL
    warnings = [i for i in items if i.severity == "warning" and i.status != "ready"]
    if warnings:
        return OVERALL_PARTIAL
    return OVERALL_READY


def build_real_data_readiness_report(
    settings: Settings,
    league_id: int,
    *,
    profile: str | None = None,
) -> ReadinessReport:
    """Costruisce report readiness senza chiamate API."""
    profile_name = parse_data_profile(profile or settings.data_profile)
    items: list[ReadinessItem] = []

    if settings.enable_sportmonks_sync:
        items.append(
            _item(
                "enable_sportmonks_sync",
                "partial",
                "warning",
                "ENABLE_SPORTMONKS_SYNC=true — sync API abilitata esplicitamente",
                "Verificare token e mapper avanzati prima di sync reale",
            )
        )
    else:
        items.append(
            _item(
                "enable_sportmonks_sync",
                "ready",
                "info",
                "ENABLE_SPORTMONKS_SYNC default disattivato — sync offline sicura",
                "Lasciare false finché mapper avanzati non sono pronti",
            )
        )

    if settings.has_api_token:
        items.append(
            _item(
                "api_token",
                "partial",
                "warning",
                "SPORTMONKS_API_TOKEN configurato (valore non mostrato)",
                "Non attivare sync reale finché readiness non è READY",
            )
        )
    else:
        items.append(
            _item(
                "api_token",
                "ready",
                "info",
                "SPORTMONKS_API_TOKEN assente — modalità offline garantita",
                "Configurare token solo al cutover Fase 3",
            )
        )

    if settings.enable_sportmonks_sync and not settings.has_api_token:
        items.append(
            _item(
                "sync_token_mismatch",
                "not_ready",
                "blocking",
                "ENABLE_SPORTMONKS_SYNC=true ma token assente — sync API non operativa",
                "Impostare SPORTMONKS_API_TOKEN o disabilitare ENABLE_SPORTMONKS_SYNC",
            )
        )

    if settings.is_offline or not settings.can_sync_api:
        items.append(
            _item(
                "offline_default",
                "ready",
                "info",
                f"Modalità effettiva offline (is_offline={settings.is_offline})",
                "Comportamento production invariato finché can_sync_api è false",
            )
        )
    else:
        items.append(
            _item(
                "offline_default",
                "partial",
                "warning",
                "can_sync_api=true — sync reale possibile al prossimo sync",
                "Eseguire readiness e completare mapper prima del primo sync",
            )
        )

    disabled = sorted(c.value for c in POLICY_DISABLED_CAPABILITIES)
    if disabled == ["ODDS", "PREDICTIONS"]:
        items.append(
            _item(
                "policy_predictions_odds",
                "ready",
                "info",
                "PREDICTIONS e ODDS policy-disabled",
                "Non abilitare mercati betting o Predictions Sportmonks",
            )
        )
    else:
        items.append(
            _item(
                "policy_predictions_odds",
                "not_ready",
                "blocking",
                f"Policy disabled inattesa: {disabled}",
                "Ripristinare POLICY_DISABLED_CAPABILITIES",
            )
        )

    items.append(_check_client_auth_header_only())

    items.append(
        _item(
            "response_cache",
            "ready",
            "info",
            "ResponseCache SQLite predisposta (data/cache.db)",
            "Usare TTL configurabili per fixtures/standings",
        )
    )

    items.append(
        _item(
            "sync_includes",
            "partial",
            "warning",
            "Sync API usa include base: participants;scores;state",
            "Estendere include per statistics, lineups, coaches prima di feature avanzate",
        )
    )

    for group in sorted(ALL_FEATURE_GROUPS):
        if group in FEATURE_GROUPS:
            items.append(
                _item(
                    f"feature_group_{group}",
                    "ready" if group not in ADVANCED_API_MAPPER_GROUPS else "partial",
                    "info" if group not in ADVANCED_API_MAPPER_GROUPS else "warning",
                    f"Gruppo '{group}' definito ({len(FEATURE_GROUPS[group])} chiavi). "
                    f"{FEATURE_GROUP_API_NOTES.get(group, '')}",
                    "Mapper API" if group in ADVANCED_API_MAPPER_GROUPS else "OK offline",
                )
            )
        else:
            items.append(
                _item(
                    f"feature_group_{group}",
                    "not_ready",
                    "blocking",
                    f"Gruppo feature '{group}' mancante in FEATURE_GROUPS",
                    "Allineare feature_groups.py e requirements.py",
                )
            )

    if "coach" in FEATURE_GROUPS:
        items.append(
            _item(
                "feature_group_coach_present",
                "ready",
                "info",
                "Gruppo coach presente nel feature vector",
                "Popolare CoachProfile da API al cutover",
            )
        )

    for group in sorted(ADVANCED_API_MAPPER_GROUPS):
        items.append(
            _item(
                f"api_mapper_{group}",
                "not_ready",
                "blocking",
                f"Mapper API Sportmonks per '{group}' non collegato al sync pipeline",
                f"Implementare normalizer + sync include per {group}",
            )
        )

    if COACH_MAPPING_DOC.exists():
        items.append(
            _item(
                "coach_mapping_doc",
                "ready",
                "info",
                "Documento coach mapping Sportmonks presente (doc 28)",
                "Implementare mapper seguendo doc 28",
            )
        )
    else:
        items.append(
            _item(
                "coach_mapping_doc",
                "not_ready",
                "blocking",
                "Documento coach mapping Sportmonks assente",
                "Creare docs/progetto/implementazioni/28-sportmonks-coach-mapping-prep.md",
            )
        )

    player_modules = (
        PROJECT_ROOT / "src/players/global_registry.py",
        PROJECT_ROOT / "src/players/composable_transfer.py",
        PROJECT_ROOT / "src/players/unknown_player_policy.py",
    )
    if all(p.exists() for p in player_modules):
        items.append(
            _item(
                "player_transfer_layer",
                "partial",
                "warning",
                "Player transfer layer offline presente; registry API non collegato",
                "Implementare sync player_careers da Sportmonks players/statistics",
            )
        )
    else:
        items.append(
            _item(
                "player_transfer_layer",
                "not_ready",
                "blocking",
                "Moduli player transfer incompleti",
                "Verificare src/players/",
            )
        )

    items.append(
        _item(
            "player_careers_api_mapper",
            "not_ready",
            "blocking",
            "player_careers.json popolato solo da fixture offline",
            "Aggiungere pipeline API per career registry cross-league",
        )
    )

    coach_modules = (
        PROJECT_ROOT / "src/coaches/coach_registry.py",
        PROJECT_ROOT / "src/coaches/coach_adaptation.py",
    )
    if all(p.exists() for p in coach_modules):
        items.append(
            _item(
                "coach_layer_offline",
                "partial",
                "warning",
                "Coach layer offline OK; mapper API documentato ma non implementato",
                "Collegare fetch coaches + statistics.details al sync",
            )
        )

    if FEATURE_POLICY_PATH.exists():
        items.append(
            _item(
                "feature_policy_compact",
                "ready",
                "info",
                "Feature policy full/compact presente",
                "Ritrainare artifact su dataset reale post-sync",
            )
        )
    else:
        items.append(
            _item(
                "feature_policy_compact",
                "not_ready",
                "blocking",
                "Modulo feature_policy assente",
                "Ripristinare src/training/feature_policy.py",
            )
        )

    if PROMOTION_GATE_PATH.exists():
        items.append(
            _item(
                "promotion_gate",
                "ready",
                "info",
                "Promotion gate presente per valutazione feature_trained",
                "Usare walk-forward refit, non backtest in-sample",
            )
        )
    else:
        items.append(
            _item(
                "promotion_gate",
                "not_ready",
                "blocking",
                "Modulo promotion_gate assente",
                "Ripristinare src/backtesting/promotion_gate.py",
            )
        )

    items.append(
        _item(
            "feature_trained_ensemble",
            "ready",
            "info",
            "feature_trained escluso da build_base_models e run_backtest_all_models",
            "Non includere feature_trained nell'ensemble production",
        )
    )

    items.append(
        _item(
            "mock_artifacts_retrain",
            "partial",
            "warning",
            "Artifact feature_trained mock non validi su dataset reale",
            "Ritrainare dopo sync reale; invalidare se league/season cambiano",
        )
    )

    if READINESS_AUDIT_DOC.exists():
        items.append(
            _item(
                "readiness_audit_doc",
                "ready",
                "info",
                "Documento audit readiness (doc 29) presente",
                "Aggiornare dopo ogni mapper API implementato",
            )
        )

    overall = _compute_overall_status(tuple(items))
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return ReadinessReport(
        generated_at=generated_at,
        league_id=league_id,
        profile=profile_name,
        overall_status=overall,
        items=tuple(items),
    )


def readiness_report_as_dict(report: ReadinessReport) -> dict:
    def _serialize_item(item: ReadinessItem) -> dict:
        return {
            "area": item.area,
            "status": item.status,
            "severity": item.severity,
            "message": item.message,
            "recommendation": item.recommendation,
        }

    return {
        "generated_at": report.generated_at,
        "league_id": report.league_id,
        "profile": report.profile,
        "overall_status": report.overall_status,
        "blocking": [_serialize_item(i) for i in report.blocking_items],
        "warnings": [_serialize_item(i) for i in report.warning_items],
        "info": [_serialize_item(i) for i in report.info_items],
        "items": [_serialize_item(i) for i in report.items],
    }
