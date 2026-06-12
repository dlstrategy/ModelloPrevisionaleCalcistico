import io
import sys
from contextlib import redirect_stderr, redirect_stdout

import pytest

from src.cli_status import print_status
from src.config import PROCESSED_DIR, load_settings
from src.data_pipeline.sync import sync_league_data


@pytest.fixture(scope="module")
def synced_dataset():
    settings = load_settings()
    return sync_league_data(settings, 384)


def test_status_offline_counts(synced_dataset):
    settings = load_settings()
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = print_status(settings, 384)
    output = buf.getvalue()

    assert code == 0
    assert "offline" in output.lower() or "Modalità:" in output
    assert "Partite totali:     50" in output
    assert "Partite finite:     40" in output
    assert "Partite future:     10" in output
    assert "Squadre distinte:   10" in output
    assert "xg" in output
    assert "lineups" in output
    assert "Feature attive" in output
    assert "Data profile:" in output
    assert "Data completeness:" in output
    assert "Feature groups:" in output
    assert "Policy disabled:" in output


def test_status_missing_dataset_suggests_sync():
    settings = load_settings()
    missing_league = 99999
    processed = PROCESSED_DIR / f"league_{missing_league}_dataset.json"
    if processed.exists():
        processed.unlink()

    err = io.StringIO()
    with redirect_stderr(err):
        code = print_status(settings, missing_league)

    message = err.getvalue()
    assert code == 1
    assert "Dataset processato non trovato" in message
    assert "python -m src.cli sync --league 99999" in message
