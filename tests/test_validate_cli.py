import io
import json
from contextlib import redirect_stdout

import pytest

from src.cli import main
from src.cli_validate import print_validate
from src.config import QUALITY_DIR, load_settings
from src.data_pipeline.sync import sync_league_data


@pytest.fixture(scope="module")
def synced(settings):
    return sync_league_data(settings, 384)


@pytest.fixture(scope="module")
def settings():
    return load_settings()


def test_validate_cli_exit_code_zero(synced, settings):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_validate(settings, 384)
    output = buf.getvalue()
    assert code == 0
    assert "Status: PASSED" in output
    assert "matches: 50" in output


def test_validate_creates_json_and_csv_reports(synced, settings):
    print_validate(settings, 384)
    json_path = QUALITY_DIR / "quality_384_latest.json"
    csv_path = QUALITY_DIR / "quality_384_latest.csv"
    assert json_path.exists()
    assert csv_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "errors" in payload
    assert "warnings" in payload
    assert "issues" in payload


def test_validate_module_entrypoint(synced):
    code = main(["validate", "--league", "384"])
    assert code == 0
