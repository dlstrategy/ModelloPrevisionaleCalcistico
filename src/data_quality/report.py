"""Report data quality — dataclass e serializzazione JSON/CSV."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class QualityIssue:
    severity: str  # "error" | "warning" | "info"
    area: str  # matches | scores | xg | shots | lineups | tactical | calendar | features
    code: str
    message: str
    fixture_id: int | None = None


@dataclass(frozen=True)
class QualityReport:
    league_id: int
    generated_at: str
    errors: int
    warnings: int
    infos: int
    issues: tuple[QualityIssue, ...]
    passed: bool
    dataset_summary: dict[str, int]
    area_status: dict[str, str]
    data_profile: str | None = None
    data_completeness: dict | None = None

    def as_dict(self) -> dict:
        payload = {
            "league_id": self.league_id,
            "generated_at": self.generated_at,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
            "dataset_summary": self.dataset_summary,
            "area_status": self.area_status,
            "issues": [asdict(issue) for issue in self.issues],
        }
        if self.data_profile is not None:
            payload["data_profile"] = self.data_profile
        if self.data_completeness is not None:
            payload["data_completeness"] = self.data_completeness
        return payload


def build_report(
    league_id: int,
    issues: list[QualityIssue],
    *,
    dataset_summary: dict[str, int],
    data_profile: str | None = None,
    data_completeness: dict | None = None,
) -> QualityReport:
    errors = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    infos = sum(1 for i in issues if i.severity == "info")

    areas = ("matches", "scores", "xg", "shots", "lineups", "tactical", "calendar", "features")
    area_status: dict[str, str] = {}
    for area in areas:
        area_errors = [i for i in issues if i.area == area and i.severity == "error"]
        area_status[area] = "FAILED" if area_errors else "OK"

    return QualityReport(
        league_id=league_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        errors=errors,
        warnings=warnings,
        infos=infos,
        issues=tuple(issues),
        passed=errors == 0,
        dataset_summary=dataset_summary,
        area_status=area_status,
        data_profile=data_profile,
        data_completeness=data_completeness,
    )


def save_quality_report(report: QualityReport, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"quality_{report.league_id}_latest.json"
    csv_path = output_dir / f"quality_{report.league_id}_latest.csv"

    json_path.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["severity", "area", "code", "message", "fixture_id"])
        for issue in report.issues:
            writer.writerow(
                [
                    issue.severity,
                    issue.area,
                    issue.code,
                    issue.message,
                    issue.fixture_id if issue.fixture_id is not None else "",
                ]
            )

    return json_path, csv_path
