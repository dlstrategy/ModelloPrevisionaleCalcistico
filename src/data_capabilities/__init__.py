"""Data capability layer — profili, requisiti feature e completeness."""

from src.data_capabilities.capabilities import (
    POLICY_DISABLED_CAPABILITIES,
    VALID_PROFILES,
    DataCapability,
)
from src.data_capabilities.profiles import DATA_PROFILES, profile_capabilities
from src.data_capabilities.report import CapabilityResolution, DataCompletenessReport
from src.data_capabilities.requirements import FEATURE_REQUIREMENTS, ALL_FEATURE_GROUPS
from src.data_capabilities.resolver import (
    capability_status_label,
    detect_available_capabilities,
    parse_data_profile,
    resolve_capabilities,
)

__all__ = [
    "ALL_FEATURE_GROUPS",
    "CapabilityResolution",
    "DATA_PROFILES",
    "DataCapability",
    "DataCompletenessReport",
    "FEATURE_REQUIREMENTS",
    "POLICY_DISABLED_CAPABILITIES",
    "VALID_PROFILES",
    "capability_status_label",
    "detect_available_capabilities",
    "parse_data_profile",
    "profile_capabilities",
    "resolve_capabilities",
]
