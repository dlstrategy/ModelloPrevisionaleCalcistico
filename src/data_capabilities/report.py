"""Report data completeness e risoluzione capability."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DataCompletenessReport:
    profile: str
    score: float
    available_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    policy_disabled_capabilities: tuple[str, ...]
    enabled_feature_groups: tuple[str, ...]
    disabled_feature_groups: tuple[str, ...]
    fallbacks_used: tuple[str, ...]

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityResolution:
    profile: str
    enabled_feature_groups: frozenset[str]
    disabled_feature_groups: frozenset[str]
    fallbacks: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    policy_disabled_capabilities: tuple[str, ...]
    available_capabilities: tuple[str, ...]
    completeness: DataCompletenessReport

    def as_dict(self) -> dict:
        return {
            "profile": self.profile,
            "enabled_feature_groups": sorted(self.enabled_feature_groups),
            "disabled_feature_groups": sorted(self.disabled_feature_groups),
            "fallbacks": list(self.fallbacks),
            "missing_capabilities": list(self.missing_capabilities),
            "policy_disabled_capabilities": list(self.policy_disabled_capabilities),
            "available_capabilities": list(self.available_capabilities),
            "data_completeness": self.completeness.as_dict(),
        }

    def enabled_groups_for_context(self) -> frozenset[str]:
        return self.enabled_feature_groups

    def explain_warnings(self) -> list[str]:
        warnings: list[str] = []
        profile_caps = set(self.completeness.available_capabilities) | set(
            self.completeness.missing_capabilities
        )
        if "xg" in self.disabled_feature_groups:
            warnings.append(
                "xG non disponibile nel profilo corrente: feature xG disabilitata/fallback."
            )
        if "shots" in self.disabled_feature_groups:
            warnings.append(
                "Shots non disponibili nel profilo corrente: feature shots disabilitata/fallback."
            )
        if any("lineup" in fb for fb in self.fallbacks):
            warnings.append(
                "Expected lineups non disponibili: uso lineup confermata se presente, "
                "altrimenti fallback neutro."
            )
        if any("tactical" in fb for fb in self.fallbacks):
            warnings.append(
                "Tactical data non disponibile: uso default tactical fallback."
            )
        if self.missing_capabilities:
            missing = ", ".join(self.missing_capabilities)
            warnings.append(f"Capability attese dal profilo ma assenti: {missing}.")
        warnings.append("PREDICTIONS e ODDS disabilitati per policy progetto.")
        return warnings
